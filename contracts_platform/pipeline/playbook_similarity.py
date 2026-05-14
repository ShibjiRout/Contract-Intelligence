from __future__ import annotations

import structlog

from contracts_platform.db.qdrant.repositories.clause_vector_repo import search_collection
from contracts_platform.pipeline.embedder import embed_text

logger = structlog.get_logger()

PLAYBOOK_COLLECTION = "clauses_playbook"
AUTO_ACCEPT_THRESHOLD = 0.90


async def should_auto_accept_contract(
    text: str,
    threshold: float = AUTO_ACCEPT_THRESHOLD,
) -> tuple[bool, float]:
    """Compare full OCR text against the playbook vector store.

    This is a coarse document-level pre-check used immediately after OCR.
    If the top playbook similarity is >= threshold, downstream clause extraction
    can auto-approve the extracted clauses without changing the fallback path.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return False, 0.0

    vector = await embed_text(cleaned)
    results = await search_collection(PLAYBOOK_COLLECTION, vector, limit=1)
    top_score = float(results[0]["score"]) if results else 0.0

    logger.info(
        "playbook_similarity.checked",
        collection=PLAYBOOK_COLLECTION,
        top_score=top_score,
        threshold=threshold,
    )
    return top_score >= threshold, top_score
