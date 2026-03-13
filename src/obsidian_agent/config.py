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
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    obsidian_api_url: str | None = None
    obsidian_api_key: str | None = None
    vault_root: Path = Field(default=Path("./data/demo_vault"))
    sqlite_path: Path = Field(default=Path("./data/processed/obsidian_agent.db"))
    vector_store_path: Path = Field(default=Path("./data/processed/vector_index.json"))
    review_folder: str = "90 Review"
    inbox_folder: str = "00 Inbox"

    @property
    def review_folder_path(self) -> Path:
        return self.vault_root / self.review_folder

    @property
    def inbox_folder_path(self) -> Path:
        return self.vault_root / self.inbox_folder


def get_settings() -> Settings:
    """Return settings instance."""

    return Settings()
