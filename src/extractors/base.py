"""
Abstract base extractor.

Extractors are responsible for pulling structured data out of raw
content (HTML, JSON, XML, etc.) and validating it against a Pydantic
schema. They sit between the scraper's fetch step and the pipeline's
transformation steps.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseExtractor(ABC, Generic[T]):
    """
    Generic extractor that produces validated Pydantic models.

    Subclasses define:
      - schema: the target Pydantic model class
      - extract_one(raw) → dict: parse a single item
      - extract_many(raw) → list[dict]: parse a collection
    """

    @property
    @abstractmethod
    def schema(self) -> Type[T]:
        """The Pydantic model this extractor produces."""
        ...

    @abstractmethod
    def extract_one(self, raw: Any) -> Dict[str, Any]:
        """Extract fields for a single item from raw content."""
        ...

    def extract_many(self, raw: Any) -> List[Dict[str, Any]]:
        """Extract fields for multiple items. Override for batch parsing."""
        raise NotImplementedError("Batch extraction not implemented for this extractor")

    def validate_one(self, raw: Any) -> T:
        """Extract and validate a single item against the schema."""
        data = self.extract_one(raw)
        return self.schema.model_validate(data)

    def validate_many(self, raw: Any) -> List[T]:
        """Extract and validate multiple items."""
        items = self.extract_many(raw)
        return [self.schema.model_validate(item) for item in items]
