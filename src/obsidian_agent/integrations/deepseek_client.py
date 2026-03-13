"""DeepSeek OpenAI-compatible client."""

from __future__ import annotations

import json

import httpx


class DeepSeekChatClient:
    """Call DeepSeek's OpenAI-compatible chat API and return JSON payloads."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

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
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
        data = response.json()
        message_text = data["choices"][0]["message"]["content"]
        return json.loads(message_text)
