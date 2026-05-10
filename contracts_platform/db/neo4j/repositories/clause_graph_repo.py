from __future__ import annotations

from datetime import datetime, timezone

from contracts_platform.core.logging import logger
from contracts_platform.db.neo4j.client import get_driver


async def create_clause_node(
    clause_id: str,
    contract_id: str,
    tenant_id: str,
    clause_type: str,
    risk_level: str,
    risk_score: float,
    status: str = "pending",
) -> None:
    driver = await get_driver()
    async with driver.session() as session:
        await session.run(
            """
            MERGE (cl:Clause {clause_id: $clause_id, tenant_id: $tenant_id})
            SET cl.type = $clause_type,
                cl.risk_level = $risk_level,
                cl.risk_score = $risk_score,
                cl.status = $status
            WITH cl
            MATCH (c:Contract {contract_id: $contract_id, tenant_id: $tenant_id})
            MERGE (c)-[:CONTAINS]->(cl)
            """,
            clause_id=clause_id,
            contract_id=contract_id,
            tenant_id=tenant_id,
            clause_type=clause_type,
            risk_level=risk_level,
            risk_score=risk_score,
            status=status,
        )
    logger.info("neo4j.clause.upsert", clause_id=clause_id, tenant_id=tenant_id)


async def record_clause_review(
    reviewer_id: str,
    tenant_id: str,
    clause_id: str,
    outcome: str,
) -> None:
    driver = await get_driver()
    async with driver.session() as session:
        timestamp = datetime.now(timezone.utc).isoformat()
        await session.run(
            """
            MERGE (r:Reviewer {reviewer_id: $reviewer_id, tenant_id: $tenant_id})
            WITH r
            MATCH (cl:Clause {clause_id: $clause_id, tenant_id: $tenant_id})
            MERGE (r)-[rel:REVIEWED]->(cl)
            SET rel.outcome = $outcome,
                rel.timestamp = $timestamp,
                cl.status = $outcome,
                cl.accepted_at = CASE WHEN $outcome = 'approved' THEN $timestamp ELSE cl.accepted_at END
            """,
            reviewer_id=reviewer_id,
            tenant_id=tenant_id,
            clause_id=clause_id,
            outcome=outcome,
            timestamp=timestamp,
        )
    logger.info(
        "neo4j.clause.review_recorded",
        clause_id=clause_id,
        tenant_id=tenant_id,
        reviewer_id=reviewer_id,
        outcome=outcome,
    )
