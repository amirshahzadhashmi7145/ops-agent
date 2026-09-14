from google import genai
from google.genai import types

from app.core.config import settings
from app.services.embeddings.base import EmbeddingProvider


class GoogleEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY is required when EMBEDDING_PROVIDER=google")
        self._client = genai.Client(api_key=settings.google_api_key)

    @property
    def model_name(self) -> str:
        return settings.embedding_model_google

    @property
    def dimensions(self) -> int:
        return settings.embedding_dimensions

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self._client.models.embed_content(
            model=self.model_name,
            contents=texts,
            config=types.EmbedContentConfig(output_dimensionality=settings.embedding_dimensions),
        )
        embeddings = response.embeddings or []
        return [list(item.values) for item in embeddings]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed_batch(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embed_batch([text])[0]
