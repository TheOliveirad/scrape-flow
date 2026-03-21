"""
Health-check endpoint.

Provides a /health route for container orchestrators, load balancers,
and monitoring systems to verify the service is alive and responsive.
"""

from fastapi import APIRouter

from src.config import get_settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """Return service status and version."""
    settings = get_settings()
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
    }
