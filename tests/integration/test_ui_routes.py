from pathlib import Path

from fastapi.testclient import TestClient

from obsidian_agent.app import create_app
from obsidian_agent.config import Settings
from obsidian_agent.test_support import make_test_dir


def _build_ui_client(root: Path) -> tuple[TestClient, dict[str, str]]:
    settings = Settings(
        _env_file=None,
        ui_admin_token="test-token",
        obsidian_mode="filesystem",
        vault_root=root / "vault",
        sqlite_path=root / "db.sqlite3",
        vector_store_path=root / "vectors.json",
    )
    app = create_app(settings)
    app.state.ui_env_path = root / ".env"
    return TestClient(app), {"X-Admin-Token": "test-token"}


def test_dashboard_serves_html() -> None:
    root = make_test_dir("ui_dashboard")
    settings = Settings(
        _env_file=None,
        ui_admin_token="test-token",
        vault_root=root / "vault",
        sqlite_path=root / "db.sqlite3",
        vector_store_path=root / "vectors.json",
    )
    client = TestClient(create_app(settings))

    response = client.get("/")
    assert response.status_code == 200
    assert "LLM2Obsidian 控制台" in response.text
    assert "简体中文" in response.text
    assert "smart-layout" in response.text
    assert "鎺" not in response.text

    app_js = client.get("/ui/assets/app.js")
    assert app_js.status_code == 200
    assert "function escapeHtml" in app_js.text
    assert "smartResultTitle" in app_js.text


def test_ui_api_requires_admin_token() -> None:
    client, _ = _build_ui_client(make_test_dir("ui_auth"))
    runtime = client.get("/ui/api/runtime")
    assert runtime.status_code == 200

    response = client.get("/ui/api/config")
    assert response.status_code == 401


def test_ui_config_roundtrip_masks_secrets() -> None:
    root = make_test_dir("ui_config")
    client, headers = _build_ui_client(root)
    payload = {
        "ui_admin_token": "test-token",
        "llm_provider": "ollama",
        "embeddings_provider": "ollama",
        "deepseek_api_key": "demo-deepseek",
        "deepseek_base_url": "https://api.deepseek.com",
        "deepseek_model": "deepseek-chat",
        "openai_api_key": "demo-openai",
        "openai_base_url": "https://api.openai.com/v1",
        "openai_model": "gpt-4.1-mini",
        "ollama_base_url": "http://127.0.0.1:11434",
        "ollama_chat_model": "qwen2.5:7b",
        "ollama_json_model": "qwen2.5:7b",
        "ollama_embedding_model": "nomic-embed-text",
        "ollama_timeout_seconds": 60,
        "obsidian_mode": "filesystem",
        "obsidian_api_url": "",
        "obsidian_api_key": "demo-obsidian",
        "obsidian_verify_ssl": True,
        "vault_root": str(root / "vault"),
        "sqlite_path": str(root / "db.sqlite3"),
        "vector_store_path": str(root / "vectors.json"),
        "log_level": "INFO",
        "dry_run": True,
        "http_timeout_seconds": 12,
        "http_retry_attempts": 2,
        "http_retry_backoff_seconds": 0.2,
        "review_folder": "90 Review",
        "inbox_folder": "00 Inbox",
        "smart_nodes_folder": "20 Smart",
        "smart_errors_folder": "21 Errors",
    }

    response = client.put("/ui/api/config", json=payload, headers=headers)
    assert response.status_code == 200
    env_text = (root / ".env").read_text(encoding="utf-8")
    assert "DEEPSEEK_API_KEY=demo-deepseek" in env_text
    assert "OBSIDIAN_VERIFY_SSL=true" in env_text

    loaded = client.get("/ui/api/config", headers=headers)
    assert loaded.status_code == 200
    body = loaded.json()
    assert body["settings"]["deepseek_api_key"] == "********"
    assert body["masked_env"]["DEEPSEEK_API_KEY"] == "********"
    assert "raw_env" not in body


def test_ui_seed_demo_returns_paths() -> None:
    client, headers = _build_ui_client(make_test_dir("ui_seed"))
    response = client.post("/ui/api/seed-demo", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["seeded"] is True
    assert payload["count"] >= 1


def test_ui_can_bootstrap_admin_token_on_first_save() -> None:
    root = make_test_dir("ui_bootstrap")
    settings = Settings(
        _env_file=None,
        ui_admin_token=None,
        obsidian_mode="filesystem",
        vault_root=root / "vault",
        sqlite_path=root / "db.sqlite3",
        vector_store_path=root / "vectors.json",
    )
    app = create_app(settings)
    app.state.ui_env_path = root / ".env"
    client = TestClient(app)

    runtime = client.get("/ui/api/runtime")
    assert runtime.status_code == 200
    assert runtime.json()["bootstrap_required"] is True

    response = client.put(
        "/ui/api/config",
        headers={"X-Admin-Token": "bootstrap-token"},
        json={
            "ui_admin_token": "bootstrap-token",
            "llm_provider": "ollama",
            "embeddings_provider": "deterministic",
            "deepseek_api_key": "",
            "deepseek_base_url": "https://api.deepseek.com",
            "deepseek_model": "deepseek-chat",
            "openai_api_key": "",
            "openai_base_url": "https://api.openai.com/v1",
            "openai_model": "gpt-4.1-mini",
            "ollama_base_url": "http://127.0.0.1:11434",
            "ollama_chat_model": "Qwen14B-fixed:latest",
            "ollama_json_model": "Qwen14B-fixed:latest",
            "ollama_embedding_model": "nomic-embed-text",
            "ollama_timeout_seconds": 60,
            "obsidian_mode": "filesystem",
            "obsidian_api_url": "",
            "obsidian_api_key": "",
            "obsidian_verify_ssl": True,
            "vault_root": str(root / "vault"),
            "sqlite_path": str(root / "db.sqlite3"),
            "vector_store_path": str(root / "vectors.json"),
            "log_level": "INFO",
            "dry_run": False,
            "http_timeout_seconds": 30,
            "http_retry_attempts": 3,
            "http_retry_backoff_seconds": 0.5,
            "review_folder": "90 Review",
            "inbox_folder": "00 Inbox",
            "smart_nodes_folder": "20 Smart",
            "smart_errors_folder": "21 Errors",
        },
    )
    assert response.status_code == 200
    assert "UI_ADMIN_TOKEN=bootstrap-token" in (root / ".env").read_text(encoding="utf-8")
