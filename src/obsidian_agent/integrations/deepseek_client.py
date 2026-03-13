"""DeepSeek OpenAI-compatible client."""

from __future__ import annotations

import json

import httpx

from obsidian_agent.integrations.http_utils import request_with_retry


class DeepSeekChatClient:
    """Call DeepSeek's OpenAI-compatible chat API and return JSON payloads."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        timeout_seconds: float = 30.0,
        retry_attempts: int = 3,
        retry_backoff_seconds: float = 0.5,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = retry_attempts
        self.retry_backoff_seconds = retry_backoff_seconds

    async def create_json_response(self, instructions: str, input_text: str) -> dict[str, object]:
        payload = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": input_text},
            ],
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await request_with_retry(
                lambda: client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                ),
                attempts=self.retry_attempts,
                backoff_seconds=self.retry_backoff_seconds,
            )
        data = response.json()
        message_text = data["choices"][0]["message"]["content"]
        return json.loads(message_text)
