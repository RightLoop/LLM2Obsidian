"""Shared HTTP helpers for outbound integrations."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import httpx


async def request_with_retry(
    operation: Callable[[], Awaitable[httpx.Response]],
    attempts: int,
    backoff_seconds: float,
) -> httpx.Response:
    """Run an HTTP operation with bounded retries for transient failures."""

    last_error: Exception | None = None
    for attempt in range(1, max(attempts, 1) + 1):
        try:
            response = await operation()
            response.raise_for_status()
            return response
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            last_error = exc
            is_last_attempt = attempt >= max(attempts, 1)
            if is_last_attempt:
                break
            await asyncio.sleep(backoff_seconds * attempt)
    if last_error is None:
        raise RuntimeError("HTTP retry helper exited without a response or error")
    raise last_error
