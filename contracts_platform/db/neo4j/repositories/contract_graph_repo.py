from contracts_platform.db.neo4j.client import get_driver
from contracts_platform.core.logging import logger


async def create_contract_node(contract_id: str, jurisdiction: str) -> None:
    driver = await get_driver()
    async with driver.session() as session:
        await session.run(
            "MERGE (c:Contract {contract_id: $contract_id}) SET c.jurisdiction = $jurisdiction",
            contract_id=contract_id, jurisdiction=jurisdiction,
        )
    logger.info("neo4j.contract.create", contract_id=contract_id)


async def link_party_to_contract(party_id: str, contract_id: str) -> None:
    driver = await get_driver()
    async with driver.session() as session:
        await session.run(
            "MATCH (p:Party {party_id: $party_id}), (c:Contract {contract_id: $contract_id}) "
            "MERGE (p)-[:SIGNED]->(c)",
            party_id=party_id, contract_id=contract_id,
        )


async def get_cross_contract_conflicts(party_id: str, clause_type: str) -> int:
    driver = await get_driver()
    async with driver.session() as session:
        result = await session.run(
            "MATCH (p:Party {party_id: $party_id})-[:SIGNED]->(c:Contract)-[:CONTAINS]->(cl:Clause) "
            "WHERE cl.type = $clause_type AND cl.risk_level = 'RED' "
            "RETURN count(cl) AS conflict_count",
            party_id=party_id, clause_type=clause_type,
        )
        record = await result.single()
        return int(record["conflict_count"]) if record else 0
