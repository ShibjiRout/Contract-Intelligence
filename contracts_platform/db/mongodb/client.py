import asyncio

import certifi
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from contracts_platform.core.config import settings

_client: AsyncIOMotorClient | None = None
_client_loop: asyncio.AbstractEventLoop | None = None


def _get_client_options() -> dict[str, str]:
    """Use an explicit CA bundle for TLS-backed MongoDB connections."""
    mongodb_url = settings.MONGODB_URL.lower()
    if mongodb_url.startswith("mongodb+srv://") or "tls=true" in mongodb_url or "ssl=true" in mongodb_url:
        return {"tlsCAFile": certifi.where()}
    return {}


async def get_database() -> AsyncIOMotorDatabase:
    global _client, _client_loop
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if _client is None or _client_loop is not current_loop:
        if _client is not None:
            _client.close()
        _client = AsyncIOMotorClient(settings.MONGODB_URL, **_get_client_options())
        _client_loop = current_loop
    return _client[settings.MONGODB_DB_NAME]


async def close_database() -> None:
    global _client, _client_loop
    if _client:
        _client.close()
        _client = None
        _client_loop = None
