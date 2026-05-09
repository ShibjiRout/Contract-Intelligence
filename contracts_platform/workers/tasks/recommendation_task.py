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
    queue="recommendation",
    name="contracts_platform.workers.tasks.recommendation_task.recommendation_task",
    max_retries=RETRY_POLICY["recommendation_task"]["max_retries"],
    default_retry_delay=RETRY_POLICY["recommendation_task"]["countdown"],
)
def recommendation_task(self, contract_id: str) -> None:
    """Generate LLM-powered recommendations and mark the contract ready for lawyer review."""

    async def _run() -> None:
        db = await get_database()
        try:
            publish(contract_id, "recommendation", 92, "generating recommendations")

            await contract_repo.update_status(
                db, contract_id, ContractStatus.PROCESSING, stage="recommendation"
            )

            from contracts_platform.pipeline.recommendation.fix_suggester import generate_fixes

            await generate_fixes(contract_id)

            await contract_repo.update_status(
                db, contract_id, ContractStatus.REVIEW_READY, stage="recommendation"
            )

            publish(contract_id, "recommendation", 100, "ready for review")

        except Exception as exc:
            await contract_repo.append_error(
                db, contract_id, stage="recommendation", message=str(exc)
            )
            logger.error("recommendation_task.error", contract_id=contract_id, error=str(exc))
            raise

    try:
        asyncio.run(_run())
    except Exception as exc:
        try:
            raise self.retry(exc=exc, countdown=RETRY_POLICY["recommendation_task"]["countdown"])
        except self.MaxRetriesExceededError:
            dead_letter_handler.apply_async(
                args=[contract_id, self.name, str(exc)],
                queue="dlq",
            )
