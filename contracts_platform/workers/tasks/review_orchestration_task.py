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
def review_orchestration_task(self, contract_id: str) -> None:
    """Run the LangGraph review orchestration (playbook + vector + graph checks)."""
    try:
        publish(contract_id, "review_orchestration", 78, "orchestration started")

        db = asyncio.run(get_database())
        asyncio.run(
            contract_repo.update_status(
                db, contract_id, ContractStatus.PROCESSING, stage="review_orchestration"
            )
        )

        # Stub call — langgraph agent will implement
        from contracts_platform.orchestration.graph import run_review_graph  # type: ignore[import]

        asyncio.run(run_review_graph(contract_id))  # type: ignore[arg-type]

        publish(contract_id, "review_orchestration", 90, "orchestration complete")

        from contracts_platform.workers.tasks.recommendation_task import recommendation_task

        recommendation_task.apply_async(args=[contract_id], queue="recommendation")

    except Exception as exc:
        db = asyncio.run(get_database())
        asyncio.run(
            contract_repo.append_error(
                db, contract_id, stage="review_orchestration", message=str(exc)
            )
        )
        logger.error("review_orchestration_task.error", contract_id=contract_id, error=str(exc))
        try:
            raise self.retry(
                exc=exc, countdown=RETRY_POLICY["review_orchestration_task"]["countdown"]
            )
        except self.MaxRetriesExceededError:
            dead_letter_handler.apply_async(
                args=[contract_id, self.name, str(exc)],
                queue="dlq",
            )
