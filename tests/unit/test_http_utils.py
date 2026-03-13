import asyncio

import httpx

from obsidian_agent.integrations.http_utils import request_with_retry


def test_request_with_retry_retries_until_success() -> None:
    attempts = {"count": 0}

    async def operation() -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise httpx.ConnectError("temporary", request=httpx.Request("GET", "https://example.com"))
        return httpx.Response(200, request=httpx.Request("GET", "https://example.com"))

    response = asyncio.run(request_with_retry(operation, attempts=3, backoff_seconds=0.0))

    assert response.status_code == 200
    assert attempts["count"] == 3
