"""Responses API client."""

from __future__ import annotations

import json

import httpx

from obsidian_agent.integrations.http_utils import request_with_retry


class OpenAIResponsesClient:
    """Thin wrapper over the OpenAI Responses API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4.1-mini",
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
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": instructions}]},
                {"role": "user", "content": [{"type": "input_text", "text": input_text}]},
            ],
            "text": {"format": {"type": "json_object"}},
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await request_with_retry(
                lambda: client.post(f"{self.base_url}/responses", headers=headers, json=payload),
                attempts=self.retry_attempts,
                backoff_seconds=self.retry_backoff_seconds,
            )
        data = response.json()
        output_text = data["output"][0]["content"][0]["text"]
        payload = json.loads(output_text)
        usage = data.get("usage", {})
        payload["_telemetry"] = {
            "provider": "openai",
            "model": data.get("model", self.model),
            "prompt_chars": len(instructions) + len(input_text),
            "response_chars": len(output_text),
            "usage": {
                "prompt_tokens": usage.get("input_tokens"),
                "completion_tokens": usage.get("output_tokens"),
                "total_tokens": usage.get("total_tokens"),
            },
        }
        return payload
