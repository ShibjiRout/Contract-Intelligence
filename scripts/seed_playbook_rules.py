import asyncio

from dotenv import load_dotenv

load_dotenv()


async def main() -> None:
    from contracts_platform.db.postgresql.client import AsyncSessionLocal
    from contracts_platform.db.postgresql.models import ClauseTypeRegistry, Jurisdiction, PlaybookRule

    async with AsyncSessionLocal() as session:
        jurisdictions = [
            Jurisdiction(code="UK", name="United Kingdom", is_active=True),
            Jurisdiction(code="US", name="United States", is_active=True),
            Jurisdiction(code="UAE", name="United Arab Emirates", is_active=True),
        ]
        session.add_all(jurisdictions)

        rules = [
            # UK rules
            PlaybookRule(
                clause_type="CONFIDENTIALITY",
                jurisdiction="UK",
                rule_type="REQUIRED",
                description="confidentiality",
                weight=1.0,
                violation_message="Violation: Confidentiality clause is required for all UK contracts.",
            ),
            PlaybookRule(
                clause_type="GOVERNING_LAW",
                jurisdiction="UK",
                rule_type="REQUIRED",
                description="governing law",
                weight=1.0,
                violation_message="Violation: Governing law must be specified in UK contracts.",
            ),
            PlaybookRule(
                clause_type="LIABILITY",
                jurisdiction="UK",
                rule_type="FORBIDDEN",
                description="no liability whatsoever",
                weight=1.0,
                violation_message="Violation: Total exclusion of liability is not permitted under UK law.",
            ),
            PlaybookRule(
                clause_type="INDEMNITY",
                jurisdiction="UK",
                rule_type="REQUIRED",
                description="indemnity",
                weight=0.8,
                violation_message="Violation: Indemnity clause is required for UK contracts.",
            ),
            # US rules
            PlaybookRule(
                clause_type="CONFIDENTIALITY",
                jurisdiction="US",
                rule_type="REQUIRED",
                description="confidentiality",
                weight=1.0,
                violation_message="Violation: NDA/Confidentiality clause required for US contracts.",
            ),
            PlaybookRule(
                clause_type="GOVERNING_LAW",
                jurisdiction="US",
                rule_type="REQUIRED",
                description="governing law",
                weight=1.0,
                violation_message="Violation: Governing law and jurisdiction must be specified in US contracts.",
            ),
            PlaybookRule(
                clause_type="LIABILITY",
                jurisdiction="US",
                rule_type="FORBIDDEN",
                description="no liability whatsoever",
                weight=1.0,
                violation_message="Violation: Blanket liability exclusion is unenforceable under US law.",
            ),
            # UAE rules
            PlaybookRule(
                clause_type="GOVERNING_LAW",
                jurisdiction="UAE",
                rule_type="REQUIRED",
                description="governing law",
                weight=1.0,
                violation_message="Violation: Governing law must be specified in UAE contracts.",
            ),
            PlaybookRule(
                clause_type="CONFIDENTIALITY",
                jurisdiction="UAE",
                rule_type="REQUIRED",
                description="confidentiality",
                weight=1.0,
                violation_message="Violation: Confidentiality clause required for UAE contracts.",
            ),
        ]
        session.add_all(rules)

        clause_types = [
            ClauseTypeRegistry(
                clause_type="CONFIDENTIALITY",
                display_name="Confidentiality",
                description="Non-disclosure and confidentiality obligations",
                is_active=True,
            ),
            ClauseTypeRegistry(
                clause_type="GOVERNING_LAW",
                display_name="Governing Law",
                description="Choice of law and jurisdiction",
                is_active=True,
            ),
            ClauseTypeRegistry(
                clause_type="LIABILITY",
                display_name="Liability",
                description="Limitation of liability and indemnification caps",
                is_active=True,
            ),
            ClauseTypeRegistry(
                clause_type="INDEMNITY",
                display_name="Indemnity",
                description="Indemnification obligations between parties",
                is_active=True,
            ),
            ClauseTypeRegistry(
                clause_type="TERMINATION",
                display_name="Termination",
                description="Contract termination conditions and notice periods",
                is_active=True,
            ),
            ClauseTypeRegistry(
                clause_type="PAYMENT",
                display_name="Payment Terms",
                description="Payment schedules, penalties, and conditions",
                is_active=True,
            ),
        ]
        session.add_all(clause_types)

        await session.commit()

    print("PostgreSQL seeded:")
    print(f"  {len(jurisdictions)} jurisdictions")
    print(f"  {len(rules)} playbook rules (REQUIRED/FORBIDDEN only)")
    print(f"  {len(clause_types)} clause types")


if __name__ == "__main__":
    asyncio.run(main())
