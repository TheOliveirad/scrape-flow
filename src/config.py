"""
Application configuration management.

Loads environment variables with sensible defaults and exposes them
as a typed Settings object. All secrets are read from the environment
so nothing sensitive is ever committed to version control.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration — every field maps to an env var."""

    # ── Application ──────────────────────────────────────────────
    app_name: str = "scrape-flow"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    # ── API ──────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: Optional[str] = None  # optional bearer-token auth

    # ── Scraping engine ──────────────────────────────────────────
    max_concurrency: int = 10
    request_timeout: int = 30
    default_retry_attempts: int = 3
    retry_backoff_factor: float = 1.5
    respect_robots_txt: bool = True

    # ── Proxy rotation (interface only — provider set via env) ───
    proxy_provider_url: Optional[str] = None
    proxy_api_key: Optional[str] = None

    # ── Storage ──────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./scrape_flow.db"
    redis_url: Optional[str] = None  # used for job queuing when available

    # ── Rate limiting ────────────────────────────────────────────
    rate_limit_per_second: float = 2.0
    rate_limit_burst: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance (parsed once at startup)."""
    return Settings()
