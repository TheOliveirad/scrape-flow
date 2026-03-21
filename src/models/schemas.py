"""
Shared Pydantic schemas used across the application.

These schemas define the API contract and are used for both
request validation and response serialization.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScrapeTarget(BaseModel):
    """A single URL target with optional per-URL configuration."""

    url: str
    headers: Dict[str, str] = Field(default_factory=dict)
    params: Dict[str, str] = Field(default_factory=dict)
    priority: int = Field(default=0, ge=0, le=10)


class JobSummary(BaseModel):
    """Lightweight job representation for list endpoints."""

    id: UUID
    scraper_name: str
    status: TaskStatus
    url_count: int
    created_at: datetime


class JobDetail(BaseModel):
    """Full job representation including results and errors."""

    id: UUID
    scraper_name: str
    status: TaskStatus
    targets: List[ScrapeTarget]
    results: List[Dict[str, Any]]
    errors: List[str]
    metadata: Dict[str, Any]
    created_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None


class PipelineConfig(BaseModel):
    """Configuration for a data processing pipeline."""

    name: str
    steps: List[str] = Field(
        default_factory=list,
        description="Ordered list of step names to apply",
    )
    output_format: str = Field(default="json", pattern="^(json|csv|parquet)$")
