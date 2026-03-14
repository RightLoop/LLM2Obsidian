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
        data = await self._post_chat(
            instructions=instructions,
            input_text=input_text,
        )
        message_text = data["message"]["content"]
        payload = self._parse_json_payload(message_text)
        repaired = False
        if self._looks_sparse(payload):
            data = await self._post_chat(
                instructions=(
                    f"{instructions}\n\n"
                    "Your previous response was invalid or too sparse. "
                    "Return one complete JSON object only. "
                    "Do not return {}. "
                    "Do not omit required keys. "
                    "Do not wrap the JSON in markdown fences."
                ),
                input_text=input_text,
            )
            message_text = data["message"]["content"]
            payload = self._parse_json_payload(message_text)
            repaired = True
        payload["_telemetry"] = {
            "provider": "ollama",
            "model": data.get("model", self.model),
            "prompt_chars": len(instructions) + len(input_text),
            "response_chars": len(message_text),
            "repaired": repaired,
            "usage": {
                "prompt_tokens": data.get("prompt_eval_count"),
                "completion_tokens": data.get("eval_count"),
                "total_tokens": (data.get("prompt_eval_count") or 0) + (data.get("eval_count") or 0),
            },
        }
        return payload

    async def _post_chat(self, instructions: str, input_text: str) -> dict[str, object]:
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
        return response.json()

    @staticmethod
    def _parse_json_payload(message_text: str) -> dict[str, object]:
        text = message_text.strip()
        if not text:
            return {}
        try:
            payload = json.loads(text)
            return payload if isinstance(payload, dict) else {}
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                try:
                    payload = json.loads(text[start : end + 1])
                    return payload if isinstance(payload, dict) else {}
                except json.JSONDecodeError:
                    return {}
            return {}

    @staticmethod
    def _looks_sparse(payload: dict[str, object]) -> bool:
        if not payload:
            return True
        meaningful_keys = [key for key, value in payload.items() if key != "_telemetry" and value not in ("", [], {}, None)]
        return len(meaningful_keys) < 3
