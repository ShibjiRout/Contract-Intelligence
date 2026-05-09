from contracts_platform.core.constants import RiskLevel


def calculate_risk(
    playbook_score: float,
    vector_score: float,
    graph_score: float,
    weights: dict[str, float],
) -> tuple[float, str]:
    """
    Weighted sum of scores (each 0.0-1.0 where 1.0 = highest risk).
    Returns (weighted_score, risk_level_str).
    Thresholds: score >= 0.7 -> RED, score >= 0.4 -> AMBER, else -> GREEN
    """
    weighted_score = (
        playbook_score * weights.get("postgresql", 0.5)
        + vector_score * weights.get("qdrant", 0.3)
        + graph_score * weights.get("neo4j", 0.2)
    )
    # Clamp to [0.0, 1.0]
    weighted_score = max(0.0, min(1.0, weighted_score))

    if weighted_score >= 0.7:
        risk_level = RiskLevel.RED.value
    elif weighted_score >= 0.4:
        risk_level = RiskLevel.AMBER.value
    else:
        risk_level = RiskLevel.GREEN.value

    return weighted_score, risk_level
