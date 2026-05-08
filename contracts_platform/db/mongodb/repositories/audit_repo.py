from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from contracts_platform.core.logging import logger


async def create_audit_summary(
    db: AsyncIOMotorDatabase,
    contract_id: str,
    summary: dict,
) -> None:
    """Insert or replace the audit summary for a contract."""
    doc = {
        "contract_id": contract_id,
        "summary": summary,
        "created_at": datetime.now(timezone.utc),
    }
    await db["audit_summaries"].replace_one(
        {"contract_id": contract_id},
        doc,
        upsert=True,
    )
    logger.info("audit.summary_created", contract_id=contract_id)


async def get_audit_summary(
    db: AsyncIOMotorDatabase,
    contract_id: str,
) -> dict | None:
    """Return the audit summary for a contract, or None."""
    return await db["audit_summaries"].find_one({"contract_id": contract_id}, {"_id": 0})
