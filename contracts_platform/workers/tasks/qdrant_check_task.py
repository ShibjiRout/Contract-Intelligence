from __future__ import annotations

import asyncio

from openai import AsyncOpenAI

from contracts_platform.core.config import settings
from contracts_platform.core.constants import ContractStatus
from contracts_platform.core.logging import logger
from contracts_platform.db.mongodb.client import get_database
from contracts_platform.db.mongodb.repositories import contract_repo
from contracts_platform.db.qdrant.repositories.clause_vector_repo import search_similar
from contracts_platform.workers.celery_app import app
from contracts_platform.workers.dead_letter import dead_letter_handler
from contracts_platform.workers.progress_tracker import publish
from contracts_platform.workers.retry_policy import RETRY_POLICY

GOLD_STANDARD_THRESHOLD = 0.95


@app.task(
    bind=True,
    queue="qdrant_check",
    name="contracts_platform.workers.tasks.qdrant_check_task.qdrant_check_task",
    max_retries=RETRY_POLICY["qdrant_check_task"]["max_retries"],
    default_retry_delay=RETRY_POLICY["qdrant_check_task"]["countdown"],
)
def qdrant_check_task(self, contract_id: str) -> None:
    """
    For each extracted clause:
      - Embed clause text via OpenAI
      - Search Qdrant Gold Standard (clauses_playbook collection)
      - If top match score >= 0.95 → clause is standard → status = approved, risk_category = GREEN
      - If score < 0.95 → clause needs review → dispatch review_orchestration_task for it

    After checking all clauses:
      - If ALL approved → contract status = COMPLETED
      - If ANY need_changes → contract status = REVIEW_READY
    """

    async def _run() -> None:
        db = await get_database()
        try:
            publish(contract_id, "qdrant_check", 76, "Gold Standard check started")

            await contract_repo.update_status(
                db, contract_id, ContractStatus.PROCESSING, stage="qdrant_check"
            )

            clauses = await db["clauses"].find(
                {"contract_id": contract_id}, {"_id": 0}
            ).to_list(length=None)

            if not clauses:
                logger.warning("qdrant_check_task.no_clauses", contract_id=contract_id)
                await contract_repo.update_status(
                    db, contract_id, ContractStatus.COMPLETED, stage="qdrant_check"
                )
                return

            oai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            risky_clause_ids: list[str] = []

            for clause in clauses:
                clause_id = str(clause.get("clause_id", ""))
                clause_type = clause.get("clause_type", "")
                raw_text = clause.get("raw_text", "")

                if not raw_text:
                    continue

                try:
                    embedding_response = await oai.embeddings.create(
                        model=settings.EMBEDDING_MODEL,
                        input=raw_text,
                    )
                    vector = embedding_response.data[0].embedding

                    # Search Gold Standard (playbook collection, accepted wording)
                    matches = await search_similar(
                        tenant_id="playbook",
                        vector=vector,
                        clause_type=clause_type,
                        status="accepted",
                        limit=1,
                    )

                    top_score = matches[0]["score"] if matches else 0.0

                    if top_score >= GOLD_STANDARD_THRESHOLD:
                        # Standard clause — auto approve
                        await db["clauses"].update_one(
                            {"clause_id": clause_id},
                            {"$set": {
                                "status": "approved",
                                "risk_category": "GREEN",
                            }},
                        )
                        logger.info(
                            "qdrant_check_task.clause_approved",
                            contract_id=contract_id,
                            clause_id=clause_id,
                            score=top_score,
                        )
                    else:
                        # Risky clause — needs LangGraph review
                        await db["clauses"].update_one(
                            {"clause_id": clause_id},
                            {"$set": {"status": "ai_flagged"}},
                        )
                        risky_clause_ids.append(clause_id)
                        logger.info(
                            "qdrant_check_task.clause_needs_review",
                            contract_id=contract_id,
                            clause_id=clause_id,
                            score=top_score,
                        )

                except Exception as exc:
                    logger.error(
                        "qdrant_check_task.clause_error",
                        contract_id=contract_id,
                        clause_id=clause_id,
                        error=str(exc),
                    )
                    risky_clause_ids.append(clause_id)

            publish(contract_id, "qdrant_check", 80, "Gold Standard check complete")

            if not risky_clause_ids:
                # All clauses matched Gold Standard — contract is complete
                await contract_repo.update_status(
                    db, contract_id, ContractStatus.COMPLETED, stage="qdrant_check"
                )
                publish(contract_id, "qdrant_check", 100, "All clauses standard — completed")
                logger.info(
                    "qdrant_check_task.all_standard",
                    contract_id=contract_id,
                    total_clauses=len(clauses),
                )
            else:
                # Dispatch LangGraph for each risky clause
                from contracts_platform.workers.tasks.review_orchestration_task import (
                    review_orchestration_task,
                )

                for risky_clause_id in risky_clause_ids:
                    review_orchestration_task.apply_async(
                        args=[contract_id, risky_clause_id],
                        queue="orchestration",
                    )

                logger.info(
                    "qdrant_check_task.risky_clauses_dispatched",
                    contract_id=contract_id,
                    risky_count=len(risky_clause_ids),
                )

        except Exception as exc:
            await contract_repo.append_error(
                db, contract_id, stage="qdrant_check", message=str(exc)
            )
            logger.error("qdrant_check_task.error", contract_id=contract_id, error=str(exc))
            raise

    try:
        asyncio.run(_run())
    except Exception as exc:
        try:
            raise self.retry(exc=exc, countdown=RETRY_POLICY["qdrant_check_task"]["countdown"])
        except self.MaxRetriesExceededError:
            dead_letter_handler.apply_async(
                args=[contract_id, self.name, str(exc)],
                queue="dlq",
            )
