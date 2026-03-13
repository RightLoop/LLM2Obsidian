"""Frontmatter utilities."""

from __future__ import annotations

from datetime import datetime


def dump_frontmatter(data: dict[str, object]) -> str:
    """Serialize a small YAML-like frontmatter block."""

    lines: list[str] = ["---"]
    for key, value in data.items():
        lines.append(f"{key}: {serialize_value(value)}")
    lines.append("---")
    return "\n".join(lines)


def parse_frontmatter(markdown: str) -> tuple[dict[str, object], str]:
    """Parse frontmatter and body."""

    if not markdown.startswith("---\n"):
        return {}, markdown
    parts = markdown.split("---\n", 2)
    if len(parts) < 3:
        return {}, markdown
    raw = parts[1].strip()
    body = parts[2].lstrip("\n")
    data: dict[str, object] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = deserialize_value(value.strip())
    return data, body


def patch_frontmatter(markdown: str, patch: dict[str, object]) -> str:
    """Update frontmatter fields."""

    data, body = parse_frontmatter(markdown)
    data.update(patch)
    return f"{dump_frontmatter(data)}\n\n{body.strip()}\n"


def serialize_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return "[" + ", ".join(str(item) for item in value) + "]"
    return str(value)


def deserialize_value(value: str) -> object:
    if value == "true":
        return True
    if value == "false":
        return False
    if value == "null":
        return None
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [item.strip() for item in inner.split(",")]
    return value
