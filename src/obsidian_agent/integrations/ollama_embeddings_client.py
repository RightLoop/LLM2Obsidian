"""Ollama embeddings client."""

from __future__ import annotations

import httpx

from obsidian_agent.integrations.http_utils import request_with_retry


class OllamaEmbeddingsClient:
    """Call Ollama's embeddings API."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "nomic-embed-text",
        timeout_seconds: float = 60.0,
        retry_attempts: int = 3,
        retry_backoff_seconds: float = 0.5,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = retry_attempts
        self.retry_backoff_seconds = retry_backoff_seconds

    async def embed_text(self, text: str) -> list[float]:
        payload = {"model": self.model, "prompt": text}
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await request_with_retry(
                lambda: client.post(f"{self.base_url}/api/embeddings", json=payload),
                attempts=self.retry_attempts,
                backoff_seconds=self.retry_backoff_seconds,
            )
        data = response.json()
        return [float(value) for value in data["embedding"]]

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed_text(text) for text in texts]
