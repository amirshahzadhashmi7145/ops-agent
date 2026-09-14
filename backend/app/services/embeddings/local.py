from functools import lru_cache

from app.core.config import settings
from app.services.embeddings.base import EmbeddingProvider

QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


@lru_cache
def _get_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.embedding_model_local)


class LocalEmbeddingProvider(EmbeddingProvider):
    @property
    def model_name(self) -> str:
        return settings.embedding_model_local

    @property
    def dimensions(self) -> int:
        return settings.embedding_dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = _get_model().encode(texts, normalize_embeddings=True)
        return [vector.tolist() for vector in vectors]

    def embed_query(self, text: str) -> list[float]:
        vector = _get_model().encode(
            QUERY_PREFIX + text,
            normalize_embeddings=True,
        )
        return vector.tolist()
