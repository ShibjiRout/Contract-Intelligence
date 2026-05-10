"""Integration tests for the sequential LangGraph pipeline."""
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
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("QDRANT_API_KEY", "")

import pytest


def test_graph_compiles():
    """build_graph() returns a compiled StateGraph without error."""
    from contracts_platform.orchestration.graph import build_graph

    graph = build_graph()
    assert graph is not None


def test_graph_has_sequential_nodes():
    """Graph contains exactly the 5 sequential nodes — no old parallel nodes."""
    from contracts_platform.orchestration.graph import build_graph

    graph = build_graph()
    node_names = set(graph.nodes.keys())

    required = {
        "intent_extraction",
        "gap_analysis",
        "precedent_check",
        "playbook_score",
        "recommendation",
    }
    assert required.issubset(node_names), f"Missing nodes: {required - node_names}"

    # Old parallel nodes must NOT exist
    removed = {"playbook_check", "vector_check", "graph_check", "risk_aggregator", "explainability"}
    present = removed & node_names
    assert not present, f"Old nodes still in graph: {present}"


def test_state_has_new_fields():
    """ContractReviewState TypedDict has all new fields."""
    from contracts_platform.orchestration.state import ContractReviewState
    import typing

    hints = typing.get_type_hints(ContractReviewState)
    for field in [
        "legal_intent",
        "gap_summary",
        "precedent",
        "risk_category",
        "violation_message",
        "ai_recommendation",
        "failed_sources",
    ]:
        assert field in hints, f"Missing field in state: {field}"


def test_playbook_score_node_green():
    """playbook_score_node returns GREEN when no rules match."""
    import asyncio
    from unittest.mock import AsyncMock, patch

    state = {
        "contract_id": "c1",
        "clause_id": "cl1",
        "clause_type": "liability",
        "clause_text": "Standard liability clause with full indemnification.",
        "jurisdiction": "UK",
        "tenant_id": "t1",
        "failed_sources": [],
    }

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "contracts_platform.orchestration.nodes.playbook_score_node.get_fresh_session_factory",
        return_value=lambda: mock_session,
    ), patch(
        "contracts_platform.orchestration.nodes.playbook_score_node.get_rules_for_jurisdiction",
        new=AsyncMock(return_value=[]),
    ):
        from contracts_platform.orchestration.nodes.playbook_score_node import playbook_score_node

        result = asyncio.get_event_loop().run_until_complete(playbook_score_node(state))

    assert result["risk_category"] == "GREEN"
    assert result["violation_message"] is None


def test_playbook_score_node_red():
    """playbook_score_node returns RED when forbidden term found with high weight."""
    import asyncio
    from unittest.mock import AsyncMock, patch

    state = {
        "contract_id": "c1",
        "clause_id": "cl1",
        "clause_type": "liability",
        "clause_text": "no liability whatsoever for any damages",
        "jurisdiction": "UK",
        "tenant_id": "t1",
        "failed_sources": [],
    }

    rules = [
        {"rule_type": "FORBIDDEN", "description": "no liability", "weight": 1.0, "violation_message": ""},
    ]

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "contracts_platform.orchestration.nodes.playbook_score_node.get_fresh_session_factory",
        return_value=lambda: mock_session,
    ), patch(
        "contracts_platform.orchestration.nodes.playbook_score_node.get_rules_for_jurisdiction",
        new=AsyncMock(return_value=rules),
    ):
        from contracts_platform.orchestration.nodes.playbook_score_node import playbook_score_node

        result = asyncio.get_event_loop().run_until_complete(playbook_score_node(state))

    assert result["risk_category"] == "RED"
    assert "FORBIDDEN" in result["violation_message"]


def test_precedent_check_node_no_data():
    """precedent_check_node returns None precedent when Neo4j has no history."""
    import asyncio
    from unittest.mock import AsyncMock, patch

    state = {
        "contract_id": "c1",
        "clause_id": "cl1",
        "clause_type": "liability",
        "tenant_id": "t1",
        "failed_sources": [],
    }

    with patch(
        "contracts_platform.orchestration.nodes.precedent_check_node.get_accepted_precedents",
        new=AsyncMock(return_value=[]),
    ):
        from contracts_platform.orchestration.nodes.precedent_check_node import precedent_check_node

        result = asyncio.get_event_loop().run_until_complete(precedent_check_node(state))

    assert result["precedent"] is None


def test_precedent_check_node_with_data():
    """precedent_check_node returns most recent precedent when Neo4j has history."""
    import asyncio
    from unittest.mock import AsyncMock, patch

    state = {
        "contract_id": "c1",
        "clause_id": "cl1",
        "clause_type": "liability",
        "tenant_id": "t1",
        "failed_sources": [],
    }

    neo4j_data = [
        {"party_name": "Acme Ltd", "accepted_at": "2026-03-10", "contract_id": "old-c1"},
        {"party_name": "Acme Ltd", "accepted_at": "2025-11-01", "contract_id": "old-c0"},
    ]

    with patch(
        "contracts_platform.orchestration.nodes.precedent_check_node.get_accepted_precedents",
        new=AsyncMock(return_value=neo4j_data),
    ):
        from contracts_platform.orchestration.nodes.precedent_check_node import precedent_check_node

        result = asyncio.get_event_loop().run_until_complete(precedent_check_node(state))

    assert result["precedent"]["party"] == "Acme Ltd"
    assert result["precedent"]["date"] == "2026-03-10"
    assert result["precedent"]["contract_id"] == "old-c1"


def test_precedent_check_node_neo4j_failure():
    """precedent_check_node degrades gracefully when Neo4j is down."""
    import asyncio
    from unittest.mock import AsyncMock, patch

    state = {
        "contract_id": "c1",
        "clause_id": "cl1",
        "clause_type": "liability",
        "tenant_id": "t1",
        "failed_sources": [],
    }

    with patch(
        "contracts_platform.orchestration.nodes.precedent_check_node.get_accepted_precedents",
        new=AsyncMock(side_effect=ConnectionError("neo4j down")),
    ):
        from contracts_platform.orchestration.nodes.precedent_check_node import precedent_check_node

        result = asyncio.get_event_loop().run_until_complete(precedent_check_node(state))

    assert result["precedent"] is None
    assert "neo4j" in result["failed_sources"]
