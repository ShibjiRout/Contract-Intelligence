from contracts_platform.core.logging import logger
from contracts_platform.orchestration.scoring.weights import DEFAULT_WEIGHTS
from contracts_platform.orchestration.state import ContractReviewState


def _impact_label(contribution: float) -> str:
    """Map a score contribution to HIGH / MEDIUM / LOW."""
    if contribution >= 0.3:
        return "HIGH"
    elif contribution >= 0.15:
        return "MEDIUM"
    return "LOW"


async def explainability_node(state: ContractReviewState) -> dict:
    """
    Build the explanation dict from the aggregated state.
    Maps source scores and weights to impact levels.
    """
    contract_id = state["contract_id"]
    clause_id = state["clause_id"]
    risk_level = state.get("risk_level", "UNKNOWN")
    risk_score = state.get("risk_score", 0.0)
    failed_sources: list[str] = state.get("failed_sources") or []
    degraded_mode: bool = state.get("degraded_mode", False)

    logger.info(
        "explainability_node.start",
        contract_id=contract_id,
        clause_id=clause_id,
        risk_level=risk_level,
    )

    # Retrieve source results (may be None in degraded mode)
    playbook_result = state.get("playbook_result") or {}
    vector_result = state.get("vector_result") or {}
    graph_result = state.get("graph_result") or {}

    # Best-effort weights — use defaults if missing
    # (weights are not stored in state; use defaults for explainability)
    wt_pg = DEFAULT_WEIGHTS["postgresql"]
    wt_qd = DEFAULT_WEIGHTS["qdrant"]
    wt_n4 = DEFAULT_WEIGHTS["neo4j"]

    pg_score = playbook_result.get("score", 0.5)
    qd_score = vector_result.get("score", 0.5)
    n4_score = graph_result.get("score", 0.5)

    pg_contribution = pg_score * wt_pg
    qd_contribution = qd_score * wt_qd
    n4_contribution = n4_score * wt_n4

    pg_findings = playbook_result.get("findings", [])
    pg_summary = "; ".join(pg_findings) if pg_findings else "No playbook violations found."
    qd_summary = (
        f"{vector_result.get('similar_rejected', 0)} similar rejected clauses found."
        if vector_result
        else "Qdrant data unavailable."
    )
    n4_summary = (
        f"{graph_result.get('conflict_count', 0)} cross-contract conflicts; "
        f"{graph_result.get('counterparty_flags', 0)} counterparty risk flags."
        if graph_result
        else "Neo4j data unavailable."
    )

    explanation = {
        "overall_risk": risk_level,
        "score": risk_score,
        "contributing_factors": [
            {
                "source": "postgresql",
                "finding": pg_summary,
                "weight": wt_pg,
                "impact": _impact_label(pg_contribution),
            },
            {
                "source": "qdrant",
                "finding": qd_summary,
                "weight": wt_qd,
                "impact": _impact_label(qd_contribution),
            },
            {
                "source": "neo4j",
                "finding": n4_summary,
                "weight": wt_n4,
                "impact": _impact_label(n4_contribution),
            },
        ],
        "missing_clauses": state.get("missing_clauses") or [],
        "conflicts": [],
        "degraded_mode": degraded_mode,
        "failed_sources": failed_sources,
    }

    logger.info(
        "explainability_node.complete",
        contract_id=contract_id,
        clause_id=clause_id,
        risk_level=risk_level,
        degraded_mode=degraded_mode,
    )

    return {"explanation": explanation}
