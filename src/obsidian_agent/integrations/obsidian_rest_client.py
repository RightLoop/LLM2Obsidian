"""Obsidian Local REST API client."""

from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import quote

import httpx


class ObsidianRestClient:
    """Client used when the Local REST API is available."""

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        verify_ssl: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.verify_ssl = verify_ssl

    def _headers(self) -> Mapping[str, str]:
        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def get(self, path: str, params: dict[str, str] | None = None) -> httpx.Response:
        async with httpx.AsyncClient(timeout=30.0, verify=self.verify_ssl) as client:
            response = await client.get(
                f"{self.base_url}{path}",
                headers=self._headers(),
                params=params,
            )
            response.raise_for_status()
            return response

    async def post(self, path: str, payload: dict[str, object]) -> httpx.Response:
        async with httpx.AsyncClient(timeout=30.0, verify=self.verify_ssl) as client:
            response = await client.post(
                f"{self.base_url}{path}",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            return response

    async def put_text(self, vault_path: str, content: str) -> None:
        encoded = quote(vault_path, safe="/")
        async with httpx.AsyncClient(timeout=30.0, verify=self.verify_ssl) as client:
            response = await client.put(
                f"{self.base_url}/vault/{encoded}",
                headers={**self._headers(), "Content-Type": "text/markdown; charset=utf-8"},
                content=content.encode("utf-8"),
            )
            response.raise_for_status()

    async def read_text(self, vault_path: str) -> str:
        encoded = quote(vault_path, safe="/")
        response = await self.get(f"/vault/{encoded}")
        return response.text

    async def delete_note(self, vault_path: str) -> None:
        encoded = quote(vault_path, safe="/")
        async with httpx.AsyncClient(timeout=30.0, verify=self.verify_ssl) as client:
            response = await client.delete(
                f"{self.base_url}/vault/{encoded}",
                headers=self._headers(),
            )
            response.raise_for_status()
