import pytest

from contracts_platform.db.neo4j.repositories import clause_graph_repo, contract_graph_repo
from contracts_platform.orchestration.nodes import graph_check_node


class _Summary:
    class counters:
        nodes_deleted = 1


class _Result:
    def __init__(self, rows=None):
        self._rows = rows or []

    def __aiter__(self):
        self._iter = iter(self._rows)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration as exc:
            raise StopAsyncIteration from exc

    async def consume(self):
        return _Summary()


class _Session:
    def __init__(self, capture, rows=None):
        self.capture = capture
        self.rows = rows or []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def run(self, query, **params):
        self.capture.append((query, params))
        return _Result(self.rows)


class _Driver:
    def __init__(self, capture, rows=None):
        self.capture = capture
        self.rows = rows or []

    def session(self):
        return _Session(self.capture, self.rows)


@pytest.mark.asyncio
async def test_create_contract_node_uses_merge(monkeypatch):
    capture = []

    async def fake_get_driver():
        return _Driver(capture)

    monkeypatch.setattr(contract_graph_repo, "get_driver", fake_get_driver)

    await contract_graph_repo.create_contract_node("c1", "t1", "contract.pdf", "UK", "UPLOADED")

    query, params = capture[0]
    assert "MERGE (c:Contract" in query
    assert params["tenant_id"] == "t1"


@pytest.mark.asyncio
async def test_link_party_to_contract_uses_party_to(monkeypatch):
    capture = []

    async def fake_get_driver():
        return _Driver(capture)

    monkeypatch.setattr(contract_graph_repo, "get_driver", fake_get_driver)

    await contract_graph_repo.link_party_to_contract("p1", "c1", "supplier")

    query, params = capture[0]
    assert "MERGE (p)-[r:PARTY_TO]->(c)" in query
    assert params["role"] == "supplier"


@pytest.mark.asyncio
async def test_create_clause_node_links_contract_to_clause(monkeypatch):
    capture = []

    async def fake_get_driver():
        return _Driver(capture)

    monkeypatch.setattr(clause_graph_repo, "get_driver", fake_get_driver)

    await clause_graph_repo.create_clause_node("cl1", "c1", "t1", "LIABILITY", "RED", 0.9)

    query, params = capture[0]
    assert "MERGE (cl:Clause" in query
    assert "MERGE (c)-[:CONTAINS]->(cl)" in query
    assert params["risk_score"] == 0.9


@pytest.mark.asyncio
async def test_graph_check_scores_party_history(monkeypatch):
    async def fake_history(contract_id, tenant_id, clause_type):
        return [{"party_name": "Acme", "party_id": "p1", "risky_history": 2}]

    monkeypatch.setattr(
        graph_check_node,
        "get_contract_party_risky_clause_history",
        fake_history,
    )

    result = await graph_check_node.graph_check_node(
        {
            "contract_id": "c1",
            "clause_id": "cl1",
            "clause_type": "LIABILITY",
            "tenant_id": "t1",
        }
    )

    assert result["graph_result"]["risky_history"] == 2
    assert result["graph_result"]["score"] == 0.6667
