from dataclasses import dataclass

from contracts_platform.core.config import settings


@dataclass
class EmbeddingModelVersion:
    model_name: str
    version: str
    vector_size: int


CURRENT_EMBEDDING_MODEL = EmbeddingModelVersion(
    model_name=settings.EMBEDDING_MODEL,
    version=settings.EMBEDDING_MODEL_VERSION,
    vector_size=1536,
)
