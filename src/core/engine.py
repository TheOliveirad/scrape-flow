"""
Async scraping engine — the heart of scrape-flow.

Manages a pool of concurrent HTTP sessions with automatic rate limiting,
retry logic, and optional proxy rotation. Scrapers register themselves
with the engine and are dispatched through a unified async interface.

Architecture
------------
    Client  →  FastAPI  →  Engine.submit()  →  Semaphore-gated workers
                                                  ├─ RateLimiter
                                                  ├─ ProxyRotator
                                                  └─ RetryPolicy

Note: proxy rotation and advanced scheduling are behind interface
boundaries. Full production configuration available on request.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Type
from uuid import UUID, uuid4

import httpx

from src.config import get_settings
from src.scrapers.base import BaseScraper
from src.utils.logging import get_logger
from src.utils.retry import RetryPolicy

logger = get_logger(__name__)


# ── Job state machine ────────────────────────────────────────────────

class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScrapeJob:
    """Represents a single scraping job tracked by the engine."""

    id: UUID = field(default_factory=uuid4)
    scraper_name: str = ""
    target_urls: List[str] = field(default_factory=list)
    status: JobStatus = JobStatus.QUEUED
    results: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.completed_at is None:
            return None
        return round(self.completed_at - self.created_at, 3)


# ── Rate limiter (token-bucket) ──────────────────────────────────────

class _TokenBucket:
    """Simple async token-bucket rate limiter."""

    def __init__(self, rate: float, burst: int) -> None:
        self._rate = rate
        self._burst = burst
        self._tokens = float(burst)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self._burst, self._tokens + elapsed * self._rate)
            self._last_refill = now

            if self._tokens < 1:
                wait = (1 - self._tokens) / self._rate
                await asyncio.sleep(wait)
                self._tokens = 0
            else:
                self._tokens -= 1


# ── Engine ───────────────────────────────────────────────────────────

class ScrapeEngine:
    """
    Central orchestrator for all scraping operations.

    Usage
    -----
    >>> engine = ScrapeEngine()
    >>> engine.register_scraper("product", ProductScraper)
    >>> job = await engine.submit("product", ["https://example.com/items"])
    >>> result = await engine.wait_for(job.id)
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._scrapers: Dict[str, Type[BaseScraper]] = {}
        self._jobs: Dict[UUID, ScrapeJob] = {}
        self._semaphore = asyncio.Semaphore(self._settings.max_concurrency)
        self._rate_limiter = _TokenBucket(
            rate=self._settings.rate_limit_per_second,
            burst=self._settings.rate_limit_burst,
        )
        self._retry_policy = RetryPolicy(
            max_attempts=self._settings.default_retry_attempts,
            backoff_factor=self._settings.retry_backoff_factor,
        )
        self._client: Optional[httpx.AsyncClient] = None

    # ── Lifecycle ────────────────────────────────────────────────

    async def startup(self) -> None:
        """Initialise the shared HTTP client pool."""
        self._client = httpx.AsyncClient(
            timeout=self._settings.request_timeout,
            follow_redirects=True,
            limits=httpx.Limits(
                max_connections=self._settings.max_concurrency * 2,
                max_keepalive_connections=self._settings.max_concurrency,
            ),
        )
        logger.info("engine.started", max_concurrency=self._settings.max_concurrency)

    async def shutdown(self) -> None:
        """Gracefully close connections."""
        if self._client:
            await self._client.aclose()
        logger.info("engine.shutdown")

    # ── Scraper registry ─────────────────────────────────────────

    def register_scraper(self, name: str, scraper_cls: Type[BaseScraper]) -> None:
        """Register a scraper class under a human-friendly name."""
        self._scrapers[name] = scraper_cls
        logger.info("scraper.registered", name=name)

    # ── Job submission ───────────────────────────────────────────

    async def submit(
        self,
        scraper_name: str,
        urls: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ScrapeJob:
        """
        Queue a new scraping job and begin processing asynchronously.

        Returns the job immediately so callers can poll or await results.
        """
        if scraper_name not in self._scrapers:
            raise ValueError(f"Unknown scraper: {scraper_name!r}")

        job = ScrapeJob(
            scraper_name=scraper_name,
            target_urls=urls,
            metadata=metadata or {},
        )
        self._jobs[job.id] = job

        logger.info("job.submitted", job_id=str(job.id), urls=len(urls))
        asyncio.create_task(self._process_job(job))
        return job

    async def get_job(self, job_id: UUID) -> Optional[ScrapeJob]:
        return self._jobs.get(job_id)

    async def list_jobs(self, limit: int = 50) -> List[ScrapeJob]:
        jobs = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)
        return jobs[:limit]

    # ── Internal processing ──────────────────────────────────────

    async def _process_job(self, job: ScrapeJob) -> None:
        """Execute all URLs for a job with concurrency control."""
        job.status = JobStatus.RUNNING
        scraper_cls = self._scrapers[job.scraper_name]

        tasks = [
            self._scrape_url(scraper_cls, url, job) for url in job.target_urls
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

        job.status = JobStatus.COMPLETED if not job.errors else JobStatus.FAILED
        job.completed_at = time.time()

        logger.info(
            "job.finished",
            job_id=str(job.id),
            status=job.status.value,
            duration=job.duration_seconds,
            results=len(job.results),
            errors=len(job.errors),
        )

    async def _scrape_url(
        self,
        scraper_cls: Type[BaseScraper],
        url: str,
        job: ScrapeJob,
    ) -> None:
        """Scrape a single URL with rate limiting, retries, and semaphore."""
        async with self._semaphore:
            await self._rate_limiter.acquire()

            scraper = scraper_cls(client=self._client)
            attempt = 0

            while attempt < self._retry_policy.max_attempts:
                try:
                    raw = await scraper.fetch(url)
                    extracted = await scraper.extract(raw)
                    job.results.append(extracted)
                    return
                except Exception as exc:
                    attempt += 1
                    wait = self._retry_policy.get_delay(attempt)
                    logger.warning(
                        "scrape.retry",
                        url=url,
                        attempt=attempt,
                        error=str(exc),
                        next_wait=wait,
                    )
                    if attempt < self._retry_policy.max_attempts:
                        await asyncio.sleep(wait)

            job.errors.append(f"Failed after {attempt} attempts: {url}")
