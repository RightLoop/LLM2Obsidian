"""Application settings."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "LLM2Obsidian"
    app_env: str = "development"
    log_level: str = "INFO"
    dry_run: bool = False
    http_timeout_seconds: float = 30.0
    http_retry_attempts: int = 3
    http_retry_backoff_seconds: float = 0.5
    ui_admin_token: str | None = None
    llm_provider: str = "auto"
    embeddings_provider: str = "deterministic"
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4.1-mini"
    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_chat_model: str = "qwen2.5:7b"
    ollama_json_model: str = "qwen2.5:7b"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_timeout_seconds: float = 60.0
    obsidian_mode: str = "auto"
    obsidian_api_url: str | None = None
    obsidian_api_key: str | None = None
    obsidian_verify_ssl: bool = True
    vault_root: Path = Field(default=Path("./data/demo_vault"))
    sqlite_path: Path = Field(default=Path("./data/processed/obsidian_agent.db"))
    vector_store_path: Path = Field(default=Path("./data/processed/vector_index.json"))
    review_folder: str = "90 Review"
    inbox_folder: str = "00 Inbox"
    smart_nodes_folder: str = "20 Smart"
    smart_errors_folder: str = "21 Errors"

    @property
    def review_folder_path(self) -> Path:
        return self.vault_root / self.review_folder

    @property
    def inbox_folder_path(self) -> Path:
        return self.vault_root / self.inbox_folder

    @property
    def smart_nodes_folder_path(self) -> Path:
        return self.vault_root / self.smart_nodes_folder

    @property
    def smart_errors_folder_path(self) -> Path:
        return self.vault_root / self.smart_errors_folder


def get_settings() -> Settings:
    """Return settings instance."""

    return Settings()
