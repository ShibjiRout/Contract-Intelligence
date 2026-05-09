from openai import AsyncOpenAI

from contracts_platform.core.config import settings
from contracts_platform.core.logging import logger
from contracts_platform.db.qdrant.repositories import clause_vector_repo


async def retrieve_accepted_wording(
    tenant_id: str,
    clause_type: str,
    clause_text: str,
    limit: int = 3,
) -> list[dict]:
    """
    Find accepted wording examples similar to clause_text.

    1. Embeds clause_text using OpenAI text-embedding-3-small.
    2. Queries Qdrant for similar accepted clauses of the same clause_type.
    3. Returns list of {score, text, clause_id} dicts.
    """
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    embedding_model = settings.EMBEDDING_MODEL

    embed_response = await client.embeddings.create(
        model=embedding_model,
        input=clause_text,
    )
    vector: list[float] = embed_response.data[0].embedding

    results = await clause_vector_repo.search_similar(
        tenant_id=tenant_id,
        vector=vector,
        clause_type=clause_type,
        status="accepted",
        limit=limit,
    )

    wording: list[dict] = []
    for r in results:
        payload = r.get("payload", {})
        wording.append(
            {
                "score": r.get("score", 0.0),
                "text": payload.get("raw_text", ""),
                "clause_id": payload.get("clause_id", ""),
            }
        )

    logger.info(
        "wording_retriever.complete",
        tenant_id=tenant_id,
        clause_type=clause_type,
        matches_found=len(wording),
    )
    return wording
