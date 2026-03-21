"""
Abstract base scraper.

All scrapers inherit from BaseScraper and implement two methods:
  - fetch(url) → raw data (HTML, JSON, etc.)
  - extract(raw) → structured dict

This ensures every scraper follows the same interface, making them
interchangeable within the engine and testable in isolation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import httpx


class BaseScraper(ABC):
    """
    Contract for all scraper implementations.

    Subclasses define how to fetch a page and how to extract
    structured data from the raw response. The engine handles
    concurrency, retries, and rate limiting externally.
    """

    def __init__(self, client: Optional[httpx.AsyncClient] = None) -> None:
        self._client = client

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Scraper requires an httpx.AsyncClient — use via ScrapeEngine")
        return self._client

    @abstractmethod
    async def fetch(self, url: str) -> Any:
        """
        Retrieve raw content from the target URL.

        Returns whatever the downstream extract() method expects:
        HTML string, JSON dict, binary bytes, etc.
        """
        ...

    @abstractmethod
    async def extract(self, raw: Any) -> Dict[str, Any]:
        """
        Transform raw fetched content into a structured dictionary.

        The returned dict should match the Pydantic schema defined
        for this scraper's data model.
        """
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"
