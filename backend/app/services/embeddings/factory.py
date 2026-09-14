from functools import lru_cache

from app.core.config import settings
from app.services.embeddings.base import EmbeddingProvider
from app.services.embeddings.local import LocalEmbeddingProvider


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    if settings.embedding_provider == "google":
        from app.services.embeddings.google import GoogleEmbeddingProvider

        return GoogleEmbeddingProvider()
    return LocalEmbeddingProvider()
