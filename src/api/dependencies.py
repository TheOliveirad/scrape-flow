"""
Shared FastAPI dependencies.

Provides dependency-injection functions for authentication,
engine access, and rate limiting across all API routes.
"""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from src.config import Settings, get_settings
from src.core.engine import ScrapeEngine


async def get_engine() -> ScrapeEngine:
    """
    Dependency that provides the shared ScrapeEngine instance.

    In production this would be wired through a proper DI container.
    For the portfolio demo, we import the singleton from main.
    """
    from src.main import engine
    return engine


async def verify_api_key(
    x_api_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    """
    Optional bearer-token authentication.

    If API_KEY is set in the environment, all requests must include
    a matching X-Api-Key header. If unset, auth is disabled.
    """
    if settings.api_key is None:
        return  # auth disabled
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
