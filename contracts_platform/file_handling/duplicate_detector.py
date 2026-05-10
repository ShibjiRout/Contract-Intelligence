import hashlib

from motor.motor_asyncio import AsyncIOMotorDatabase

from contracts_platform.db.mongodb.repositories import contract_repo


def compute_file_hash(file_bytes: bytes) -> str:
    """Return SHA-256 hex digest of file bytes."""
    return hashlib.sha256(file_bytes).hexdigest()


async def check_duplicate(
    db: AsyncIOMotorDatabase,
    file_bytes: bytes,
    exclude_contract_id: str | None = None,
    tenant_id: str | None = None,
) -> tuple[bool, str | None]:
    """Return (is_duplicate, existing_contract_id). Queries MongoDB by file_hash."""
    file_hash = compute_file_hash(file_bytes)
    existing = await contract_repo.get_by_file_hash(db, file_hash, tenant_id=tenant_id)
    if existing:
        if exclude_contract_id and existing.get("contract_id") == exclude_contract_id:
            return False, None
        return True, existing.get("contract_id")
    return False, None
