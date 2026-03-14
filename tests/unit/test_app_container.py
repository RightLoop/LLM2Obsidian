from obsidian_agent.app import build_container
from obsidian_agent.config import Settings


def test_build_container_prefers_deepseek_when_configured(tmp_path) -> None:
    settings = Settings(
        llm_provider="deepseek",
        deepseek_api_key="test-key",
        vault_root=tmp_path / "vault",
        sqlite_path=tmp_path / "db.sqlite3",
        vector_store_path=tmp_path / "vectors.json",
    )
    container = build_container(settings)
    assert container.llm_service.client is not None
    assert container.llm_service.client.__class__.__name__ == "DeepSeekChatClient"


def test_build_container_uses_filesystem_when_no_rest_client(tmp_path) -> None:
    settings = Settings(
        obsidian_mode="filesystem",
        vault_root=tmp_path / "vault",
        sqlite_path=tmp_path / "db.sqlite3",
        vector_store_path=tmp_path / "vectors.json",
    )
    container = build_container(settings)
    assert container.obsidian_service.client is None
