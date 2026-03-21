"""
Tests for data extractors and pipeline utilities.

Validates Pydantic schema enforcement, pipeline step functions,
and the extractor interface contract.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.extractors.structured import (
    ArticleData,
    ContactData,
    ProductData,
    ProductExtractor,
    normalize_text,
    remove_empty_fields,
)


# ── Schema validation tests ─────────────────────────────────────────

class TestProductData:
    def test_valid_product(self):
        product = ProductData(title="Widget", price=9.99)
        assert product.title == "Widget"
        assert product.currency == "USD"

    def test_missing_title_raises(self):
        with pytest.raises(ValidationError):
            ProductData(title="", price=9.99)

    def test_negative_price_raises(self):
        with pytest.raises(ValidationError):
            ProductData(title="Widget", price=-1.0)

    def test_optional_fields_default(self):
        product = ProductData(title="Widget", price=0)
        assert product.description == ""
        assert product.tags == []
        assert product.availability is True


class TestArticleData:
    def test_valid_article(self):
        article = ArticleData(title="Test Article")
        assert article.author == "Unknown"
        assert article.word_count == 0

    def test_content_preview_max_length(self):
        long_text = "x" * 501
        with pytest.raises(ValidationError):
            ArticleData(title="Test", content_preview=long_text)


class TestContactData:
    def test_valid_contact(self):
        contact = ContactData(name="Jane Doe", email="jane@example.com")
        assert contact.company == ""


# ── Pipeline step tests ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_normalize_text():
    data = {"title": "  Hello   World  ", "count": 42}
    result = await normalize_text(data)
    assert result["title"] == "Hello World"
    assert result["count"] == 42


@pytest.mark.asyncio
async def test_remove_empty_fields():
    data = {"title": "Widget", "description": "", "tags": [], "price": 0}
    result = await remove_empty_fields(data)
    assert "description" not in result
    assert "tags" not in result
    assert result["price"] == 0  # 0 is not empty


# ── Extractor tests ──────────────────────────────────────────────────

class TestProductExtractor:
    def test_extract_one(self):
        extractor = ProductExtractor()
        raw = {"name": "Widget", "price": "19.99", "in_stock": True}
        result = extractor.extract_one(raw)
        assert result["title"] == "Widget"
        assert result["price"] == 19.99

    def test_validate_one(self):
        extractor = ProductExtractor()
        raw = {"name": "Widget", "price": "9.99"}
        product = extractor.validate_one(raw)
        assert isinstance(product, ProductData)
        assert product.title == "Widget"

    def test_extract_many(self):
        extractor = ProductExtractor()
        raw = {"results": [
            {"name": "A", "price": "1.00"},
            {"name": "B", "price": "2.00"},
        ]}
        items = extractor.extract_many(raw)
        assert len(items) == 2
