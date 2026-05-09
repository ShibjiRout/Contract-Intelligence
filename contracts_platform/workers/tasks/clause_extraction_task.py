import asyncio

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


@app.task(
    bind=True,
    queue="extraction",
    name="contracts_platform.workers.tasks.clause_extraction_task.clause_extraction_task",
    max_retries=RETRY_POLICY["clause_extraction_task"]["max_retries"],
    default_retry_delay=RETRY_POLICY["clause_extraction_task"]["countdown"],
)
def clause_extraction_task(self, contract_id: str) -> None:
    """Extract clauses from the OCR text stored in Redis."""
    try:
        publish(contract_id, "clause_extraction", 55, "clause extraction started")

        db = asyncio.run(get_database())
        asyncio.run(
            contract_repo.update_status(
                db, contract_id, ContractStatus.PROCESSING, stage="clause_extraction"
            )
        )

        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        text = r.get(f"ocr_text:{contract_id}") or ""

        # Stub call — pipeline agent will implement
        from contracts_platform.pipeline.clause_extraction.extractor import extract_clauses  # type: ignore[import]

        clauses = asyncio.run(extract_clauses(contract_id, text))  # type: ignore[arg-type]
        if clauses:
            asyncio.run(db["clauses"].insert_many(clauses))

        publish(contract_id, "clause_extraction", 75, "clauses extracted")

        from contracts_platform.workers.tasks.review_orchestration_task import review_orchestration_task

        review_orchestration_task.apply_async(args=[contract_id], queue="orchestration")

    except Exception as exc:
        db = asyncio.run(get_database())
        asyncio.run(
            contract_repo.append_error(
                db, contract_id, stage="clause_extraction", message=str(exc)
            )
        )
        logger.error("clause_extraction_task.error", contract_id=contract_id, error=str(exc))
        try:
            raise self.retry(exc=exc, countdown=RETRY_POLICY["clause_extraction_task"]["countdown"])
        except self.MaxRetriesExceededError:
            dead_letter_handler.apply_async(
                args=[contract_id, self.name, str(exc)],
                queue="dlq",
            )
