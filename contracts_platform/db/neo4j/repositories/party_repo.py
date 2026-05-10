from __future__ import annotations

from contracts_platform.core.logging import logger
from contracts_platform.db.neo4j.client import get_driver


async def upsert_party(
    party_id: str,
    tenant_id: str,
    name: str,
    normalized_name: str,
) -> None:
    driver = await get_driver()
    async with driver.session() as session:
        await session.run(
            """
            MERGE (p:Party {party_id: $party_id, tenant_id: $tenant_id})
            SET p.name = $name,
                p.normalized_name = $normalized_name
            """,
            party_id=party_id,
            tenant_id=tenant_id,
            name=name,
            normalized_name=normalized_name,
        )
    logger.info("neo4j.party.upsert", party_id=party_id, tenant_id=tenant_id)


async def get_party_risk_history(party_id: str, tenant_id: str) -> list[dict]:
    driver = await get_driver()
    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Party {party_id: $party_id, tenant_id: $tenant_id})-[:PARTY_TO]->(c:Contract)-[:CONTAINS]->(cl:Clause)
            WHERE cl.risk_level IN ["RED", "AMBER"]
            RETURN c.contract_id AS contract_id,
                   cl.clause_id AS clause_id,
                   cl.type AS clause_type,
                   cl.risk_level AS risk_level,
                   cl.risk_score AS risk_score
            ORDER BY cl.risk_score DESC
            LIMIT 20
            """,
            party_id=party_id,
            tenant_id=tenant_id,
        )
        return [dict(record) async for record in result]
