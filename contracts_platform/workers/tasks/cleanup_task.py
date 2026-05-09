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
    queue="cleanup",
    name="contracts_platform.workers.tasks.cleanup_task.cleanup_task",
    max_retries=RETRY_POLICY["cleanup_task"]["max_retries"],
    default_retry_delay=RETRY_POLICY["cleanup_task"]["countdown"],
)
def cleanup_task(self, contract_id: str) -> None:
    """Delete temporary Azure File Share data, write audit summary, and mark contract COMPLETED."""
    try:
        db = asyncio.run(get_database())
        asyncio.run(
            contract_repo.update_status(
                db, contract_id, ContractStatus.PROCESSING, stage="cleanup"
            )
        )

        # Stub call — fastapi/file_handling agent will implement
        from file_handling.temp_storage import delete_temp_file  # type: ignore[import]

        asyncio.run(delete_temp_file(contract_id))  # type: ignore[arg-type]

        db = asyncio.run(get_database())
        asyncio.run(
            contract_repo.append_error(
                db, contract_id, stage="audit", message="cleanup complete"
            )
        )

        asyncio.run(
            contract_repo.update_status(
                db, contract_id, ContractStatus.COMPLETED, stage="cleanup"
            )
        )

        publish(contract_id, "cleanup", 100, "pipeline complete")

    except Exception as exc:
        db = asyncio.run(get_database())
        asyncio.run(
            contract_repo.append_error(db, contract_id, stage="cleanup", message=str(exc))
        )
        logger.error("cleanup_task.error", contract_id=contract_id, error=str(exc))
        try:
            raise self.retry(exc=exc, countdown=RETRY_POLICY["cleanup_task"]["countdown"])
        except self.MaxRetriesExceededError:
            dead_letter_handler.apply_async(
                args=[contract_id, self.name, str(exc)],
                queue="dlq",
            )
