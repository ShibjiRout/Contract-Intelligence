from sqlalchemy.ext.asyncio import AsyncSession

from contracts_platform.core.logging import logger
from contracts_platform.db.postgresql.repositories import rule_repo


async def detect_missing(
    contract_id: str,
    jurisdiction: str,
    extracted_types: list[str],
    db_session: AsyncSession,
) -> list[str]:
    """
    Compare required clause types for the jurisdiction against those actually extracted.

    1. Queries PostgreSQL rule_repo for REQUIRED clause types for the jurisdiction.
    2. Compares against extracted_types.
    3. Returns a list of missing clause type strings.
    """
    required: list[str] = await rule_repo.get_required_clauses(db_session, jurisdiction)
    extracted_set = set(extracted_types)
    missing = [ct for ct in required if ct not in extracted_set]

    if missing:
        logger.warning(
            "missing_clause_detector.missing_clauses",
            contract_id=contract_id,
            jurisdiction=jurisdiction,
            missing=missing,
        )
    else:
        logger.info(
            "missing_clause_detector.all_required_present",
            contract_id=contract_id,
            jurisdiction=jurisdiction,
        )

    return missing
