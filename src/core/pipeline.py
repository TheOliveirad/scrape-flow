"""
Data pipeline orchestration.

Defines the Pipeline abstraction — a composable chain of steps that
transform raw scraped data into clean, structured output. Each step
is an async callable that receives the previous step's output.

Example
-------
>>> pipeline = Pipeline("product-clean")
>>> pipeline.add_step(normalize_whitespace)
>>> pipeline.add_step(extract_price_fields)
>>> pipeline.add_step(validate_with_schema)
>>> output = await pipeline.run(raw_html)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, List, Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Type alias for an async pipeline step
StepFn = Callable[[Any], Coroutine[Any, Any, Any]]


@dataclass
class StepResult:
    """Captures the outcome of a single pipeline step."""

    name: str
    success: bool
    duration_ms: float
    error: Optional[str] = None


@dataclass
class PipelineResult:
    """Full result of a pipeline run, including per-step telemetry."""

    pipeline_name: str
    output: Any = None
    steps: List[StepResult] = field(default_factory=list)
    total_duration_ms: float = 0.0

    @property
    def success(self) -> bool:
        return all(s.success for s in self.steps)


class Pipeline:
    """
    Composable async data pipeline.

    Chains together transformation steps that process scraped data
    sequentially. Each step receives the output of the previous step.
    Failed steps short-circuit the pipeline and record diagnostics.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self._steps: List[tuple[str, StepFn]] = []

    def add_step(self, fn: StepFn, name: Optional[str] = None) -> "Pipeline":
        """Append a processing step. Returns self for chaining."""
        step_name = name or fn.__name__
        self._steps.append((step_name, fn))
        return self

    async def run(self, data: Any) -> PipelineResult:
        """Execute all steps in order, returning a PipelineResult."""
        result = PipelineResult(pipeline_name=self.name)
        current = data
        pipeline_start = time.perf_counter()

        for step_name, fn in self._steps:
            step_start = time.perf_counter()
            try:
                current = await fn(current)
                elapsed = (time.perf_counter() - step_start) * 1000
                result.steps.append(
                    StepResult(name=step_name, success=True, duration_ms=round(elapsed, 2))
                )
                logger.debug("pipeline.step.ok", pipeline=self.name, step=step_name)

            except Exception as exc:
                elapsed = (time.perf_counter() - step_start) * 1000
                result.steps.append(
                    StepResult(
                        name=step_name,
                        success=False,
                        duration_ms=round(elapsed, 2),
                        error=str(exc),
                    )
                )
                logger.error(
                    "pipeline.step.failed",
                    pipeline=self.name,
                    step=step_name,
                    error=str(exc),
                )
                break  # short-circuit on failure

        result.output = current
        result.total_duration_ms = round(
            (time.perf_counter() - pipeline_start) * 1000, 2
        )
        return result


# ── Built-in pipeline factory ────────────────────────────────────────

def create_default_pipeline() -> Pipeline:
    """
    Returns a sensible default pipeline for HTML → structured data.

    Steps are intentionally minimal here; production pipelines should
    be assembled per-scraper with domain-specific transformations.
    Full implementation available on request.
    """
    from src.extractors.structured import normalize_text, remove_empty_fields

    pipeline = Pipeline("default")
    pipeline.add_step(normalize_text, "normalize-text")
    pipeline.add_step(remove_empty_fields, "remove-empties")
    return pipeline
