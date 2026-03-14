"""Ollama chat client."""

from __future__ import annotations

import json

import httpx

from obsidian_agent.integrations.http_utils import request_with_retry


class OllamaChatClient:
    """Call Ollama's chat API and return JSON payloads."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "qwen2.5:7b",
        timeout_seconds: float = 60.0,
        retry_attempts: int = 3,
        retry_backoff_seconds: float = 0.5,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = retry_attempts
        self.retry_backoff_seconds = retry_backoff_seconds

    async def create_json_response(self, instructions: str, input_text: str) -> dict[str, object]:
        payload = {
            "model": self.model,
            "format": "json",
            "stream": False,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": input_text},
            ],
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await request_with_retry(
                lambda: client.post(f"{self.base_url}/api/chat", json=payload),
                attempts=self.retry_attempts,
                backoff_seconds=self.retry_backoff_seconds,
            )
        data = response.json()
        message_text = data["message"]["content"]
        return json.loads(message_text)
