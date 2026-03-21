"""
Tests for the data pipeline orchestration module.

Validates step chaining, error handling, and telemetry recording.
"""

from __future__ import annotations

import pytest

from src.core.pipeline import Pipeline, PipelineResult


# ── Helper steps ─────────────────────────────────────────────────────

async def double_value(data: dict) -> dict:
    return {k: v * 2 if isinstance(v, (int, float)) else v for k, v in data.items()}


async def add_label(data: dict) -> dict:
    data["label"] = "processed"
    return data


async def exploding_step(data: dict) -> dict:
    raise RuntimeError("Intentional failure")


# ── Tests ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_runs_steps_in_order():
    pipeline = Pipeline("test")
    pipeline.add_step(double_value, "double")
    pipeline.add_step(add_label, "label")

    result = await pipeline.run({"count": 5})
    assert result.success
    assert result.output["count"] == 10
    assert result.output["label"] == "processed"
    assert len(result.steps) == 2


@pytest.mark.asyncio
async def test_pipeline_records_telemetry():
    pipeline = Pipeline("timed")
    pipeline.add_step(add_label)

    result = await pipeline.run({"x": 1})
    assert result.total_duration_ms > 0
    assert result.steps[0].duration_ms >= 0


@pytest.mark.asyncio
async def test_pipeline_short_circuits_on_failure():
    pipeline = Pipeline("failing")
    pipeline.add_step(exploding_step, "boom")
    pipeline.add_step(add_label, "label")

    result = await pipeline.run({"x": 1})
    assert not result.success
    assert len(result.steps) == 1
    assert result.steps[0].error is not None
    assert "label" not in (result.output or {})


@pytest.mark.asyncio
async def test_empty_pipeline():
    pipeline = Pipeline("empty")
    result = await pipeline.run({"data": "unchanged"})
    assert result.success
    assert result.output == {"data": "unchanged"}
