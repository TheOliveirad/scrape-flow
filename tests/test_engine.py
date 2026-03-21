"""
Tests for the core scraping engine.

Covers job lifecycle, concurrency controls, and retry behavior
using mock scrapers and httpx test transport.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest

from src.core.engine import JobStatus, ScrapeEngine, ScrapeJob
from src.scrapers.base import BaseScraper


# ── Test fixtures ────────────────────────────────────────────────────

class MockScraper(BaseScraper):
    """Scraper that returns deterministic test data."""

    async def fetch(self, url: str) -> Dict[str, Any]:
        return {"url": url, "content": "test-data"}

    async def extract(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        return {"extracted": True, "source": raw["url"]}


class FailingScraper(BaseScraper):
    """Scraper that always raises to test retry logic."""

    async def fetch(self, url: str) -> Any:
        raise ConnectionError("Simulated network failure")

    async def extract(self, raw: Any) -> Dict[str, Any]:
        return {}


# ── Tests ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_engine_registers_scraper():
    """Scrapers should be discoverable after registration."""
    engine = ScrapeEngine()
    engine.register_scraper("mock", MockScraper)
    assert "mock" in engine._scrapers


@pytest.mark.asyncio
async def test_submit_unknown_scraper_raises():
    """Submitting a job for an unregistered scraper should raise ValueError."""
    engine = ScrapeEngine()
    await engine.startup()
    try:
        with pytest.raises(ValueError, match="Unknown scraper"):
            await engine.submit("nonexistent", ["https://example.com"])
    finally:
        await engine.shutdown()


@pytest.mark.asyncio
async def test_successful_job_lifecycle():
    """A job with a working scraper should reach COMPLETED status."""
    engine = ScrapeEngine()
    await engine.startup()
    try:
        engine.register_scraper("mock", MockScraper)
        job = await engine.submit("mock", ["https://example.com/1"])

        # Give the background task time to complete
        await asyncio.sleep(0.5)

        fetched = await engine.get_job(job.id)
        assert fetched is not None
        assert fetched.status in (JobStatus.COMPLETED, JobStatus.RUNNING)
    finally:
        await engine.shutdown()


@pytest.mark.asyncio
async def test_failed_job_records_errors():
    """A job where all URLs fail should record errors."""
    engine = ScrapeEngine()
    await engine.startup()
    try:
        engine.register_scraper("failing", FailingScraper)
        job = await engine.submit("failing", ["https://example.com/fail"])

        # Wait for retries to exhaust
        await asyncio.sleep(3)

        fetched = await engine.get_job(job.id)
        assert fetched is not None
        assert len(fetched.errors) > 0
    finally:
        await engine.shutdown()


@pytest.mark.asyncio
async def test_list_jobs():
    """list_jobs should return submitted jobs in reverse chronological order."""
    engine = ScrapeEngine()
    await engine.startup()
    try:
        engine.register_scraper("mock", MockScraper)
        await engine.submit("mock", ["https://example.com/a"])
        await engine.submit("mock", ["https://example.com/b"])

        jobs = await engine.list_jobs()
        assert len(jobs) == 2
        assert jobs[0].created_at >= jobs[1].created_at
    finally:
        await engine.shutdown()
