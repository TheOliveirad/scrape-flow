"""
Job management endpoints.

Full CRUD for scraping jobs: create, list, get status, and cancel.
All endpoints require an optional API key when configured.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.api.dependencies import get_engine, verify_api_key
from src.core.engine import JobStatus, ScrapeEngine, ScrapeJob

router = APIRouter(dependencies=[Depends(verify_api_key)])


# ── Request / Response schemas ───────────────────────────────────────

class JobCreateRequest(BaseModel):
    """Payload for creating a new scraping job."""

    scraper_name: str = Field(..., description="Registered scraper identifier")
    urls: List[str] = Field(..., min_length=1, description="Target URLs to scrape")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Arbitrary metadata")

    model_config = {"json_schema_extra": {
        "example": {
            "scraper_name": "product",
            "urls": ["https://example.com/products/1", "https://example.com/products/2"],
            "metadata": {"source": "weekly-refresh"},
        }
    }}


class JobResponse(BaseModel):
    """Serialized view of a ScrapeJob."""

    id: UUID
    scraper_name: str
    status: JobStatus
    url_count: int
    result_count: int
    error_count: int
    duration_seconds: Optional[float]
    created_at: float

    @classmethod
    def from_job(cls, job: ScrapeJob) -> "JobResponse":
        return cls(
            id=job.id,
            scraper_name=job.scraper_name,
            status=job.status,
            url_count=len(job.target_urls),
            result_count=len(job.results),
            error_count=len(job.errors),
            duration_seconds=job.duration_seconds,
            created_at=job.created_at,
        )


# ── Endpoints ────────────────────────────────────────────────────────

@router.post("/jobs", status_code=status.HTTP_202_ACCEPTED, response_model=JobResponse)
async def create_job(
    payload: JobCreateRequest,
    engine: ScrapeEngine = Depends(get_engine),
):
    """Submit a new scraping job. Returns immediately with a job ID."""
    try:
        job = await engine.submit(
            scraper_name=payload.scraper_name,
            urls=payload.urls,
            metadata=payload.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return JobResponse.from_job(job)


@router.get("/jobs", response_model=List[JobResponse])
async def list_jobs(
    limit: int = 50,
    engine: ScrapeEngine = Depends(get_engine),
):
    """List recent scraping jobs, newest first."""
    jobs = await engine.list_jobs(limit=limit)
    return [JobResponse.from_job(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    engine: ScrapeEngine = Depends(get_engine),
):
    """Get the current status of a specific job."""
    job = await engine.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.from_job(job)


@router.get("/jobs/{job_id}/results")
async def get_job_results(
    job_id: UUID,
    engine: ScrapeEngine = Depends(get_engine),
):
    """
    Retrieve extracted data for a completed job.

    Returns the raw result list. In production, this would support
    pagination and format options (JSON, CSV, etc.).
    """
    job = await engine.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": str(job.id),
        "status": job.status.value,
        "results": job.results,
        "errors": job.errors,
    }


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_job(
    job_id: UUID,
    engine: ScrapeEngine = Depends(get_engine),
):
    """Cancel a running or queued job."""
    job = await engine.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = JobStatus.CANCELLED
