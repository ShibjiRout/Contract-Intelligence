from contracts_platform.db.qdrant.collections import init_collection


async def ensure_tenant_collection(tenant_id: str) -> None:
    await init_collection(tenant_id)
