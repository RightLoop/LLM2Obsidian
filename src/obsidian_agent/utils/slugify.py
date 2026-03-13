"""Slug helpers."""

import re


def slugify(value: str) -> str:
    """Return a filesystem-safe slug."""

    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "untitled"
