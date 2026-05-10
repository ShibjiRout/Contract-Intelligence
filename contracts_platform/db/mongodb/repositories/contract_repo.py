from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from contracts_platform.core.constants import ContractStatus, RiskLevel
from contracts_platform.core.logging import logger


async def create_contract(db: AsyncIOMotorDatabase, doc: dict) -> str:
    """Insert a contract document and return its contract_id."""
    result = await db["contracts"].insert_one(doc)
    logger.info("contract.created", contract_id=doc.get("contract_id"), inserted_id=str(result.inserted_id))
    return doc["contract_id"]


async def get_contract(db: AsyncIOMotorDatabase, contract_id: str) -> dict | None:
    """Return the contract document for the given contract_id, or None."""
    return await db["contracts"].find_one({"contract_id": contract_id}, {"_id": 0})


async def get_contract_for_tenant(
    db: AsyncIOMotorDatabase,
    contract_id: str,
    tenant_id: str,
) -> dict | None:
    """Return the contract document when it belongs to the given tenant."""
    return await db["contracts"].find_one(
        {"contract_id": contract_id, "tenant_id": tenant_id},
        {"_id": 0},
    )


async def update_status(
    db: AsyncIOMotorDatabase,
    contract_id: str,
    status: ContractStatus,
    stage: str,
) -> None:
    """Update the status and current_stage of a contract, setting updated_at."""
    await db["contracts"].update_one(
        {"contract_id": contract_id},
        {
            "$set": {
                "status": status.value,
                "current_stage": stage,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    logger.info("contract.status_updated", contract_id=contract_id, status=status.value, stage=stage)


async def append_error(
    db: AsyncIOMotorDatabase,
    contract_id: str,
    stage: str,
    message: str,
) -> None:
    """Push an error entry to the contract's errors array."""
    error_entry = {
        "stage": stage,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await db["contracts"].update_one(
        {"contract_id": contract_id},
        {
            "$push": {"errors": error_entry},
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
    )
    logger.warning("contract.error_appended", contract_id=contract_id, stage=stage, message=message)


async def update_final_risk(
    db: AsyncIOMotorDatabase,
    contract_id: str,
    risk: RiskLevel,
) -> None:
    """Set the final_risk field on a contract."""
    await db["contracts"].update_one(
        {"contract_id": contract_id},
        {
            "$set": {
                "final_risk": risk.value,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    logger.info("contract.risk_updated", contract_id=contract_id, risk=risk.value)


async def get_by_file_hash(
    db: AsyncIOMotorDatabase,
    file_hash: str,
    tenant_id: str | None = None,
) -> dict | None:
    """Return the contract document matching the given file_hash, optionally scoped by tenant."""
    query = {"file_hash": file_hash}
    if tenant_id is not None:
        query["tenant_id"] = tenant_id
    return await db["contracts"].find_one(query, {"_id": 0})


async def list_contracts(
    db: AsyncIOMotorDatabase,
    user_id: str,
    tenant_id: str,
    limit: int = 50,
) -> list[dict]:
    """Return up to `limit` contracts for the given user and tenant."""
    cursor = (
        db["contracts"]
        .find({"user_id": user_id, "tenant_id": tenant_id}, {"_id": 0})
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


async def delete_contract_data(
    db: AsyncIOMotorDatabase,
    contract_id: str,
    tenant_id: str,
) -> dict[str, int]:
    """Delete MongoDB records owned by one contract and tenant."""
    contract_result = await db["contracts"].delete_one(
        {"contract_id": contract_id, "tenant_id": tenant_id}
    )
    clauses_result = await db["clauses"].delete_many(
        {"contract_id": contract_id, "tenant_id": tenant_id}
    )
    audit_result = await db["audit_summaries"].delete_many({"contract_id": contract_id})
    cost_result = await db["cost_tracking"].delete_many({"contract_id": contract_id})
    logger.info(
        "contract.deleted_mongodb",
        contract_id=contract_id,
        tenant_id=tenant_id,
        contracts=contract_result.deleted_count,
        clauses=clauses_result.deleted_count,
        audit_summaries=audit_result.deleted_count,
        cost_entries=cost_result.deleted_count,
    )
    return {
        "contracts": contract_result.deleted_count,
        "clauses": clauses_result.deleted_count,
        "audit_summaries": audit_result.deleted_count,
        "cost_entries": cost_result.deleted_count,
    }
