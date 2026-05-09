import asyncio
import base64

import magic

from contracts_platform.core.constants import ContractStatus
from contracts_platform.core.logging import logger
from contracts_platform.db.mongodb.client import get_database
from contracts_platform.db.mongodb.repositories import contract_repo
from contracts_platform.file_handling.duplicate_detector import check_duplicate
from contracts_platform.workers.celery_app import app
from contracts_platform.workers.dead_letter import dead_letter_handler
from contracts_platform.workers.progress_tracker import publish
from contracts_platform.workers.retry_policy import RETRY_POLICY

_ALLOWED_MIMES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
_MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


@app.task(
    bind=True,
    queue="ingest",
    name="contracts_platform.workers.tasks.ingest_task.ingest_task",
    max_retries=RETRY_POLICY["ingest_task"]["max_retries"],
    default_retry_delay=RETRY_POLICY["ingest_task"]["countdown"],
)
def ingest_task(
    self,
    contract_id: str,
    file_bytes_b64: str,
    filename: str,
    user_id: str,
    tenant_id: str,
) -> None:
    """Validate, deduplicate, and hand off to OCR."""

    async def _run() -> None:
        db = await get_database()
        try:
            publish(contract_id, "ingest", 0, "ingestion started")

            file_bytes = base64.b64decode(file_bytes_b64)

            await contract_repo.update_status(
                db, contract_id, ContractStatus.PROCESSING, stage="ingestion"
            )

            mime = magic.from_buffer(file_bytes, mime=True)
            if mime not in _ALLOWED_MIMES:
                raise ValueError(f"Unsupported file type: {mime}")

            if len(file_bytes) > _MAX_SIZE_BYTES:
                raise ValueError(f"File size {len(file_bytes)} exceeds 50 MB limit")

            is_duplicate, existing_id = await check_duplicate(db, file_bytes, exclude_contract_id=contract_id)

            if is_duplicate:
                publish(contract_id, "ingest", 100, "duplicate detected")
                await contract_repo.update_status(
                    db, contract_id, ContractStatus.REVIEW_READY, stage="ingestion"
                )
                logger.info(
                    "ingest_task.duplicate",
                    contract_id=contract_id,
                    existing_id=existing_id,
                )
                return

            publish(contract_id, "ingest", 25, "validation passed")

            from contracts_platform.workers.tasks.ocr_task import ocr_task

            ocr_task.apply_async(
                args=[contract_id, file_bytes_b64, filename],
                queue="ocr",
            )

        except Exception as exc:
            await contract_repo.append_error(db, contract_id, stage="ingest", message=str(exc))
            logger.error("ingest_task.error", contract_id=contract_id, error=str(exc))
            raise

    try:
        asyncio.run(_run())
    except Exception as exc:
        try:
            raise self.retry(exc=exc, countdown=RETRY_POLICY["ingest_task"]["countdown"])
        except self.MaxRetriesExceededError:
            dead_letter_handler.apply_async(
                args=[contract_id, self.name, str(exc)],
                queue="dlq",
            )
