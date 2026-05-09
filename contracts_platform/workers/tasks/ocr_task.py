import asyncio
import base64

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

            # Embed pages into ephemeral Qdrant collection for RAG context
            try:
                from contracts_platform.pipeline.ocr.extractor import extract_pages
                from contracts_platform.pipeline.embedder import embed_text
                from contracts_platform.db.qdrant.repositories.clause_vector_repo import (
                    create_temp_collection, upsert_chunk,
                )
                pages = await extract_pages(file_bytes, filename)
                temp_name = f"contract_ingest_{contract_id}"
                await create_temp_collection(temp_name)
                for page in pages:
                    page_text = page.get("text", "").strip()
                    if not page_text:
                        continue
                    vector = await embed_text(page_text)
                    await upsert_chunk(
                        temp_name,
                        str(page.get("page_num", 0)),
                        vector,
                        {"text": page_text, "page_num": page.get("page_num", 0)},
                    )
                r.setex(f"temp_collection:{contract_id}", 7200, temp_name)
                logger.info("ocr_task.temp_collection.ready", contract_id=contract_id, temp_name=temp_name)
            except Exception as exc:
                logger.warning("ocr_task.temp_collection.failed", contract_id=contract_id, error=str(exc))

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
