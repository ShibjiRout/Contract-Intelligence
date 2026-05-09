from openai import AsyncOpenAI

from contracts_platform.core.config import settings
from contracts_platform.core.logging import logger


async def embed_text(text: str) -> list[float]:
    """Embed text using OpenAI embeddings. Truncates to 8000 chars to stay within token limit."""
    oai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    response = await oai.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=text[:8000],
    )
    return response.data[0].embedding