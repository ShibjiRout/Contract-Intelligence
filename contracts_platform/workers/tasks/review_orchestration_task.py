import asyncio

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
    queue="orchestration",
    name="contracts_platform.workers.tasks.review_orchestration_task.review_orchestration_task",
    max_retries=RETRY_POLICY["review_orchestration_task"]["max_retries"],
    default_retry_delay=RETRY_POLICY["review_orchestration_task"]["countdown"],
)
def review_orchestration_task(self, contract_id: str, clause_id: str) -> None:
    """Run the LangGraph sequential pipeline for a single risky clause."""

    async def _run() -> None:
        db = await get_database()
        try:
            publish(contract_id, "review_orchestration", 82, f"analysing clause {clause_id}")

            await contract_repo.update_status(
                db, contract_id, ContractStatus.PROCESSING, stage="review_orchestration"
            )

            from contracts_platform.orchestration.graph import run_review_graph

            await run_review_graph(contract_id, clause_id)

            publish(contract_id, "review_orchestration", 95, "clause analysis complete")

            # Check if all risky clauses are done — if so, set REVIEW_READY
            remaining = await db["clauses"].count_documents(
                {"contract_id": contract_id, "status": "need_changes", "ai_recommendation": None}
            )
            if remaining == 0:
                await contract_repo.update_status(
                    db, contract_id, ContractStatus.REVIEW_READY, stage="review_orchestration"
                )
                publish(contract_id, "review_orchestration", 100, "ready for lawyer review")
                logger.info("review_orchestration_task.review_ready", contract_id=contract_id)

        except Exception as exc:
            await contract_repo.append_error(
                db, contract_id, stage="review_orchestration", message=str(exc)
            )
            logger.error("review_orchestration_task.error", contract_id=contract_id, error=str(exc))
            raise

    try:
        asyncio.run(_run())
    except Exception as exc:
        try:
            raise self.retry(
                exc=exc, countdown=RETRY_POLICY["review_orchestration_task"]["countdown"]
            )
        except self.MaxRetriesExceededError:
            dead_letter_handler.apply_async(
                args=[contract_id, self.name, str(exc)],
                queue="dlq",
            )
