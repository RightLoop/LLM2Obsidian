from fastapi.testclient import TestClient

from obsidian_agent.app import build_container, create_app
from obsidian_agent.config import Settings
from obsidian_agent.test_support import make_test_dir


def test_healthcheck() -> None:
    root = make_test_dir("healthcheck")
    settings = Settings(
        _env_file=None,
        vault_root=root / "vault",
        sqlite_path=root / "db.sqlite3",
        vector_store_path=root / "vectors.json",
    )
    client = TestClient(create_app(settings))
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_settings_default_to_secure_obsidian_tls() -> None:
    settings = Settings(_env_file=None)
    assert settings.obsidian_verify_ssl is True


def test_build_container_supports_ollama_embedding_provider() -> None:
    root = make_test_dir("ollama_container")
    settings = Settings(
        _env_file=None,
        llm_provider="ollama",
        embeddings_provider="ollama",
        vault_root=root / "vault",
        sqlite_path=root / "db.sqlite3",
        vector_store_path=root / "vectors.json",
    )
    container = build_container(settings)
    assert container.llm_service.client is not None
    assert container.retrieval_service.embeddings_service.provider == "ollama"
