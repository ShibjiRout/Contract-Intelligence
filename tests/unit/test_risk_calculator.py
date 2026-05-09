"""Unit tests for calculate_risk() from orchestration.scoring.risk_calculator."""
import pytest

from contracts_platform.orchestration.scoring.risk_calculator import calculate_risk

DEFAULT_WEIGHTS = {"postgresql": 0.5, "qdrant": 0.3, "neo4j": 0.2}


def test_all_low_scores_green():
    """playbook=0.1, vector=0.1, graph=0.1, default weights → GREEN."""
    score, level = calculate_risk(0.1, 0.1, 0.1, DEFAULT_WEIGHTS)
    # weighted = 0.1*0.5 + 0.1*0.3 + 0.1*0.2 = 0.1
    assert level == "GREEN"
    assert score < 0.4


def test_all_high_scores_red():
    """playbook=1.0, vector=1.0, graph=1.0, default weights → RED."""
    score, level = calculate_risk(1.0, 1.0, 1.0, DEFAULT_WEIGHTS)
    assert level == "RED"
    assert score >= 0.7


def test_medium_scores_amber():
    """Scores around 0.5 → AMBER."""
    score, level = calculate_risk(0.5, 0.5, 0.5, DEFAULT_WEIGHTS)
    # weighted = 0.5 * (0.5+0.3+0.2) = 0.5
    assert level == "AMBER"
    assert 0.4 <= score < 0.7


def test_custom_weights_weighted_calculation():
    """Custom weights summing to 1.0 → verify correct weighted result."""
    weights = {"postgresql": 0.6, "qdrant": 0.3, "neo4j": 0.1}
    score, level = calculate_risk(0.8, 0.2, 0.1, weights)
    expected = 0.8 * 0.6 + 0.2 * 0.3 + 0.1 * 0.1
    assert abs(score - expected) < 1e-9
    # expected ~= 0.48 + 0.06 + 0.01 = 0.55 → AMBER
    assert level == "AMBER"


def test_score_clamp_high():
    """Scores > 1.0 passed in cause weighted sum > 1.0 which is clamped to 1.0."""
    score, level = calculate_risk(2.0, 2.0, 2.0, DEFAULT_WEIGHTS)
    assert score == 1.0
    assert level == "RED"


def test_score_clamp_low():
    """Negative scores result in weighted_score clamped to 0.0."""
    score, level = calculate_risk(-1.0, -1.0, -1.0, DEFAULT_WEIGHTS)
    assert score == 0.0
    assert level == "GREEN"


def test_threshold_boundary_red():
    """weighted_score exactly 0.7 → RED."""
    # Use equal weights 1/3 each and scores = 0.7 → weighted = 0.7
    weights = {"postgresql": 1 / 3, "qdrant": 1 / 3, "neo4j": 1 / 3}
    score, level = calculate_risk(0.7, 0.7, 0.7, weights)
    assert abs(score - 0.7) < 1e-9
    assert level == "RED"


def test_threshold_boundary_amber():
    """weighted_score exactly 0.4 → AMBER."""
    weights = {"postgresql": 1 / 3, "qdrant": 1 / 3, "neo4j": 1 / 3}
    score, level = calculate_risk(0.4, 0.4, 0.4, weights)
    assert abs(score - 0.4) < 1e-9
    assert level == "AMBER"


def test_threshold_just_below_red():
    """weighted_score of ~0.699 → AMBER, not RED."""
    weights = {"postgresql": 1 / 3, "qdrant": 1 / 3, "neo4j": 1 / 3}
    score, level = calculate_risk(0.699, 0.699, 0.699, weights)
    assert score < 0.7
    assert level == "AMBER"


def test_degraded_single_source():
    """Only playbook_score is reliable; others at 0.5 — still returns a valid result."""
    score, level = calculate_risk(0.9, 0.5, 0.5, DEFAULT_WEIGHTS)
    # weighted = 0.9*0.5 + 0.5*0.3 + 0.5*0.2 = 0.45 + 0.15 + 0.10 = 0.70
    assert level == "RED"
    assert score >= 0.7


def test_missing_weight_keys_use_defaults():
    """Missing weight keys fall back to the function's default get() values."""
    # Empty weights dict — defaults: postgresql=0.5, qdrant=0.3, neo4j=0.2
    score, level = calculate_risk(1.0, 1.0, 1.0, {})
    assert score == 1.0
    assert level == "RED"
