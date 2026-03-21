"""
Job scheduler for recurring and one-off scraping tasks.

Provides a lightweight async scheduler that can trigger scraping jobs
on a cron-like schedule or at a specific datetime. Designed to work
standalone or be replaced by Celery / ARQ / APScheduler in production.

Note: full production scheduling with Redis-backed queues and
distributed locking is available on request.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional
from uuid import UUID, uuid4

from src.utils.logging import get_logger

logger = get_logger(__name__)


class ScheduleType(str, Enum):
    ONCE = "once"
    INTERVAL = "interval"
    CRON = "cron"


@dataclass
class ScheduledTask:
    """A task registered with the scheduler."""

    id: UUID = field(default_factory=uuid4)
    name: str = ""
    schedule_type: ScheduleType = ScheduleType.ONCE
    interval_seconds: Optional[int] = None
    cron_expression: Optional[str] = None
    next_run: Optional[datetime] = None
    enabled: bool = True
    callback: Optional[Callable[..., Coroutine[Any, Any, Any]]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class Scheduler:
    """
    Async task scheduler with interval and one-shot support.

    Usage
    -----
    >>> scheduler = Scheduler()
    >>> scheduler.add_interval("refresh-prices", callback=run_price_scrape, seconds=3600)
    >>> await scheduler.start()
    """

    def __init__(self) -> None:
        self._tasks: Dict[UUID, ScheduledTask] = {}
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None

    def add_interval(
        self,
        name: str,
        callback: Callable[..., Coroutine[Any, Any, Any]],
        seconds: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ScheduledTask:
        """Register a task that runs at a fixed interval."""
        task = ScheduledTask(
            name=name,
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=seconds,
            next_run=datetime.utcnow() + timedelta(seconds=seconds),
            callback=callback,
            metadata=metadata or {},
        )
        self._tasks[task.id] = task
        logger.info("scheduler.task.added", name=name, interval=seconds)
        return task

    def add_once(
        self,
        name: str,
        callback: Callable[..., Coroutine[Any, Any, Any]],
        run_at: datetime,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ScheduledTask:
        """Register a one-shot task for a specific datetime."""
        task = ScheduledTask(
            name=name,
            schedule_type=ScheduleType.ONCE,
            next_run=run_at,
            callback=callback,
            metadata=metadata or {},
        )
        self._tasks[task.id] = task
        logger.info("scheduler.task.added", name=name, run_at=run_at.isoformat())
        return task

    def remove(self, task_id: UUID) -> None:
        self._tasks.pop(task_id, None)

    def list_tasks(self) -> List[ScheduledTask]:
        return list(self._tasks.values())

    # ── Run loop ─────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the scheduler loop. Non-blocking — runs in background."""
        self._running = True
        self._loop_task = asyncio.create_task(self._run_loop())
        logger.info("scheduler.started")

    async def stop(self) -> None:
        """Gracefully stop the scheduler."""
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
        logger.info("scheduler.stopped")

    async def _run_loop(self) -> None:
        """Internal tick loop — checks every second for due tasks."""
        while self._running:
            now = datetime.utcnow()
            for task in list(self._tasks.values()):
                if not task.enabled or task.next_run is None:
                    continue
                if now >= task.next_run and task.callback:
                    logger.info("scheduler.task.firing", name=task.name)
                    asyncio.create_task(self._execute(task))

                    if task.schedule_type == ScheduleType.INTERVAL and task.interval_seconds:
                        task.next_run = now + timedelta(seconds=task.interval_seconds)
                    else:
                        task.enabled = False

            await asyncio.sleep(1)

    async def _execute(self, task: ScheduledTask) -> None:
        """Run a task's callback with error isolation."""
        try:
            await task.callback()
        except Exception as exc:
            logger.error("scheduler.task.error", name=task.name, error=str(exc))
