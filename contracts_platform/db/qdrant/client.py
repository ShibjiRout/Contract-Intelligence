from qdrant_client import AsyncQdrantClient

from contracts_platform.core.config import settings


def get_qdrant_client() -> AsyncQdrantClient:
    return AsyncQdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None,
    )
