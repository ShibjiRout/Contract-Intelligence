"""Migration 001 — create initial MongoDB indexes."""

import asyncio

from pymongo import ASCENDING, IndexModel

from contracts_platform.db.mongodb.client import close_database, get_database
from contracts_platform.core.logging import logger


async def run() -> None:
    db = await get_database()

    # contracts collection
    await db["contracts"].create_indexes(
        [
            IndexModel([("contract_id", ASCENDING)], unique=True, name="uq_contract_id"),
            IndexModel([("user_id", ASCENDING)], name="idx_user_id"),
            IndexModel([("status", ASCENDING)], name="idx_status"),
            IndexModel([("tenant_id", ASCENDING)], name="idx_tenant_id"),
            IndexModel([("file_hash", ASCENDING)], name="idx_file_hash"),
        ]
    )
    logger.info("migration.indexes_created", collection="contracts")

    # cost_tracking collection
    await db["cost_tracking"].create_indexes(
        [
            IndexModel([("contract_id", ASCENDING)], name="idx_cost_contract_id"),
        ]
    )
    logger.info("migration.indexes_created", collection="cost_tracking")

    # audit_summaries collection
    await db["audit_summaries"].create_indexes(
        [
            IndexModel([("contract_id", ASCENDING)], unique=True, name="uq_audit_contract_id"),
        ]
    )
    logger.info("migration.indexes_created", collection="audit_summaries")

    await close_database()
    logger.info("migration.001_complete")


if __name__ == "__main__":
    asyncio.run(run())
