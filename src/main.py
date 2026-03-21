"""
Application entry point.

Bootstraps the FastAPI application, wires up the scraping engine,
and registers API routes. Run with:

    uvicorn src.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config import get_settings
from src.core.engine import ScrapeEngine
from src.api.routes.health import router as health_router
from src.api.routes.jobs import router as jobs_router

# ── Shared engine instance ───────────────────────────────────────────
engine = ScrapeEngine()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup/shutdown of the scraping engine."""
    await engine.startup()
    yield
    await engine.shutdown()


def create_app() -> FastAPI:
    """Application factory — returns a fully configured FastAPI app."""
    settings = get_settings()

    app = FastAPI(
        title="scrape-flow",
        description="Async web scraping engine with structured data extraction",
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── Register routes ──────────────────────────────────────────
    app.include_router(health_router, tags=["health"])
    app.include_router(jobs_router, prefix="/api/v1", tags=["jobs"])

    return app


app = create_app()
