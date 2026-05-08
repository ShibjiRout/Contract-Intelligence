from qdrant_client.models import Distance, VectorParams

from contracts_platform.db.qdrant.client import get_qdrant_client

VECTOR_SIZE = 1536


async def init_collection(tenant_id: str) -> None:
    """Create the clause vector collection for a tenant if it does not exist."""
    client = get_qdrant_client()
    collection_name = f"clauses_{tenant_id}"
    existing = await client.get_collections()
    names = [c.name for c in existing.collections]
    if collection_name not in names:
        await client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
