"""Embedding service abstraction."""

from __future__ import annotations

import hashlib
import math


class EmbeddingsService:
    """Deterministic local embedding implementation for MVP."""

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
