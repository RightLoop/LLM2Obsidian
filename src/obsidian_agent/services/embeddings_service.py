"""Embedding service abstraction."""

from __future__ import annotations

import hashlib
import math
from typing import Protocol


class EmbeddingClient(Protocol):
    """Minimal provider contract for embedding backends."""

    async def embed_text(self, text: str) -> list[float]:
        """Return one embedding vector."""

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return multiple embedding vectors."""


class DeterministicEmbeddingsClient:
    """Stable local embedding implementation for tests and offline fallback."""

    def __init__(self, dimensions: int = 16) -> None:
        self.dimensions = dimensions

    async def embed_text(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for idx in range(self.dimensions):
                vector[idx] += digest[idx] / 255.0
        norm = math.sqrt(sum(item * item for item in vector))
        if norm == 0:
            return vector
        return [item / norm for item in vector]

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed_text(text) for text in texts]


class EmbeddingsService:
    """Provider-aware embedding facade."""

    def __init__(
        self,
        provider: str = "deterministic",
        client: EmbeddingClient | None = None,
        fallback_client: EmbeddingClient | None = None,
    ) -> None:
        self.provider = provider.lower()
        self.client = client
        self.fallback_client = fallback_client or DeterministicEmbeddingsClient()

    def _active_client(self) -> EmbeddingClient:
        if self.provider == "ollama" and self.client is not None:
            return self.client
        return self.fallback_client

    async def embed_text(self, text: str) -> list[float]:
        return await self._active_client().embed_text(text)

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return await self._active_client().embed_texts(texts)
