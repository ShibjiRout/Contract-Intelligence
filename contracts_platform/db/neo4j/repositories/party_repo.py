from contracts_platform.db.neo4j.client import get_driver
from contracts_platform.core.logging import logger


async def get_party_risk_history(party_id: str) -> list[dict]:
    driver = await get_driver()
    async with driver.session() as session:
        result = await session.run(
            "MATCH (p:Party {party_id: $party_id})-[r:REVIEWED_BY]->(c:Contract) "
            "RETURN r.outcome AS outcome, c.contract_id AS contract_id, r.timestamp AS timestamp "
            "ORDER BY r.timestamp DESC LIMIT 10",
            party_id=party_id,
        )
        return [dict(r) async for r in result]


async def create_or_update_party(party_id: str, name_hash: str, risk_score: float) -> None:
    driver = await get_driver()
    async with driver.session() as session:
        await session.run(
            "MERGE (p:Party {party_id: $party_id}) "
            "SET p.name_hash = $name_hash, p.risk_score = $risk_score",
            party_id=party_id, name_hash=name_hash, risk_score=risk_score,
        )
    logger.info("neo4j.party.upsert", party_id=party_id)


async def get_party_by_name_hash(name_hash: str) -> dict | None:
    driver = await get_driver()
    async with driver.session() as session:
        result = await session.run(
            "MATCH (p:Party) WHERE p.name_hash = $name_hash RETURN p",
            name_hash=name_hash,
        )
        record = await result.single()
        return dict(record["p"]) if record else None
