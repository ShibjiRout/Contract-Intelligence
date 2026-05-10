from __future__ import annotations

from contracts_platform.core.logging import logger
from contracts_platform.db.neo4j.client import get_driver


async def create_contract_node(
    contract_id: str,
    tenant_id: str,
    filename: str,
    jurisdiction: str,
    status: str,
) -> None:
    driver = await get_driver()
    async with driver.session() as session:
        await session.run(
            """
            MERGE (c:Contract {contract_id: $contract_id, tenant_id: $tenant_id})
            SET c.filename = $filename,
                c.jurisdiction = $jurisdiction,
                c.status = $status
            """,
            contract_id=contract_id,
            tenant_id=tenant_id,
            filename=filename,
            jurisdiction=jurisdiction,
            status=status,
        )
    logger.info("neo4j.contract.upsert", contract_id=contract_id, tenant_id=tenant_id)


async def link_party_to_contract(
    party_id: str,
    contract_id: str,
    role: str,
) -> None:
    driver = await get_driver()
    async with driver.session() as session:
        await session.run(
            """
            MATCH (c:Contract {contract_id: $contract_id})
            MATCH (p:Party {party_id: $party_id, tenant_id: c.tenant_id})
            MERGE (p)-[r:PARTY_TO]->(c)
            SET r.role = $role
            """,
            party_id=party_id,
            contract_id=contract_id,
            role=role,
        )
    logger.info("neo4j.party.linked_contract", party_id=party_id, contract_id=contract_id)


async def delete_contract_graph(contract_id: str, tenant_id: str) -> int:
    """Delete a tenant-owned contract graph without deleting reusable party history."""
    driver = await get_driver()
    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (c:Contract {contract_id: $contract_id, tenant_id: $tenant_id})
            OPTIONAL MATCH (c)-[:CONTAINS]->(cl:Clause)
            DETACH DELETE cl, c
            WITH 1 AS _
            MATCH (p:Party {tenant_id: $tenant_id})
            WHERE NOT (p)--()
            DELETE p
            """,
            contract_id=contract_id,
            tenant_id=tenant_id,
        )
        summary = await result.consume()
    deleted = summary.counters.nodes_deleted
    logger.info(
        "neo4j.contract.deleted",
        contract_id=contract_id,
        tenant_id=tenant_id,
        nodes_deleted=deleted,
    )
    return deleted


async def get_accepted_precedents(
    contract_id: str,
    tenant_id: str,
    clause_type: str,
) -> list[dict]:
    """
    Find parties linked to this contract who have previously ACCEPTED
    a clause of the same type in a past contract.
    Returns list of {party_name, accepted_at, contract_id} ordered by most recent.
    """
    driver = await get_driver()
    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (current:Contract {contract_id: $contract_id, tenant_id: $tenant_id})<-[:PARTY_TO]-(p:Party)
            MATCH (p)-[:PARTY_TO]->(old:Contract {tenant_id: $tenant_id})-[:CONTAINS]->(cl:Clause)
            WHERE old.contract_id <> $contract_id
              AND cl.type = $clause_type
              AND cl.status = 'approved'
            RETURN p.name AS party_name,
                   p.party_id AS party_id,
                   old.contract_id AS contract_id,
                   cl.accepted_at AS accepted_at
            ORDER BY cl.accepted_at DESC
            LIMIT 5
            """,
            contract_id=contract_id,
            tenant_id=tenant_id,
            clause_type=clause_type,
        )
        return [dict(record) async for record in result]


async def get_contract_party_risky_clause_history(
    contract_id: str,
    tenant_id: str,
    clause_type: str,
) -> list[dict]:
    driver = await get_driver()
    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (current:Contract {contract_id: $contract_id, tenant_id: $tenant_id})<-[:PARTY_TO]-(p:Party)
            MATCH (p)-[:PARTY_TO]->(old:Contract {tenant_id: $tenant_id})-[:CONTAINS]->(cl:Clause)
            WHERE old.contract_id <> $contract_id
              AND cl.type = $clause_type
              AND cl.risk_level IN ["RED", "AMBER"]
            RETURN p.name AS party_name,
                   p.party_id AS party_id,
                   count(cl) AS risky_history,
                   collect(DISTINCT old.contract_id)[0..5] AS contract_ids
            ORDER BY risky_history DESC
            """,
            contract_id=contract_id,
            tenant_id=tenant_id,
            clause_type=clause_type,
        )
        return [dict(record) async for record in result]
