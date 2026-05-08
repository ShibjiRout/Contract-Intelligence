from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contracts_platform.core.logging import logger
from contracts_platform.db.postgresql.models import PlaybookRule, RuleVersion, RuleWeight


async def get_rules_for_jurisdiction(
    session: AsyncSession,
    jurisdiction: str,
    clause_type: str,
) -> list[dict]:
    """Return active rules matching jurisdiction and clause_type."""
    result = await session.execute(
        select(PlaybookRule).where(
            PlaybookRule.jurisdiction == jurisdiction,
            PlaybookRule.clause_type == clause_type,
            PlaybookRule.is_active.is_(True),
        )
    )
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "clause_type": r.clause_type,
            "jurisdiction": r.jurisdiction,
            "rule_type": r.rule_type,
            "description": r.description,
            "weight": r.weight,
        }
        for r in rows
    ]


async def get_required_clauses(session: AsyncSession, jurisdiction: str) -> list[str]:
    """Return clause_type strings that are REQUIRED for the given jurisdiction."""
    result = await session.execute(
        select(PlaybookRule.clause_type).where(
            PlaybookRule.jurisdiction == jurisdiction,
            PlaybookRule.rule_type == "REQUIRED",
            PlaybookRule.is_active.is_(True),
        )
    )
    return list(result.scalars().all())


async def get_weights(session: AsyncSession, jurisdiction: str) -> dict:
    """Return scoring weights for the jurisdiction, with safe defaults."""
    result = await session.execute(
        select(RuleWeight).where(RuleWeight.jurisdiction == jurisdiction)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return {"postgresql_weight": 0.5, "qdrant_weight": 0.3, "neo4j_weight": 0.2}
    return {
        "postgresql_weight": row.postgresql_weight,
        "qdrant_weight": row.qdrant_weight,
        "neo4j_weight": row.neo4j_weight,
    }


async def create_rule(session: AsyncSession, rule_data: dict) -> int:
    """Insert a new PlaybookRule and return its id."""
    rule = PlaybookRule(**rule_data)
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    logger.info("rule.created", rule_id=rule.id, jurisdiction=rule.jurisdiction)
    return rule.id


async def create_rule_version(
    session: AsyncSession,
    rule_id: int,
    old_value: dict,
    new_value: dict,
    changed_by: str,
) -> None:
    """Record an audit version for a rule change."""
    # Determine next version number
    result = await session.execute(
        select(RuleVersion).where(RuleVersion.rule_id == rule_id)
    )
    existing = result.scalars().all()
    version_number = len(existing) + 1

    version = RuleVersion(
        rule_id=rule_id,
        version_number=version_number,
        old_value=old_value,
        new_value=new_value,
        changed_by=changed_by,
        changed_at=datetime.now(timezone.utc),
    )
    session.add(version)
    await session.commit()
    logger.info("rule_version.created", rule_id=rule_id, version_number=version_number)
