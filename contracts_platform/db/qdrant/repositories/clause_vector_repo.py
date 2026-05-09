from datetime import datetime, timedelta, timezone
from qdrant_client.models import Filter, FieldCondition, MatchValue, PointStruct
from qdrant_client import models as qdrant_models
from contracts_platform.db.qdrant.client import get_qdrant_client
from contracts_platform.core.logging import logger


def _collection(tenant_id: str) -> str:
    return f"clauses_{tenant_id}"


async def upsert_clause(tenant_id: str, clause_id: str, vector: list[float], payload: dict) -> None:
    client = get_qdrant_client()
    await client.upsert(
        collection_name=_collection(tenant_id),
        points=[PointStruct(id=clause_id, vector=vector, payload=payload)],
    )
    logger.info("qdrant.upsert", clause_id=clause_id, tenant_id=tenant_id)


async def search_similar(tenant_id: str, vector: list[float], clause_type: str, status: str = "accepted", limit: int = 3) -> list[dict]:
    client = get_qdrant_client()
    results = await client.search(
        collection_name=_collection(tenant_id),
        query_vector=vector,
        query_filter=Filter(must=[
            FieldCondition(key="clause_type", match=MatchValue(value=clause_type)),
            FieldCondition(key="status", match=MatchValue(value=status)),
        ]),
        limit=limit,
        with_payload=True,
    )
    return [{"score": r.score, "payload": r.payload} for r in results]


async def delete_clause(tenant_id: str, clause_id: str) -> None:
    client = get_qdrant_client()
    await client.delete(
        collection_name=_collection(tenant_id),
        points_selector=qdrant_models.PointIdsList(points=[clause_id]),
    )
    logger.info("qdrant.delete", clause_id=clause_id, tenant_id=tenant_id)


async def create_temp_collection(collection_name: str, vector_size: int = 1536) -> None:
    """Create a temporary Qdrant collection for RAG ingestion."""
    from qdrant_client.models import VectorParams, Distance
    client = get_qdrant_client()
    await client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )
    logger.info("qdrant.temp_collection.created", collection=collection_name)


async def upsert_chunk(collection_name: str, chunk_id: str, vector: list[float], payload: dict) -> None:
    """Upsert a raw text chunk into any Qdrant collection."""
    client = get_qdrant_client()
    await client.upsert(
        collection_name=collection_name,
        points=[PointStruct(id=chunk_id, vector=vector, payload=payload)],
    )


async def search_collection(collection_name: str, vector: list[float], limit: int = 5) -> list[dict]:
    """Vector search in any collection (not tenant-scoped)."""
    client = get_qdrant_client()
    results = await client.search(
        collection_name=collection_name,
        query_vector=vector,
        limit=limit,
    )
    return [{"score": r.score, "payload": r.payload} for r in results]


async def delete_temp_collection(collection_name: str) -> None:
    """Delete an ephemeral Qdrant collection after ingestion is complete."""
    client = get_qdrant_client()
    await client.delete_collection(collection_name=collection_name)
    logger.info("qdrant.temp_collection.deleted", collection=collection_name)


async def cleanup_stale(tenant_id: str, older_than_days: int = 30) -> int:
    client = get_qdrant_client()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=older_than_days)).isoformat()
    await client.delete(
        collection_name=_collection(tenant_id),
        points_selector=qdrant_models.FilterSelector(
            filter=Filter(must=[
                FieldCondition(key="status", match=MatchValue(value="rejected")),
                FieldCondition(key="created_at", range=qdrant_models.Range(lt=cutoff)),
            ])
        ),
    )
    logger.info("qdrant.cleanup_stale", tenant_id=tenant_id, older_than_days=older_than_days)
    return 0
