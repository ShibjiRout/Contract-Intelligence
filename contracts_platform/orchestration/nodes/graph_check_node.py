from contracts_platform.core.logging import logger
from contracts_platform.db.neo4j.client import get_driver
from contracts_platform.db.neo4j.repositories import party_repo
from contracts_platform.orchestration.state import ContractReviewState


async def graph_check_node(state: ContractReviewState) -> dict:
    """
    Compare the contract's Clause node against PlaybookRule nodes in Neo4j.

    Two checks:
    1. Playbook match — find PlaybookRule nodes for this clause_type + jurisdiction.
       For each REQUIRED rule: is its description present in clause_text?
       For each FORBIDDEN rule: is its description present in clause_text?
    2. Counterparty history — how many times has this party been REJECTED on
       the same clause_type in past contracts?

    Score = weighted combination of rule violations + counterparty flags.
    """
    contract_id = state["contract_id"]
    clause_id = state["clause_id"]
    clause_type = state["clause_type"]
    clause_text = state["clause_text"]
    jurisdiction = state["jurisdiction"]

    logger.info(
        "graph_check_node.start",
        contract_id=contract_id,
        clause_id=clause_id,
        clause_type=clause_type,
        jurisdiction=jurisdiction,
    )

    try:
        driver = await get_driver()
        violations: list[str] = []
        playbook_rules_checked = 0

        # ── Check 1: contract Clause node vs PlaybookRule nodes ──────────────
        async with driver.session() as session:
            result = await session.run(
                """
                MATCH (cl:Clause {clause_id: $clause_id})
                MATCH (r:PlaybookRule)-[:GOVERNS]->(:ClauseType {name: $clause_type})
                MATCH (r)-[:APPLIES_TO]->(:Jurisdiction {code: $jurisdiction})
                RETURN r.rule_type AS rule_type, r.description AS description
                """,
                clause_id=clause_id,
                clause_type=clause_type,
                jurisdiction=jurisdiction,
            )
            rows = [dict(r) async for r in result]

        playbook_rules_checked = len(rows)
        for row in rows:
            rule_type = row.get("rule_type", "")
            description = (row.get("description") or "").lower()
            if not description:
                continue
            if rule_type == "REQUIRED" and description not in clause_text.lower():
                violations.append(f"REQUIRED rule missing in clause: {row['description']}")
            elif rule_type == "FORBIDDEN" and description in clause_text.lower():
                violations.append(f"FORBIDDEN term present in clause: {row['description']}")

        # ── Check 2: counterparty risk history ────────────────────────────────
        counterparty_flags = 0
        async with driver.session() as session:
            result = await session.run(
                """
                MATCH (c:Contract {contract_id: $contract_id})<-[:REVIEWED_BY]-(p:Party)
                MATCH (p)-[r:REVIEWED_BY]->(prev:Contract)
                MATCH (prev)-[:CONTAINS]->(cl:Clause {type: $clause_type})
                WHERE r.outcome IN ['rejected', 'REJECTED']
                RETURN count(r) AS flag_count
                """,
                contract_id=contract_id,
                clause_type=clause_type,
            )
            row = await result.single()
            counterparty_flags = row["flag_count"] if row else 0

        # ── Score ─────────────────────────────────────────────────────────────
        # violations contribute 0.6 weight, counterparty history 0.4
        violation_score = min(1.0, len(violations) / max(playbook_rules_checked, 1))
        counterparty_score = min(1.0, counterparty_flags / 3)
        score = round(violation_score * 0.6 + counterparty_score * 0.4, 4)

        logger.info(
            "graph_check_node.complete",
            contract_id=contract_id,
            clause_id=clause_id,
            playbook_rules_checked=playbook_rules_checked,
            violations=len(violations),
            counterparty_flags=counterparty_flags,
            score=score,
        )

        return {
            "graph_result": {
                "score": score,
                "playbook_rules_checked": playbook_rules_checked,
                "violations": violations,
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
