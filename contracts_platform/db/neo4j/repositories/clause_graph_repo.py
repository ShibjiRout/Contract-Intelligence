from datetime import datetime, timezone
from contracts_platform.db.neo4j.client import get_driver
from contracts_platform.core.logging import logger


async def create_clause_node(clause_id: str, contract_id: str, clause_type: str, risk_level: str) -> None:
    driver = await get_driver()
    async with driver.session() as session:
        await session.run(
            "MERGE (cl:Clause {clause_id: $clause_id}) "
            "SET cl.type = $clause_type, cl.risk_level = $risk_level "
            "WITH cl "
            "MATCH (c:Contract {contract_id: $contract_id}) "
            "MERGE (c)-[:CONTAINS]->(cl)",
            clause_id=clause_id, contract_id=contract_id,
            clause_type=clause_type, risk_level=risk_level,
        )
    logger.info("neo4j.clause.create", clause_id=clause_id)


async def add_review_decision(party_id: str, contract_id: str, reviewer_id: str, outcome: str) -> None:
    driver = await get_driver()
    async with driver.session() as session:
        await session.run(
            "MATCH (p:Party {party_id: $party_id}), (c:Contract {contract_id: $contract_id}) "
            "MERGE (p)-[r:REVIEWED_BY]->(c) "
            "SET r.reviewer_id = $reviewer_id, r.outcome = $outcome, r.timestamp = $timestamp",
            party_id=party_id, contract_id=contract_id,
            reviewer_id=reviewer_id, outcome=outcome,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


async def find_conflicts(clause_id: str) -> list[dict]:
    driver = await get_driver()
    async with driver.session() as session:
        result = await session.run(
            "MATCH (c1:Clause {clause_id: $clause_id})-[:CONFLICTS_WITH]->(c2:Clause) RETURN c2",
            clause_id=clause_id,
        )
        return [dict(r["c2"]) async for r in result]
