from __future__ import annotations

import structlog
from opentelemetry import trace

from contracts_platform.orchestration.state import ContractReviewState
from contracts_platform.pipeline.recommendation import wording_retriever, generator

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)


async def recommendation_node(state: ContractReviewState) -> dict:
    """Generate a recommendation and suggested fix for a non-GREEN clause."""
    contract_id = state["contract_id"]
    clause_id = state["clause_id"]
    clause_type = state["clause_type"]
    clause_text = state["clause_text"]
    risk_indicators = state.get("risk_indicators") or []
    tenant_id = state["tenant_id"]

    with tracer.start_as_current_span("recommendation_node") as span:
        span.set_attribute("contract_id", contract_id)
        span.set_attribute("clause_id", clause_id)
        span.set_attribute("clause_type", clause_type)

        try:
            accepted_examples = await wording_retriever.retrieve_accepted_wording(
                tenant_id, clause_type, clause_text
            )

            result = await generator.generate_recommendation(
                clause_text, clause_type, risk_indicators, accepted_examples
            )

            recommendation: str = result.get("recommendation", "")
            suggested_fix: str | None = result.get("suggested_fix")

            logger.info(
                "recommendation_node.success",
                contract_id=contract_id,
                clause_id=clause_id,
            )

            return {
                "recommendation": recommendation,
                "suggested_fix": suggested_fix,
            }

        except Exception as exc:
            logger.error(
                "recommendation_node.error",
                contract_id=contract_id,
                clause_id=clause_id,
                error=str(exc),
                exc_info=True,
            )
            span.record_exception(exc)
            return {
                "recommendation": "Unable to generate recommendation.",
                "suggested_fix": None,
            }
