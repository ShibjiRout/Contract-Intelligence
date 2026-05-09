from __future__ import annotations

import structlog
from qdrant_client.models import FieldCondition, Filter, MatchValue, PointStruct

logger = structlog.get_logger(__name__)


async def search_similar_clauses(
    client,
    collection_name: str,
    embedding: list[float],
    limit: int = 5,
) -> list[dict]:
    """Search by vector similarity and return scored results with payloads.

    Returns a list of dicts with keys: clause_id, score, payload.
    """
    results = await client.search(
        collection_name=collection_name,
        query_vector=embedding,
        limit=limit,
        with_payload=True,
    )
    hits = [
        {
            "clause_id": r.payload.get("clause_id") if r.payload else None,
            "score": r.score,
            "payload": r.payload or {},
        }
        for r in results
    ]
    logger.info(
        "clause_repo.search_similar_clauses",
        collection_name=collection_name,
        limit=limit,
        returned=len(hits),
    )
    return hits


async def upsert_clause(
    client,
    collection_name: str,
    clause_id: str,
    embedding: list[float],
    payload: dict,
) -> None:
    """Upsert a single clause vector into the given collection."""
    await client.upsert(
        collection_name=collection_name,
        points=[PointStruct(id=clause_id, vector=embedding, payload=payload)],
    )
    logger.info(
        "clause_repo.upsert_clause",
        collection_name=collection_name,
        clause_id=clause_id,
    )


async def get_accepted_wording(
    client,
    collection_name: str,
    clause_type: str,
    limit: int = 3,
) -> list[str]:
    """Return raw_text strings for accepted clauses of the given type.

    Filters payload on clause_type == clause_type and status == "accepted".
    Points that have no raw_text in their payload are silently skipped.
    """
    results = await client.scroll(
        collection_name=collection_name,
        scroll_filter=Filter(
            must=[
                FieldCondition(key="clause_type", match=MatchValue(value=clause_type)),
                FieldCondition(key="status", match=MatchValue(value="accepted")),
            ]
        ),
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )
    # scroll() returns a tuple (list[Record], next_page_offset)
    records = results[0] if isinstance(results, tuple) else results
    texts: list[str] = []
    for record in records:
        payload = record.payload or {}
        raw_text = payload.get("raw_text")
        if raw_text:
            texts.append(raw_text)
    logger.info(
        "clause_repo.get_accepted_wording",
        collection_name=collection_name,
        clause_type=clause_type,
        returned=len(texts),
    )
    return texts
