"""
Structured JSON logging.

Provides a consistent logging interface across the application.
All log entries are structured key-value pairs, making them easy
to ingest into log aggregation tools (ELK, Datadog, etc.).
"""

from __future__ import annotations

import logging
import json
import sys
from datetime import datetime, timezone
from typing import Any


class StructuredFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Merge any extra key-value pairs passed via logger.info("msg", extra={...})
        if hasattr(record, "_structured_data"):
            log_entry.update(record._structured_data)

        return json.dumps(log_entry, default=str)


class StructuredLogger(logging.Logger):
    """Logger subclass that accepts keyword arguments as structured data."""

    def _log(self, level: int, msg: object, args: Any, **kwargs: Any) -> None:
        # Pull out structured kv pairs from the call site
        extra = kwargs.get("extra", {})
        structured = {k: v for k, v in kwargs.items() if k not in (
            "exc_info", "stack_info", "stacklevel", "extra",
        )}
        if structured:
            extra["_structured_data"] = structured
            kwargs["extra"] = extra
            # Remove our custom keys so the parent doesn't choke
            for key in structured:
                kwargs.pop(key, None)

        super()._log(level, msg, args, **kwargs)


def get_logger(name: str) -> StructuredLogger:
    """
    Return a structured logger for the given module.

    Usage
    -----
    >>> logger = get_logger(__name__)
    >>> logger.info("request.completed", status=200, duration_ms=42)
    """
    logging.setLoggerClass(StructuredLogger)
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger  # type: ignore[return-value]
