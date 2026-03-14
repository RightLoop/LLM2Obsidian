"""Obsidian Local REST API client."""

from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import quote

import httpx

from obsidian_agent.integrations.http_utils import request_with_retry


class ObsidianRestClient:
    """Client used when the Local REST API is available."""

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        verify_ssl: bool = False,
        timeout_seconds: float = 30.0,
        retry_attempts: int = 3,
        retry_backoff_seconds: float = 0.5,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.verify_ssl = verify_ssl
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = retry_attempts
        self.retry_backoff_seconds = retry_backoff_seconds

    def _headers(self) -> Mapping[str, str]:
        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def get(self, path: str, params: dict[str, str] | None = None) -> httpx.Response:
        async with httpx.AsyncClient(timeout=self.timeout_seconds, verify=self.verify_ssl) as client:
            return await request_with_retry(
                lambda: client.get(
                    f"{self.base_url}{path}",
                    headers=self._headers(),
                    params=params,
                ),
                attempts=self.retry_attempts,
                backoff_seconds=self.retry_backoff_seconds,
            )

    async def post(self, path: str, payload: dict[str, object]) -> httpx.Response:
        async with httpx.AsyncClient(timeout=self.timeout_seconds, verify=self.verify_ssl) as client:
            return await request_with_retry(
                lambda: client.post(
                    f"{self.base_url}{path}",
                    headers=self._headers(),
                    json=payload,
                ),
                attempts=self.retry_attempts,
                backoff_seconds=self.retry_backoff_seconds,
            )

    async def put_text(self, vault_path: str, content: str) -> None:
        encoded = quote(vault_path, safe="/")
        async with httpx.AsyncClient(timeout=self.timeout_seconds, verify=self.verify_ssl) as client:
            await request_with_retry(
                lambda: client.put(
                    f"{self.base_url}/vault/{encoded}",
                    headers={**self._headers(), "Content-Type": "text/markdown; charset=utf-8"},
                    content=content.encode("utf-8"),
                ),
                attempts=self.retry_attempts,
                backoff_seconds=self.retry_backoff_seconds,
            )

    async def read_text(self, vault_path: str) -> str:
        encoded = quote(vault_path, safe="/")
        response = await self.get(f"/vault/{encoded}")
        return response.text

    async def delete_note(self, vault_path: str) -> None:
        encoded = quote(vault_path, safe="/")
        async with httpx.AsyncClient(timeout=self.timeout_seconds, verify=self.verify_ssl) as client:
            await request_with_retry(
                lambda: client.delete(
                    f"{self.base_url}/vault/{encoded}",
                    headers=self._headers(),
                ),
                attempts=self.retry_attempts,
                backoff_seconds=self.retry_backoff_seconds,
            )
