"""
Structured data extraction utilities.

Provides reusable pipeline-step functions for cleaning and
normalizing extracted data, plus a concrete extractor example
that maps JSON API responses to typed Pydantic models.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Type

from pydantic import BaseModel, Field

from src.extractors.base import BaseExtractor


# ── Pipeline step functions (used by Pipeline.add_step) ──────────────

async def normalize_text(data: Dict[str, Any]) -> Dict[str, Any]:
    """Collapse whitespace and strip all string values in a dict."""
    cleaned = {}
    for key, value in data.items():
        if isinstance(value, str):
            cleaned[key] = re.sub(r"\s+", " ", value).strip()
        else:
            cleaned[key] = value
    return cleaned


async def remove_empty_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove keys with None, empty string, or empty list values."""
    return {k: v for k, v in data.items() if v not in (None, "", [])}


# ── Pydantic schemas ────────────────────────────────────────────────

class ProductData(BaseModel):
    """Validated product data extracted from e-commerce pages."""

    title: str = Field(..., min_length=1)
    price: float = Field(..., ge=0)
    currency: str = Field(default="USD", max_length=3)
    description: str = Field(default="")
    availability: bool = Field(default=True)
    image_url: str = Field(default="")
    source_url: str = Field(default="")
    tags: List[str] = Field(default_factory=list)


class ArticleData(BaseModel):
    """Validated article/blog-post data."""

    title: str = Field(..., min_length=1)
    author: str = Field(default="Unknown")
    published_date: str = Field(default="")
    content_preview: str = Field(default="", max_length=500)
    word_count: int = Field(default=0, ge=0)
    source_url: str = Field(default="")
    categories: List[str] = Field(default_factory=list)


class ContactData(BaseModel):
    """Validated contact/lead data extracted from directory pages."""

    name: str = Field(..., min_length=1)
    email: str = Field(default="")
    phone: str = Field(default="")
    company: str = Field(default="")
    title: str = Field(default="")
    location: str = Field(default="")
    source_url: str = Field(default="")


# ── Concrete extractor example ───────────────────────────────────────

class ProductExtractor(BaseExtractor[ProductData]):
    """
    Extractor for product data from JSON API responses.

    Demonstrates how to map raw API fields to a validated Pydantic
    model. For HTML-based extraction with CSS selectors, see the
    HTMLProductScraper in scrapers/example.py.
    """

    @property
    def schema(self) -> Type[ProductData]:
        return ProductData

    def extract_one(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "title": raw.get("name", raw.get("title", "")),
            "price": float(raw.get("price", 0)),
            "currency": raw.get("currency", "USD"),
            "description": raw.get("description", ""),
            "availability": raw.get("in_stock", True),
            "image_url": raw.get("image", ""),
            "source_url": raw.get("url", ""),
            "tags": raw.get("tags", []),
        }

    def extract_many(self, raw: Any) -> List[Dict[str, Any]]:
        """Handle paginated API responses with a 'results' key."""
        items = raw if isinstance(raw, list) else raw.get("results", [])
        return [self.extract_one(item) for item in items]
