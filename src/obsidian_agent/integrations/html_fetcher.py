"""HTML fetch and cleanup helpers with SSRF protection."""

from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
from urllib.parse import urljoin, urlsplit

import httpx


class UnsafeUrlError(ValueError):
    """Raised when a URL targets a blocked address."""


def extract_title(html: str) -> str:
    """Extract a best-effort title from HTML."""

    match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if not match:
        return "Untitled"
    return re.sub(r"\s+", " ", match.group(1)).strip()


def strip_html(html: str) -> str:
    """Convert HTML to plain text."""

    html = re.sub(r"<script.*?>.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r"<style.*?>.*?</style>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def _is_blocked_ip(candidate: str) -> bool:
    address = ipaddress.ip_address(candidate)
    return any(
        (
            address.is_private,
            address.is_loopback,
            address.is_link_local,
            address.is_multicast,
            address.is_reserved,
            address.is_unspecified,
        )
    )


def _validate_hostname(hostname: str) -> None:
    host = hostname.strip().strip("[]").lower()
    if not host:
        raise UnsafeUrlError("URL host is missing.")
    if host == "localhost":
        raise UnsafeUrlError("Loopback hosts are not allowed.")
    try:
        if _is_blocked_ip(host):
            raise UnsafeUrlError("Private or loopback IP ranges are not allowed.")
        return
    except ValueError:
        pass
    for family, _, _, _, sockaddr in socket.getaddrinfo(host, None):
        resolved = sockaddr[0]
        if family == socket.AF_INET6:
            resolved = resolved.split("%", 1)[0]
        if _is_blocked_ip(resolved):
            raise UnsafeUrlError("Resolved host points to a blocked IP range.")


async def validate_public_url(url: str) -> None:
    """Reject non-public URLs before fetching remote content."""

    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeUrlError("Only http and https URLs are allowed.")
    if parsed.username or parsed.password:
        raise UnsafeUrlError("Embedded credentials are not allowed.")
    if not parsed.hostname:
        raise UnsafeUrlError("URL host is missing.")
    await asyncio.to_thread(_validate_hostname, parsed.hostname)


async def fetch_url_text(url: str, timeout_seconds: float = 30.0) -> tuple[str, str]:
    """Return title and cleaned text for a URL."""

    await validate_public_url(url)
    async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=False) as client:
        current_url = url
        response: httpx.Response | None = None
        for _ in range(5):
            response = await client.get(current_url)
            if response.status_code not in {301, 302, 303, 307, 308}:
                break
            location = response.headers.get("location")
            if not location:
                break
            current_url = urljoin(str(response.url), location)
            await validate_public_url(current_url)
        if response is None:
            raise RuntimeError("No response returned while fetching URL.")
        response.raise_for_status()
    html = response.text
    return extract_title(html), strip_html(html)
