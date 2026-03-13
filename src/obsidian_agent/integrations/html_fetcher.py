"""HTML fetch and cleanup helpers."""

from __future__ import annotations

import re

import httpx


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


async def fetch_url_text(url: str) -> tuple[str, str]:
    """Return title and cleaned text for a URL."""

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
    html = response.text
    return extract_title(html), strip_html(html)
