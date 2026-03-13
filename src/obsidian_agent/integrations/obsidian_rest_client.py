"""Obsidian Local REST API client."""

from __future__ import annotations

from collections.abc import Mapping

import httpx


class ObsidianRestClient:
    """Client used when the Local REST API is available."""

    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> Mapping[str, str]:
        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def get(self, path: str, params: dict[str, str] | None = None) -> dict[str, object]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}{path}", headers=self._headers(), params=params)
            response.raise_for_status()
            return response.json()

    async def post(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self.base_url}{path}", headers=self._headers(), json=payload)
            response.raise_for_status()
            return response.json()
