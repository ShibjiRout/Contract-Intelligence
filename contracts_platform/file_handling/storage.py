from __future__ import annotations

import asyncio
from functools import partial

from azure.storage.blob import BlobServiceClient

from contracts_platform.core.config import settings
from contracts_platform.core.exceptions import StorageError
from contracts_platform.core.logging import logger


def _get_blob_client(container: str, blob_name: str):
    service = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
    return service.get_blob_client(container=container, blob=blob_name)


def _upload_sync(contract_id: str, file_bytes: bytes, filename: str) -> str:
    blob_name = f"{contract_id}/{filename}"
    client = _get_blob_client(settings.AZURE_STORAGE_CONTAINER_NAME, blob_name)
    client.upload_blob(file_bytes, overwrite=True)
    return client.url


def _download_sync(contract_id: str, filename: str) -> bytes:
    blob_name = f"{contract_id}/{filename}"
    client = _get_blob_client(settings.AZURE_STORAGE_CONTAINER_NAME, blob_name)
    stream = client.download_blob()
    return stream.readall()


def _delete_sync(contract_id: str, filename: str) -> None:
    blob_name = f"{contract_id}/{filename}"
    client = _get_blob_client(settings.AZURE_STORAGE_CONTAINER_NAME, blob_name)
    client.delete_blob()


async def upload_contract(contract_id: str, file_bytes: bytes, filename: str) -> str:
    """Upload contract bytes to Azure Blob Storage. Returns the blob URL."""
    loop = asyncio.get_event_loop()
    try:
        url: str = await loop.run_in_executor(
            None, partial(_upload_sync, contract_id, file_bytes, filename)
        )
        logger.info("storage.upload_complete", contract_id=contract_id, filename=filename)
        return url
    except Exception as exc:
        logger.error("storage.upload_failed", contract_id=contract_id, error=str(exc))
        raise StorageError(f"Failed to upload contract {contract_id}: {exc}") from exc


async def download_contract(contract_id: str, filename: str) -> bytes:
    """Download blob bytes from Azure Blob Storage."""
    loop = asyncio.get_event_loop()
    try:
        data: bytes = await loop.run_in_executor(
            None, partial(_download_sync, contract_id, filename)
        )
        logger.info("storage.download_complete", contract_id=contract_id, filename=filename)
        return data
    except Exception as exc:
        logger.error("storage.download_failed", contract_id=contract_id, error=str(exc))
        raise StorageError(f"Failed to download contract {contract_id}: {exc}") from exc


async def delete_contract(contract_id: str, filename: str) -> None:
    """Delete blob from Azure Blob Storage."""
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, partial(_delete_sync, contract_id, filename))
        logger.info("storage.delete_complete", contract_id=contract_id, filename=filename)
    except Exception as exc:
        logger.error("storage.delete_failed", contract_id=contract_id, error=str(exc))
        raise StorageError(f"Failed to delete contract {contract_id}: {exc}") from exc
