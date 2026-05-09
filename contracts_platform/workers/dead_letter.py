import asyncio

from contracts_platform.core.constants import ContractStatus
from contracts_platform.core.logging import logger
from contracts_platform.db.mongodb.client import get_database
from contracts_platform.db.mongodb.repositories import contract_repo
from contracts_platform.workers.celery_app import app


@app.task(bind=True, queue="dlq", name="contracts_platform.workers.dead_letter.dead_letter_handler")
def dead_letter_handler(self, contract_id: str, task_name: str, error_message: str) -> None:
    """Handle tasks that have exceeded their max retries by recording the failure in MongoDB."""

    async def _run() -> None:
        db = await get_database()
        await contract_repo.update_status(
            db, contract_id, ContractStatus.ERROR, stage=task_name
        )
        await contract_repo.append_error(
            db, contract_id, stage=task_name, message=error_message
        )

    asyncio.run(_run())

    logger.error(
        "task.dead_letter",
        contract_id=contract_id,
        task_name=task_name,
        error=error_message,
    )
