from contracts_platform.core.logging import logger
from contracts_platform.db.neo4j.repositories import contract_graph_repo, party_repo
from contracts_platform.orchestration.state import ContractReviewState

_CONFLICT_SCORE_MAP = {0: 0.0, 1: 0.4, 2: 0.7}


def _conflict_score(conflict_count: int) -> float:
    if conflict_count >= 3:
        return 1.0
    return _CONFLICT_SCORE_MAP.get(conflict_count, 0.0)


async def graph_check_node(state: ContractReviewState) -> dict:
    """
    Query Neo4j for counterparty risk history using party_repo and contract_graph_repo.
    Score based on conflict count: 0 -> 0.0, 1 -> 0.4, 2 -> 0.7, 3+ -> 1.0
    On exception: degraded_mode=True, add 'neo4j' to failed_sources.
    """
    contract_id = state["contract_id"]
    clause_id = state["clause_id"]
    clause_type = state["clause_type"]

    logger.info(
        "graph_check_node.start",
        contract_id=contract_id,
        clause_id=clause_id,
        clause_type=clause_type,
    )

    try:
        parties = state.get("parties_mentioned") or []
        party_id = parties[0] if parties else None
        if not party_id:
            return {"graph_result": {"score": 0.0, "conflict_count": 0, "conflicts": []}}

        conflict_count = await contract_graph_repo.get_cross_contract_conflicts(
            party_id=party_id,
            clause_type=clause_type,
        )

        risk_history = await party_repo.get_party_risk_history(party_id=party_id)
        counterparty_flags = sum(
            1 for entry in risk_history if entry.get("outcome") in ("REJECTED", "RED")
        )

        score = _conflict_score(conflict_count)

        logger.info(
            "graph_check_node.complete",
            contract_id=contract_id,
            clause_id=clause_id,
            conflict_count=conflict_count,
            counterparty_flags=counterparty_flags,
            score=score,
        )

        return {
            "graph_result": {
                "score": score,
                "conflict_count": conflict_count,
                "counterparty_flags": counterparty_flags,
            }
        }

    except Exception as exc:
        logger.error(
            "graph_check_node.failed",
            contract_id=contract_id,
            clause_id=clause_id,
            error=str(exc),
        )
        failed_sources = list(state.get("failed_sources") or [])
        if "neo4j" not in failed_sources:
            failed_sources.append("neo4j")
        return {
            "degraded_mode": True,
            "failed_sources": failed_sources,
            "graph_result": None,
        }
