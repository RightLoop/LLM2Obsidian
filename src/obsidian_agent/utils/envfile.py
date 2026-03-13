"""Helpers for reading and writing local .env files."""

from __future__ import annotations

from pathlib import Path


KNOWN_ENV_KEYS = [
    "LLM_PROVIDER",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_MODEL",
    "OBSIDIAN_MODE",
    "OBSIDIAN_API_URL",
    "OBSIDIAN_API_KEY",
    "OBSIDIAN_VERIFY_SSL",
    "VAULT_ROOT",
    "SQLITE_PATH",
    "VECTOR_STORE_PATH",
    "LOG_LEVEL",
    "DRY_RUN",
    "HTTP_TIMEOUT_SECONDS",
    "HTTP_RETRY_ATTEMPTS",
    "HTTP_RETRY_BACKOFF_SECONDS",
    "REVIEW_FOLDER",
    "INBOX_FOLDER",
]


def read_env_file(path: Path) -> dict[str, str]:
    """Read a simple KEY=VALUE env file."""

    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def write_env_file(path: Path, values: dict[str, str]) -> None:
    """Write a normalized env file with a stable key order."""

    lines: list[str] = []
    seen: set[str] = set()
    for key in KNOWN_ENV_KEYS:
        if key in values:
            lines.append(f"{key}={values[key]}")
            seen.add(key)
    for key in sorted(values):
        if key not in seen:
            lines.append(f"{key}={values[key]}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
