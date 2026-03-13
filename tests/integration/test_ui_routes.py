from pathlib import Path

from fastapi.testclient import TestClient

from obsidian_agent.app import build_container, create_app
from obsidian_agent.config import Settings


def test_dashboard_serves_html() -> None:
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    assert "LLM2Obsidian Control Panel" in response.text


def test_ui_config_roundtrip_updates_env_file(tmp_path: Path) -> None:
    app = create_app()
    app.state.ui_env_path = tmp_path / ".env"
    client = TestClient(app)

    payload = {
        "llm_provider": "deepseek",
        "deepseek_api_key": "demo-key",
        "deepseek_base_url": "https://api.deepseek.com",
        "deepseek_model": "deepseek-chat",
        "openai_api_key": "",
        "openai_base_url": "https://api.openai.com/v1",
        "openai_model": "gpt-4.1-mini",
        "obsidian_mode": "filesystem",
        "obsidian_api_url": "",
        "obsidian_api_key": "",
        "obsidian_verify_ssl": False,
        "vault_root": str(tmp_path / "vault"),
        "sqlite_path": str(tmp_path / "db.sqlite3"),
        "vector_store_path": str(tmp_path / "vectors.json"),
        "log_level": "INFO",
        "dry_run": True,
        "http_timeout_seconds": 12,
        "http_retry_attempts": 2,
        "http_retry_backoff_seconds": 0.2,
        "review_folder": "90 Review",
        "inbox_folder": "00 Inbox",
    }

    response = client.put("/ui/api/config", json=payload)
    assert response.status_code == 200
    env_text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "DEEPSEEK_API_KEY=demo-key" in env_text
    assert "DRY_RUN=true" in env_text

    loaded = client.get("/ui/api/config")
    assert loaded.status_code == 200
    assert loaded.json()["raw_env"]["DEEPSEEK_API_KEY"] == "demo-key"


def test_ui_seed_demo_returns_paths(tmp_path: Path) -> None:
    app = create_app()
    settings = Settings(
        obsidian_mode="filesystem",
        vault_root=tmp_path / "vault",
        sqlite_path=tmp_path / "db.sqlite3",
        vector_store_path=tmp_path / "vectors.json",
    )
    app.state.container = build_container(settings)
    client = TestClient(app)
    response = client.post("/ui/api/seed-demo")
    assert response.status_code == 200
    payload = response.json()
    assert payload["seeded"] is True
    assert payload["count"] >= 1
