from __future__ import annotations

from contracts_platform.core.logging import logger
from contracts_platform.db.neo4j.repositories.contract_graph_repo import get_accepted_precedents
from contracts_platform.orchestration.state import ContractReviewState


async def precedent_check_node(state: ContractReviewState) -> dict:
    """
    Step 3: Query Neo4j to find if parties in this contract have previously
    accepted a clause of the same type.

    Returns the most recent accepted precedent:
    e.g. {"party": "Acme Ltd", "date": "2026-03-10", "contract_id": "xyz-123"}
    """
    contract_id = state["contract_id"]
    clause_id = state["clause_id"]
    clause_type = state["clause_type"]
    tenant_id = state.get("tenant_id", "")

    logger.info(
        "precedent_check_node.start",
        contract_id=contract_id,
        clause_id=clause_id,
        clause_type=clause_type,
    )

    try:
        precedents = await get_accepted_precedents(
            contract_id=contract_id,
            tenant_id=tenant_id,
            clause_type=clause_type,
        )

        if precedents:
            # Return the most recent precedent
            precedent = precedents[0]
            logger.info(
                "precedent_check_node.found",
                contract_id=contract_id,
                clause_id=clause_id,
                party=precedent.get("party_name"),
                accepted_at=precedent.get("accepted_at"),
            )
            return {
                "precedent": {
                    "party": precedent.get("party_name"),
                    "date": precedent.get("accepted_at"),
                    "contract_id": precedent.get("contract_id"),
                }
            }

        logger.info(
            "precedent_check_node.no_precedent",
            contract_id=contract_id,
            clause_id=clause_id,
        )
        return {"precedent": None}

    except Exception as exc:
        logger.error(
            "precedent_check_node.failed",
            contract_id=contract_id,
            clause_id=clause_id,
            error=str(exc),
        )
        failed_sources = list(state.get("failed_sources") or [])
        failed_sources.append("neo4j")
        return {
            "precedent": None,
            "failed_sources": failed_sources,
        }
