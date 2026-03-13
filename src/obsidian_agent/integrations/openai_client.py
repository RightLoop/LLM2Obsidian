"""Responses API client."""

from __future__ import annotations

import json

import httpx


class OpenAIResponsesClient:
    """Thin wrapper over the OpenAI Responses API."""

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    async def create_json_response(self, instructions: str, input_text: str) -> dict[str, object]:
        payload = {
            "model": "gpt-4.1-mini",
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": instructions}]},
                {"role": "user", "content": [{"type": "input_text", "text": input_text}]},
            ],
            "text": {"format": {"type": "json_object"}},
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self.base_url}/responses", headers=headers, json=payload)
            response.raise_for_status()
        data = response.json()
        output_text = data["output"][0]["content"][0]["text"]
        return json.loads(output_text)
