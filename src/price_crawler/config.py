"""Configurações centralizadas (.env → pydantic-settings)."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    headless: bool = True
    wait_ms: int = 3000
    timeout_ms: int = 30000

    db_path: Path = Path("./price_results.db")

    resolve_store_url: bool = True
    max_results_per_item: int = 5

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
