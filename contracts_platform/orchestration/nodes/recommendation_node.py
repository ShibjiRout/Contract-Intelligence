from contracts_platform.core.logging import logger
from contracts_platform.orchestration.state import ContractReviewState


async def recommendation_node(state: ContractReviewState) -> dict:
    """
    Stub — real implementation wired in by llm-pipeline-agent.
    Logs that recommendation was triggered for contract_id + clause_id.
    Returns placeholder recommendation with suggested_fix as None.
    """
    contract_id = state["contract_id"]
    clause_id = state["clause_id"]
    risk_level = state.get("risk_level", "UNKNOWN")

    logger.info(
        "recommendation_node.triggered",
        contract_id=contract_id,
        clause_id=clause_id,
        risk_level=risk_level,
    )

    return {
        "recommendation": "Recommendation pending LLM processing.",
        "suggested_fix": None,
    }
