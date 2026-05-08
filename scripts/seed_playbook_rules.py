import asyncio
from contracts_platform.db.postgresql.client import AsyncSessionLocal
from contracts_platform.db.postgresql.models import PlaybookRule, RuleWeight, Jurisdiction


async def main() -> None:
    async with AsyncSessionLocal() as session:
        jurisdictions = [
            Jurisdiction(code="UK", name="United Kingdom", is_active=True),
            Jurisdiction(code="US", name="United States", is_active=True),
            Jurisdiction(code="UAE", name="United Arab Emirates", is_active=True),
        ]
        session.add_all(jurisdictions)

        rules = [
            PlaybookRule(clause_type="CONFIDENTIALITY", jurisdiction="UK", rule_type="REQUIRED",
                         description="Confidentiality clause required for all UK contracts", weight=1.0),
            PlaybookRule(clause_type="GOVERNING_LAW", jurisdiction="UK", rule_type="REQUIRED",
                         description="Governing law must be specified", weight=1.0),
            PlaybookRule(clause_type="INDEMNITY", jurisdiction="UK", rule_type="CONDITIONAL",
                         description="Indemnity clause required for contracts over £100k", weight=0.8),
            PlaybookRule(clause_type="CONFIDENTIALITY", jurisdiction="US", rule_type="REQUIRED",
                         description="NDA/Confidentiality required for US contracts", weight=1.0),
            PlaybookRule(clause_type="GOVERNING_LAW", jurisdiction="US", rule_type="REQUIRED",
                         description="Governing law and jurisdiction must be specified", weight=1.0),
        ]
        session.add_all(rules)

        weights = [
            RuleWeight(jurisdiction="UK", postgresql_weight=0.5, qdrant_weight=0.3, neo4j_weight=0.2),
            RuleWeight(jurisdiction="US", postgresql_weight=0.5, qdrant_weight=0.3, neo4j_weight=0.2),
            RuleWeight(jurisdiction="UAE", postgresql_weight=0.6, qdrant_weight=0.25, neo4j_weight=0.15),
        ]
        session.add_all(weights)
        await session.commit()

    print("Playbook rules and weights seeded successfully.")


if __name__ == "__main__":
    asyncio.run(main())
