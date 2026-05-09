from contracts_platform.core.logging import logger
from contracts_platform.db.qdrant.repositories import clause_vector_repo
from contracts_platform.orchestration.state import ContractReviewState

# Zero vector used as placeholder until llm-pipeline-agent wires in real embeddings
_ZERO_VECTOR = [0.0] * 1536


async def vector_check_node(state: ContractReviewState) -> dict:
    """
    Search Qdrant for similar clauses that were previously REJECTED.
    Score = fraction of similar rejected clauses in top results.
    NOTE: Uses a zero vector of length 1536 as placeholder embedding.
          The llm-pipeline-agent will wire in real embeddings later.
    On exception: degraded_mode=True, add 'qdrant' to failed_sources.
    """
    contract_id = state["contract_id"]
    clause_id = state["clause_id"]
    clause_type = state["clause_type"]
    tenant_id = state["tenant_id"]

    logger.info(
        "vector_check_node.start",
        contract_id=contract_id,
        clause_id=clause_id,
        clause_type=clause_type,
        tenant_id=tenant_id,
    )

    try:
        results = await clause_vector_repo.search_similar(
            tenant_id=tenant_id,
            vector=_ZERO_VECTOR,
            clause_type=clause_type,
            status="rejected",
            limit=5,
        )

        similar_rejected = len(results)
        # Score = fraction of top-5 slots filled with rejected matches
        score = min(1.0, similar_rejected / 5)

        top_matches = [
            {"score": r["score"], "clause_id": r["payload"].get("clause_id")}
            for r in results
        ]

        logger.info(
            "vector_check_node.complete",
            contract_id=contract_id,
            clause_id=clause_id,
            similar_rejected=similar_rejected,
            score=score,
        )

        return {
            "vector_result": {
                "score": score,
                "similar_rejected": similar_rejected,
                "top_matches": top_matches,
            }
        }

    except Exception as exc:
        logger.error(
            "vector_check_node.failed",
            contract_id=contract_id,
            clause_id=clause_id,
            error=str(exc),
        )
        failed_sources = list(state.get("failed_sources") or [])
        if "qdrant" not in failed_sources:
            failed_sources.append("qdrant")
        return {
            "degraded_mode": True,
            "failed_sources": failed_sources,
            "vector_result": None,
        }
