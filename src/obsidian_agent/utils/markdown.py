"""Markdown rendering helpers."""

from __future__ import annotations

from pathlib import Path


def render_template(template_path: Path, context: dict[str, str]) -> str:
    """Render a simple key replacement template."""

    content = template_path.read_text(encoding="utf-8")
    for key, value in context.items():
        content = content.replace(f"{{{{{key}}}}}", value)
    return content
