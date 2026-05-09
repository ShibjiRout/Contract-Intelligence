from __future__ import annotations

import structlog
from openai import AsyncOpenAI
from opentelemetry import trace

from contracts_platform.core.config import settings
from contracts_platform.db.qdrant.repositories import clause_vector_repo
from contracts_platform.orchestration.state import ContractReviewState

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)

_openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def vector_check_node(state: ContractReviewState) -> dict:
    """Search Qdrant for similar clauses that were previously REJECTED."""
    contract_id = state["contract_id"]
    clause_id = state["clause_id"]
    clause_type = state["clause_type"]
    clause_text = state["clause_text"]
    tenant_id = state["tenant_id"]

    with tracer.start_as_current_span("vector_check_node") as span:
        span.set_attribute("contract_id", contract_id)
        span.set_attribute("clause_id", clause_id)
        span.set_attribute("clause_type", clause_type)

        try:
            embedding_response = await _openai_client.embeddings.create(
                model=settings.EMBEDDING_MODEL,
                input=clause_text,
            )
            vector: list[float] = embedding_response.data[0].embedding
        except Exception as embed_exc:
            logger.error(
                "vector_check_node.embedding_error",
                contract_id=contract_id,
                clause_id=clause_id,
                source="qdrant",
                error=str(embed_exc),
                exc_info=True,
            )
            span.record_exception(embed_exc)
            failed_sources = list(state.get("failed_sources") or [])
            if "qdrant" not in failed_sources:
                failed_sources.append("qdrant")
            return {
                "vector_result": None,
                "degraded_mode": True,
                "failed_sources": failed_sources,
            }

        try:
            results = await clause_vector_repo.search_similar(
                tenant_id=tenant_id,
                vector=vector,
                clause_type=clause_type,
                status="rejected",
                limit=5,
            )

            similar_rejected = len(results)
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
                source="qdrant",
                error=str(exc),
                exc_info=True,
            )
            span.record_exception(exc)
            failed_sources = list(state.get("failed_sources") or [])
            if "qdrant" not in failed_sources:
                failed_sources.append("qdrant")
            return {
                "degraded_mode": True,
                "failed_sources": failed_sources,
                "vector_result": None,
            }
