"""Integration tests for LangGraph graph compilation and risk calculator integration."""
import os

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017")
os.environ.setdefault("POSTGRES_DSN", "postgresql+asyncpg://postgres:postgres@localhost:5432/test")
os.environ.setdefault("NEO4J_URL", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "testpass")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault(
    "AZURE_STORAGE_CONNECTION_STRING",
    "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=dGVzdA==;EndpointSuffix=core.windows.net",
)
os.environ.setdefault(
    "AZURE_FILE_SHARE_CONNECTION_STRING",
    "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=dGVzdA==;EndpointSuffix=core.windows.net",
)
os.environ.setdefault("AZURE_FILE_SHARE_NAME", "test")
os.environ.setdefault("AZURE_STORAGE_CONTAINER_NAME", "test")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-for-ci-only")
os.environ.setdefault("ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS1mb3ItY2ktb25seQ==")

import pytest


def test_graph_compiles():
    """Verify build_graph() returns a StateGraph without error."""
    from contracts_platform.orchestration.graph import build_graph

    graph = build_graph()
    assert graph is not None


def test_risk_calculator_integration_red():
    """End-to-end: high scores + custom weights → RED."""
    from contracts_platform.orchestration.scoring.risk_calculator import calculate_risk

    score, level = calculate_risk(
        0.8, 0.8, 0.8, {"postgresql": 0.5, "qdrant": 0.3, "neo4j": 0.2}
    )
    assert level == "RED"
    assert score >= 0.7


def test_risk_calculator_integration_green():
    """End-to-end: low scores + custom weights → GREEN."""
    from contracts_platform.orchestration.scoring.risk_calculator import calculate_risk

    score, level = calculate_risk(
        0.1, 0.1, 0.1, {"postgresql": 0.5, "qdrant": 0.3, "neo4j": 0.2}
    )
    assert level == "GREEN"
    assert score < 0.4


def test_risk_calculator_integration_amber():
    """End-to-end: medium scores → AMBER."""
    from contracts_platform.orchestration.scoring.risk_calculator import calculate_risk

    score, level = calculate_risk(
        0.5, 0.5, 0.5, {"postgresql": 0.5, "qdrant": 0.3, "neo4j": 0.2}
    )
    assert level == "AMBER"
    assert 0.4 <= score < 0.7


def test_graph_has_expected_nodes():
    """Verify build_graph() produces a graph containing all required node names."""
    from contracts_platform.orchestration.graph import build_graph

    graph = build_graph()
    # StateGraph stores nodes in its internal graph builder
    node_names = set(graph.nodes.keys())
    required_nodes = {
        "playbook_check",
        "vector_check",
        "graph_check",
        "risk_aggregator",
        "recommendation",
        "explainability",
    }
    assert required_nodes.issubset(node_names)
