"""
Example scraper implementation — demonstrates the BaseScraper interface.

This module shows how a real scraper is built on top of the framework.
It targets a placeholder API for demonstration purposes. Production
scrapers for specific sites/APIs are available on request.
"""

from __future__ import annotations

from typing import Any, Dict

from src.scrapers.base import BaseScraper
from src.utils.logging import get_logger

logger = get_logger(__name__)


class JSONPlaceholderScraper(BaseScraper):
    """
    Demo scraper targeting jsonplaceholder.typicode.com.

    Fetches a single post and extracts its fields into a
    clean dictionary matching the PostSchema model.
    """

    async def fetch(self, url: str) -> Dict[str, Any]:
        """Fetch JSON from the API endpoint."""
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()

    async def extract(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map raw API response to our internal schema.

        In a production scraper this would involve HTML parsing,
        CSS selectors, XPath queries, or LLM-assisted extraction.
        """
        return {
            "id": raw.get("id"),
            "title": raw.get("title", "").strip(),
            "body": raw.get("body", "").strip(),
            "user_id": raw.get("userId"),
            "source_url": f"https://jsonplaceholder.typicode.com/posts/{raw.get('id')}",
        }


class HTMLProductScraper(BaseScraper):
    """
    Skeleton scraper for HTML product pages.

    Demonstrates the pattern for parsing real HTML with
    selectolax or BeautifulSoup. The CSS selectors here are
    placeholders — actual selectors are site-specific and
    configured per-client.

    Full implementation available on request.
    """

    # CSS selectors — would be loaded from config in production
    SELECTORS = {
        "title": "h1.product-title",
        "price": "span.price-current",
        "description": "div.product-description",
        "availability": "span.stock-status",
        "image_url": "img.product-hero::attr(src)",
    }

    async def fetch(self, url: str) -> str:
        """Fetch raw HTML from the product page."""
        response = await self.client.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; ScrapeFlow/0.1)",
                "Accept": "text/html",
            },
        )
        response.raise_for_status()
        return response.text

    async def extract(self, raw: str) -> Dict[str, Any]:
        """
        Parse HTML and extract product fields.

        Production implementation uses selectolax for speed or
        BeautifulSoup for complex DOM traversal. Extraction logic
        is intentionally abstracted here.
        """
        # NOTE: This is the interface demonstration.
        # Actual parsing logic with CSS selectors is implemented
        # per-client and not included in the public repo.
        raise NotImplementedError(
            "HTML extraction requires site-specific selectors. "
            "See README for details on requesting full implementations."
        )
