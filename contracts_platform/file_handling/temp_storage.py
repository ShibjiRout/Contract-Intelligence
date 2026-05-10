from __future__ import annotations

import asyncio
from functools import partial

from azure.storage.fileshare import ShareFileClient

from contracts_platform.core.config import settings
from contracts_platform.core.exceptions import StorageError
from contracts_platform.core.logging import logger


def _get_file_client(contract_id: str) -> ShareFileClient:
    return ShareFileClient.from_connection_string(
        conn_str=settings.AZURE_FILE_SHARE_CONNECTION_STRING,
        share_name=settings.AZURE_FILE_SHARE_NAME,
        file_path=f"{contract_id}.txt",
    )


def _save_sync(contract_id: str, text: str) -> None:
    client = _get_file_client(contract_id)
    encoded = text.encode("utf-8")
    client.upload_file(encoded)


def _load_sync(contract_id: str) -> str:
    client = _get_file_client(contract_id)
    stream = client.download_file()
    return stream.readall().decode("utf-8")


def _delete_sync(contract_id: str) -> None:
    client = _get_file_client(contract_id)
    client.delete_file()


async def save_temp_text(contract_id: str, text: str) -> None:
    """Save extracted text to Azure File Share as {contract_id}.txt."""
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, partial(_save_sync, contract_id, text))
        logger.info("temp_storage.save_complete", contract_id=contract_id)
    except Exception as exc:
        logger.error("temp_storage.save_failed", contract_id=contract_id, error=str(exc))
        raise StorageError(f"Failed to save temp text for {contract_id}: {exc}") from exc


async def load_temp_text(contract_id: str) -> str:
    """Load extracted text for contract_id from Azure File Share."""
    loop = asyncio.get_event_loop()
    try:
        text: str = await loop.run_in_executor(None, partial(_load_sync, contract_id))
        logger.info("temp_storage.load_complete", contract_id=contract_id)
        return text
    except Exception as exc:
        logger.error("temp_storage.load_failed", contract_id=contract_id, error=str(exc))
        raise StorageError(f"Failed to load temp text for {contract_id}: {exc}") from exc


async def delete_temp_file(contract_id: str) -> None:
    """Delete {contract_id}.txt from Azure File Share. 404 is treated as success (idempotent)."""
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, partial(_delete_sync, contract_id))
        logger.info("temp_storage.delete_complete", contract_id=contract_id)
    except Exception as exc:
        exc_str = str(exc).lower()
        if "resourcenotfound" in exc_str or "404" in exc_str or "does not exist" in exc_str:
            logger.info("temp_storage.delete_already_gone", contract_id=contract_id)
            return
        logger.error("temp_storage.delete_failed", contract_id=contract_id, error=str(exc))
        raise StorageError(f"Failed to delete temp file for {contract_id}: {exc}") from exc
