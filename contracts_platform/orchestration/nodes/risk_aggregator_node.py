from contracts_platform.core.logging import logger
from contracts_platform.orchestration.scoring import risk_calculator, weights as weights_module
from contracts_platform.orchestration.state import ContractReviewState

_DEGRADED_DEFAULT_SCORE = 0.5


async def risk_aggregator_node(state: ContractReviewState) -> dict:
    """
    1. Load weights from scoring/weights.py
    2. Extract scores from playbook_result, vector_result, graph_result
       (use 0.5 as default for any None result due to degraded mode)
    3. Call risk_calculator.calculate_risk()
    4. Return {"risk_level": str, "risk_score": float}
    """
    contract_id = state["contract_id"]
    clause_id = state["clause_id"]
    jurisdiction = state["jurisdiction"]

    logger.info(
        "risk_aggregator_node.start",
        contract_id=contract_id,
        clause_id=clause_id,
        jurisdiction=jurisdiction,
    )

    try:
        from contracts_platform.db.postgresql.client import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            current_weights = await weights_module.get_weights(jurisdiction, session)
    except Exception as exc:
        logger.warning(
            "risk_aggregator_node.weights_fallback",
            contract_id=contract_id,
            error=str(exc),
        )
        current_weights = weights_module.DEFAULT_WEIGHTS

    playbook_result = state.get("playbook_result")
    vector_result = state.get("vector_result")
    graph_result = state.get("graph_result")

    playbook_score = (
        playbook_result["score"] if playbook_result is not None else _DEGRADED_DEFAULT_SCORE
    )
    vector_score = (
        vector_result["score"] if vector_result is not None else _DEGRADED_DEFAULT_SCORE
    )
    graph_score = (
        graph_result["score"] if graph_result is not None else _DEGRADED_DEFAULT_SCORE
    )

    risk_score, risk_level = risk_calculator.calculate_risk(
        playbook_score=playbook_score,
        vector_score=vector_score,
        graph_score=graph_score,
        weights=current_weights,
    )

    logger.info(
        "risk_aggregator_node.complete",
        contract_id=contract_id,
        clause_id=clause_id,
        risk_level=risk_level,
        risk_score=risk_score,
        playbook_score=playbook_score,
        vector_score=vector_score,
        graph_score=graph_score,
    )

    return {"risk_level": risk_level, "risk_score": risk_score}
