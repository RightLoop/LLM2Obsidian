"""Operator UI and runtime management routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from obsidian_agent.app import build_container
from obsidian_agent.api.deps import require_ui_admin_token
from obsidian_agent.config import Settings
from obsidian_agent.utils.demo_data import seed_demo_vault
from obsidian_agent.utils.envfile import read_env_file, write_env_file

router = APIRouter(tags=["ui"])
SECRET_MASK = "********"


class UiConfigPayload(BaseModel):
    ui_admin_token: str = ""
    llm_provider: str = "deepseek"
    embeddings_provider: str = "deterministic"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4.1-mini"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_chat_model: str = "Qwen14B-fixed:latest"
    ollama_json_model: str = "Qwen14B-fixed:latest"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_timeout_seconds: float = 60.0
    obsidian_mode: str = "auto"
    obsidian_api_url: str = ""
    obsidian_api_key: str = ""
    obsidian_verify_ssl: bool = True
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
    smart_nodes_folder: str = "20 Smart"
    smart_errors_folder: str = "21 Errors"


class WeeklyDigestRunRequest(BaseModel):
    week_key: str = Field(min_length=4)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _ui_root() -> Path:
    return Path(__file__).resolve().parents[1] / "ui"


def _env_path(request: Request) -> Path:
    return getattr(request.app.state, "ui_env_path", _repo_root() / ".env")


def _mask_secret(value: str | None) -> str:
    return SECRET_MASK if value else ""


def _settings_to_payload(request: Request, *, mask_secrets: bool = True) -> UiConfigPayload:
    settings = request.app.state.container.settings
    return UiConfigPayload(
        ui_admin_token=_mask_secret(settings.ui_admin_token) if mask_secrets else settings.ui_admin_token or "",
        llm_provider=settings.llm_provider,
        embeddings_provider=settings.embeddings_provider,
        deepseek_api_key=_mask_secret(settings.deepseek_api_key) if mask_secrets else settings.deepseek_api_key or "",
        deepseek_base_url=settings.deepseek_base_url,
        deepseek_model=settings.deepseek_model,
        openai_api_key=_mask_secret(settings.openai_api_key) if mask_secrets else settings.openai_api_key or "",
        openai_base_url=settings.openai_base_url,
        openai_model=settings.openai_model,
        ollama_base_url=settings.ollama_base_url,
        ollama_chat_model=settings.ollama_chat_model,
        ollama_json_model=settings.ollama_json_model,
        ollama_embedding_model=settings.ollama_embedding_model,
        ollama_timeout_seconds=settings.ollama_timeout_seconds,
        obsidian_mode=settings.obsidian_mode,
        obsidian_api_url=settings.obsidian_api_url or "",
        obsidian_api_key=_mask_secret(settings.obsidian_api_key) if mask_secrets else settings.obsidian_api_key or "",
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
        smart_nodes_folder=settings.smart_nodes_folder,
        smart_errors_folder=settings.smart_errors_folder,
    )


def _load_settings_from_env(request: Request) -> Settings:
    return Settings(_env_file=_env_path(request), _env_file_encoding="utf-8")


def _masked_env_values(env_values: dict[str, str]) -> dict[str, str]:
    secret_keys = {
        "UI_ADMIN_TOKEN",
        "DEEPSEEK_API_KEY",
        "OPENAI_API_KEY",
        "OBSIDIAN_API_KEY",
    }
    return {
        key: (SECRET_MASK if key in secret_keys and value else value)
        for key, value in env_values.items()
    }


def _preserve_secret(submitted: str, current: str | None) -> str:
    if submitted == SECRET_MASK:
        return current or ""
    if not submitted:
        return current or ""
    return submitted


def _ensure_ui_access(
    request: Request,
    x_admin_token: str | None,
    bootstrap_token: str | None = None,
) -> None:
    configured_token = request.app.state.container.settings.ui_admin_token
    if configured_token:
        if x_admin_token != configured_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing admin token.",
            )
        return
    if bootstrap_token and x_admin_token == bootstrap_token:
        return
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="UI admin token is not configured. Set and save a new token first.",
    )


@router.get("/")
async def dashboard() -> FileResponse:
    return FileResponse(_ui_root() / "index.html")


@router.get("/ui")
async def dashboard_alias() -> FileResponse:
    return FileResponse(_ui_root() / "index.html")


@router.get("/ui/api/runtime")
async def runtime_state(
    request: Request,
) -> dict[str, object]:
    container = request.app.state.container
    settings = container.settings
    return {
        "app_name": settings.app_name,
        "health": "ok",
        "env_path": str(_env_path(request)),
        "bootstrap_required": not bool(settings.ui_admin_token),
        "settings": _settings_to_payload(request, mask_secrets=True).model_dump(mode="json"),
    }


@router.get("/ui/api/config")
async def load_config(
    request: Request,
    _: None = Depends(require_ui_admin_token),
) -> dict[str, object]:
    env_values = read_env_file(_env_path(request))
    return {
        "env_path": str(_env_path(request)),
        "settings": _settings_to_payload(request, mask_secrets=True).model_dump(mode="json"),
        "masked_env": _masked_env_values(env_values),
    }


@router.put("/ui/api/config")
async def save_config(
    payload: UiConfigPayload,
    request: Request,
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> dict[str, object]:
    _ensure_ui_access(request, x_admin_token, bootstrap_token=payload.ui_admin_token.strip() or None)
    current = _load_settings_from_env(request)
    env_values = {
        "UI_ADMIN_TOKEN": _preserve_secret(payload.ui_admin_token, current.ui_admin_token),
        "LLM_PROVIDER": payload.llm_provider,
        "EMBEDDINGS_PROVIDER": payload.embeddings_provider,
        "DEEPSEEK_API_KEY": _preserve_secret(payload.deepseek_api_key, current.deepseek_api_key),
        "DEEPSEEK_BASE_URL": payload.deepseek_base_url,
        "DEEPSEEK_MODEL": payload.deepseek_model,
        "OPENAI_API_KEY": _preserve_secret(payload.openai_api_key, current.openai_api_key),
        "OPENAI_BASE_URL": payload.openai_base_url,
        "OPENAI_MODEL": payload.openai_model,
        "OLLAMA_BASE_URL": payload.ollama_base_url,
        "OLLAMA_CHAT_MODEL": payload.ollama_chat_model,
        "OLLAMA_JSON_MODEL": payload.ollama_json_model,
        "OLLAMA_EMBEDDING_MODEL": payload.ollama_embedding_model,
        "OLLAMA_TIMEOUT_SECONDS": str(payload.ollama_timeout_seconds),
        "OBSIDIAN_MODE": payload.obsidian_mode,
        "OBSIDIAN_API_URL": payload.obsidian_api_url,
        "OBSIDIAN_API_KEY": _preserve_secret(payload.obsidian_api_key, current.obsidian_api_key),
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
        "SMART_NODES_FOLDER": payload.smart_nodes_folder,
        "SMART_ERRORS_FOLDER": payload.smart_errors_folder,
    }
    write_env_file(_env_path(request), env_values)
    request.app.state.container = build_container(_load_settings_from_env(request))
    return {
        "saved": True,
        "settings": _settings_to_payload(request, mask_secrets=True).model_dump(mode="json"),
    }


@router.post("/ui/api/reload")
async def reload_runtime(
    request: Request,
    _: None = Depends(require_ui_admin_token),
) -> dict[str, object]:
    request.app.state.container = build_container(_load_settings_from_env(request))
    return {
        "reloaded": True,
        "settings": _settings_to_payload(request, mask_secrets=True).model_dump(mode="json"),
    }


@router.post("/ui/api/seed-demo")
async def seed_demo(
    request: Request,
    _: None = Depends(require_ui_admin_token),
) -> dict[str, object]:
    settings = request.app.state.container.settings
    paths = seed_demo_vault(settings.vault_root)
    return {"seeded": True, "count": len(paths), "paths": sorted(paths)}


@router.post("/ui/api/reindex")
async def reindex_from_ui(
    request: Request,
    _: None = Depends(require_ui_admin_token),
) -> dict[str, object]:
    paths = await request.app.state.container.indexing_service.reindex_all()
    return {"count": len(paths), "paths": paths}


@router.post("/ui/api/weekly-digest")
async def weekly_digest_from_ui(
    payload: WeeklyDigestRunRequest,
    request: Request,
    _: None = Depends(require_ui_admin_token),
) -> dict[str, object]:
    result = await request.app.state.container.maintenance_workflow.weekly_digest(payload.week_key)
    if hasattr(result, "model_dump"):
        return {"status": "dry_run", "action_preview": result.model_dump(mode="json")}
    return {"status": "created", "path": result}
