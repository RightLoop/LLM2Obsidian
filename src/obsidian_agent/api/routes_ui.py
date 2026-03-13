"""Operator UI and runtime management routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from obsidian_agent.app import build_container
from obsidian_agent.config import Settings
from obsidian_agent.utils.demo_data import seed_demo_vault
from obsidian_agent.utils.envfile import read_env_file, write_env_file

router = APIRouter(tags=["ui"])


class UiConfigPayload(BaseModel):
    llm_provider: str = "deepseek"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4.1-mini"
    obsidian_mode: str = "auto"
    obsidian_api_url: str = ""
    obsidian_api_key: str = ""
    obsidian_verify_ssl: bool = False
    vault_root: str = "./data/demo_vault"
    sqlite_path: str = "./data/processed/obsidian_agent.db"
    vector_store_path: str = "./data/processed/vector_index.json"
    log_level: str = "INFO"
    dry_run: bool = False
    http_timeout_seconds: float = 30.0
    http_retry_attempts: int = 3
    http_retry_backoff_seconds: float = 0.5
    review_folder: str = "90 Review"
    inbox_folder: str = "00 Inbox"


class WeeklyDigestRunRequest(BaseModel):
    week_key: str = Field(min_length=4)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _ui_root() -> Path:
    return Path(__file__).resolve().parents[1] / "ui"


def _env_path(request: Request) -> Path:
    return getattr(request.app.state, "ui_env_path", _repo_root() / ".env")


def _settings_to_payload(request: Request) -> UiConfigPayload:
    settings = request.app.state.container.settings
    return UiConfigPayload(
        llm_provider=settings.llm_provider,
        deepseek_api_key=settings.deepseek_api_key or "",
        deepseek_base_url=settings.deepseek_base_url,
        deepseek_model=settings.deepseek_model,
        openai_api_key=settings.openai_api_key or "",
        openai_base_url=settings.openai_base_url,
        openai_model=settings.openai_model,
        obsidian_mode=settings.obsidian_mode,
        obsidian_api_url=settings.obsidian_api_url or "",
        obsidian_api_key=settings.obsidian_api_key or "",
        obsidian_verify_ssl=settings.obsidian_verify_ssl,
        vault_root=str(settings.vault_root),
        sqlite_path=str(settings.sqlite_path),
        vector_store_path=str(settings.vector_store_path),
        log_level=settings.log_level,
        dry_run=settings.dry_run,
        http_timeout_seconds=settings.http_timeout_seconds,
        http_retry_attempts=settings.http_retry_attempts,
        http_retry_backoff_seconds=settings.http_retry_backoff_seconds,
        review_folder=settings.review_folder,
        inbox_folder=settings.inbox_folder,
    )


def _load_settings_from_env(request: Request) -> Settings:
    return Settings(_env_file=_env_path(request), _env_file_encoding="utf-8")


@router.get("/")
async def dashboard() -> FileResponse:
    return FileResponse(_ui_root() / "index.html")


@router.get("/ui")
async def dashboard_alias() -> FileResponse:
    return FileResponse(_ui_root() / "index.html")


@router.get("/ui/api/runtime")
async def runtime_state(request: Request) -> dict[str, object]:
    container = request.app.state.container
    settings = container.settings
    return {
        "app_name": settings.app_name,
        "health": "ok",
        "env_path": str(_env_path(request)),
        "settings": _settings_to_payload(request).model_dump(mode="json"),
    }


@router.get("/ui/api/config")
async def load_config(request: Request) -> dict[str, object]:
    env_values = read_env_file(_env_path(request))
    return {
        "env_path": str(_env_path(request)),
        "settings": _settings_to_payload(request).model_dump(mode="json"),
        "raw_env": env_values,
    }


@router.put("/ui/api/config")
async def save_config(payload: UiConfigPayload, request: Request) -> dict[str, object]:
    env_values = {
        "LLM_PROVIDER": payload.llm_provider,
        "DEEPSEEK_API_KEY": payload.deepseek_api_key,
        "DEEPSEEK_BASE_URL": payload.deepseek_base_url,
        "DEEPSEEK_MODEL": payload.deepseek_model,
        "OPENAI_API_KEY": payload.openai_api_key,
        "OPENAI_BASE_URL": payload.openai_base_url,
        "OPENAI_MODEL": payload.openai_model,
        "OBSIDIAN_MODE": payload.obsidian_mode,
        "OBSIDIAN_API_URL": payload.obsidian_api_url,
        "OBSIDIAN_API_KEY": payload.obsidian_api_key,
        "OBSIDIAN_VERIFY_SSL": str(payload.obsidian_verify_ssl).lower(),
        "VAULT_ROOT": payload.vault_root,
        "SQLITE_PATH": payload.sqlite_path,
        "VECTOR_STORE_PATH": payload.vector_store_path,
        "LOG_LEVEL": payload.log_level,
        "DRY_RUN": str(payload.dry_run).lower(),
        "HTTP_TIMEOUT_SECONDS": str(payload.http_timeout_seconds),
        "HTTP_RETRY_ATTEMPTS": str(payload.http_retry_attempts),
        "HTTP_RETRY_BACKOFF_SECONDS": str(payload.http_retry_backoff_seconds),
        "REVIEW_FOLDER": payload.review_folder,
        "INBOX_FOLDER": payload.inbox_folder,
    }
    write_env_file(_env_path(request), env_values)
    request.app.state.container = build_container(_load_settings_from_env(request))
    return {"saved": True, "settings": _settings_to_payload(request).model_dump(mode="json")}


@router.post("/ui/api/reload")
async def reload_runtime(request: Request) -> dict[str, object]:
    request.app.state.container = build_container(_load_settings_from_env(request))
    return {"reloaded": True, "settings": _settings_to_payload(request).model_dump(mode="json")}


@router.post("/ui/api/seed-demo")
async def seed_demo(request: Request) -> dict[str, object]:
    settings = request.app.state.container.settings
    paths = seed_demo_vault(settings.vault_root)
    return {"seeded": True, "count": len(paths), "paths": sorted(paths)}


@router.post("/ui/api/reindex")
async def reindex_from_ui(request: Request) -> dict[str, object]:
    paths = await request.app.state.container.indexing_service.reindex_all()
    return {"count": len(paths), "paths": paths}


@router.post("/ui/api/weekly-digest")
async def weekly_digest_from_ui(
    payload: WeeklyDigestRunRequest, request: Request
) -> dict[str, object]:
    result = await request.app.state.container.maintenance_workflow.weekly_digest(payload.week_key)
    if hasattr(result, "model_dump"):
        return {"status": "dry_run", "action_preview": result.model_dump(mode="json")}
    return {"status": "created", "path": result}
