import asyncio
import base64
import json

import redis

from contracts_platform.core.config import settings
from contracts_platform.core.constants import ContractStatus
from contracts_platform.core.logging import logger
from contracts_platform.db.mongodb.client import get_database
from contracts_platform.db.mongodb.repositories import contract_repo
from contracts_platform.workers.celery_app import app
from contracts_platform.workers.dead_letter import dead_letter_handler
from contracts_platform.workers.progress_tracker import publish
from contracts_platform.workers.retry_policy import RETRY_POLICY

_OCR_TEXT_TTL = 3600  # 1 hour


@app.task(
    bind=True,
    queue="ocr",
    name="contracts_platform.workers.tasks.ocr_task.ocr_task",
    max_retries=RETRY_POLICY["ocr_task"]["max_retries"],
    default_retry_delay=RETRY_POLICY["ocr_task"]["countdown"],
)
def ocr_task(self, contract_id: str, file_bytes_b64: str, filename: str) -> None:
    """Run OCR on the uploaded file and cache the extracted text in Redis."""

    async def _run() -> None:
        db = await get_database()
        try:
            publish(contract_id, "ocr", 10, "OCR started")

            await contract_repo.update_status(
                db, contract_id, ContractStatus.PROCESSING, stage="ocr"
            )

            file_bytes = base64.b64decode(file_bytes_b64)

            from contracts_platform.pipeline.ocr.extractor import extract_text

            extracted_text: str = await extract_text(file_bytes, filename)

            r = redis.from_url(settings.REDIS_URL, decode_responses=True)
            r.setex(f"ocr_text:{contract_id}", _OCR_TEXT_TTL, extracted_text)

            # Document-level playbook similarity pre-check. If this passes,
            # clause extraction will still run so we have real clause records,
            # but it can short-circuit the later clause-by-clause review path.
            try:
                from contracts_platform.pipeline.playbook_similarity import (
                    AUTO_ACCEPT_THRESHOLD,
                    should_auto_accept_contract,
                )

                auto_accept_all, top_score = await should_auto_accept_contract(extracted_text)
                if auto_accept_all:
                    r.setex(
                        f"auto_accept_all:{contract_id}",
                        _OCR_TEXT_TTL,
                        json.dumps(
                            {
                                "threshold": AUTO_ACCEPT_THRESHOLD,
                                "top_score": top_score,
                            }
                        ),
                    )
                    logger.info(
                        "ocr_task.auto_accept_flagged",
                        contract_id=contract_id,
                        threshold=AUTO_ACCEPT_THRESHOLD,
                        top_score=top_score,
                    )
                else:
                    r.delete(f"auto_accept_all:{contract_id}")
            except Exception as exc:
                logger.warning(
                    "ocr_task.playbook_similarity_failed",
                    contract_id=contract_id,
                    error=str(exc),
                )

            try:
                from contracts_platform.db.neo4j.repositories.contract_graph_repo import (
                    link_party_to_contract,
                )
                from contracts_platform.db.neo4j.repositories.party_repo import upsert_party
                from contracts_platform.pipeline.party_extraction.extractor import extract_parties

                contract_doc = await db["contracts"].find_one({"contract_id": contract_id}) or {}
                tenant_id = contract_doc.get("tenant_id", "unknown")
                parties = extract_parties(extracted_text)
                await db["contracts"].update_one(
                    {"contract_id": contract_id},
                    {"$set": {"parties": parties}},
                )
                for party in parties:
                    await upsert_party(
                        party_id=party["party_id"],
                        tenant_id=tenant_id,
                        name=party["name"],
                        normalized_name=party["normalized_name"],
                    )
                    await link_party_to_contract(
                        party_id=party["party_id"],
                        contract_id=contract_id,
                        role=party.get("role", "party"),
                    )
                logger.info(
                    "ocr_task.parties_extracted",
                    contract_id=contract_id,
                    parties=len(parties),
                )
            except Exception as exc:
                logger.warning("ocr_task.party_extraction_failed", contract_id=contract_id, error=str(exc))

            from contracts_platform.file_handling.temp_storage import save_temp_text

            await save_temp_text(contract_id, extracted_text)

            publish(contract_id, "ocr", 50, "OCR complete")

            from contracts_platform.workers.tasks.clause_extraction_task import clause_extraction_task

            clause_extraction_task.apply_async(args=[contract_id], queue="extraction")

        except Exception as exc:
            await contract_repo.append_error(db, contract_id, stage="ocr", message=str(exc))
            logger.error("ocr_task.error", contract_id=contract_id, error=str(exc))
            raise

    try:
        asyncio.run(_run())
    except Exception as exc:
        try:
            raise self.retry(exc=exc, countdown=RETRY_POLICY["ocr_task"]["countdown"])
        except self.MaxRetriesExceededError:
            dead_letter_handler.apply_async(
                args=[contract_id, self.name, str(exc)],
                queue="dlq",
            )
