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
