import asyncio
import sys
from contracts_platform.db.qdrant.collections import init_collection


async def main() -> None:
    tenant_id = sys.argv[1] if len(sys.argv) > 1 else "default"
    await init_collection(tenant_id)
    print(f"Qdrant collection initialized for tenant: {tenant_id}")


if __name__ == "__main__":
    asyncio.run(main())
