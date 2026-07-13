"""iios/investment/strategy/lifecycle/strategy_scheduler.py
Top-level strategy scheduler facade.

Integrates the ScheduleRegistry, PriorityScheduler, and a background
timer thread into a unified scheduling system.

Supported modes:
  Sequential  — max_concurrent=1 (caller-controlled)
  Parallel    — max_concurrent > 1 (default)
  Priority    — CRITICAL/HIGH strategies dispatch before NORMAL/LOW/BACKGROUND
  Periodic    — triggered every N seconds
  Time-based  — triggered at specific UTC HH:MM wall-clock times
  Event       — triggered by external fire_event() calls
  Conditional — triggered when condition_fn() returns True
  Dependency  — upstream strategies declared via declare_dependency()
"""
from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

from iios.investment.strategy.lifecycle.execution_queue import (
    ExecutionQueue,
    ExecutionRequest,
    QueueFullError,
    SchedulePriority,
)
from iios.investment.strategy.lifecycle.priority_scheduler import PriorityScheduler
from iios.investment.strategy.lifecycle.schedule_registry import (
    ScheduleEntry,
    ScheduleRegistry,
    ScheduleType,
)

logger = logging.getLogger(__name__)


class StrategyScheduler:
    """
    Manages periodic, time-based, event-driven, and conditional strategy triggers,
    and dispatches them to the PriorityScheduler for concurrent execution.
    """

    _TICK_INTERVAL_S: float = 0.5  # background loop polling interval

    def __init__(
        self,
        executor_fn: Callable[[ExecutionRequest], None],
        max_concurrent: int = 32,
        max_queue_depth: int = 10_000,
        thread_pool: Optional[ThreadPoolExecutor] = None,
    ) -> None:
        self._queue = ExecutionQueue(max_size=max_queue_depth)
        self._schedule_registry = ScheduleRegistry()
        self._priority_scheduler = PriorityScheduler(
            queue=self._queue,
            executor_fn=executor_fn,
            max_concurrent=max_concurrent,
            thread_pool=thread_pool,
        )
        self._lock = threading.RLock()
        self._paused = False
        self._running = False
        self._thread: Optional[threading.Thread] = None
        # event_name → list of subscribed strategy_ids
        self._event_subscribers: Dict[str, List[str]] = {}

    # ── Engine lifecycle ──────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the background scheduling loop."""
        with self._lock:
            if self._running:
                return
            self._running = True
        self._thread = threading.Thread(
            target=self._background_loop,
            name="iios-scheduler-loop",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "StrategyScheduler started (max_concurrent=%d)",
            self._priority_scheduler._max_concurrent,
        )

    def stop(self, wait: bool = True) -> None:
        """Stop the background loop and optionally drain the thread pool."""
        with self._lock:
            self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        self._priority_scheduler.shutdown(wait=wait)
        logger.info("StrategyScheduler stopped")

    def pause(self) -> None:
        with self._lock:
            self._paused = True
        self._priority_scheduler.pause()

    def resume(self) -> None:
        with self._lock:
            self._paused = False
        self._priority_scheduler.resume()

    # ── Schedule registration ─────────────────────────────────────────────────

    def schedule(self, entry: ScheduleEntry, replace: bool = False) -> None:
        """Register a schedule entry for a strategy."""
        self._schedule_registry.register(entry, replace=replace)
        if entry.schedule_type == ScheduleType.EVENT and entry.trigger_event:
            with self._lock:
                self._event_subscribers.setdefault(
                    entry.trigger_event, []
                ).append(entry.strategy_id)
        logger.debug(
            "Scheduled %s (%s)", entry.strategy_id, entry.schedule_type.value
        )

    def unschedule(self, strategy_id: str) -> None:
        """Remove all scheduling configuration for a strategy."""
        entry = self._schedule_registry.get(strategy_id)
        if entry and entry.trigger_event:
            with self._lock:
                subscribers = self._event_subscribers.get(entry.trigger_event, [])
                try:
                    subscribers.remove(strategy_id)
                except ValueError:
                    pass
        self._schedule_registry.unregister(strategy_id)

    # ── Immediate / event submission ──────────────────────────────────────────

    def submit_immediate(
        self,
        strategy_id: str,
        context: object,
        priority: SchedulePriority = SchedulePriority.NORMAL,
        dependencies: Optional[List[str]] = None,
    ) -> Optional[ExecutionRequest]:
        """Bypass the schedule and submit a strategy for immediate execution."""
        with self._lock:
            if self._paused:
                return None
        req = self._priority_scheduler.submit(
            strategy_id=strategy_id,
            context=context,
            priority=priority,
            dependencies=dependencies,
        )
        self._priority_scheduler.tick()
        return req

    def fire_event(self, event_name: str, context: object) -> int:
        """
        Trigger all strategies subscribed to the named event.

        Returns the number of strategies dispatched.
        """
        with self._lock:
            subscribers = list(self._event_subscribers.get(event_name, []))
        dispatched = 0
        for strategy_id in subscribers:
            entry = self._schedule_registry.get(strategy_id)
            if entry and entry.enabled:
                try:
                    self._priority_scheduler.submit(
                        strategy_id=strategy_id,
                        context=context,
                        priority=SchedulePriority(entry.priority),
                    )
                    self._schedule_registry.update_last_triggered(strategy_id)
                    dispatched += 1
                except QueueFullError:
                    logger.warning(
                        "Queue full — event dispatch skipped for %s", strategy_id
                    )
        self._priority_scheduler.tick()
        return dispatched

    # ── Observability ─────────────────────────────────────────────────────────

    @property
    def queue_depth(self) -> int:
        return self._queue.depth

    @property
    def in_flight_count(self) -> int:
        return self._priority_scheduler.in_flight_count

    @property
    def in_flight_ids(self) -> List[str]:
        return self._priority_scheduler.in_flight_ids

    @property
    def schedule_registry(self) -> ScheduleRegistry:
        return self._schedule_registry

    # ── Background loop ───────────────────────────────────────────────────────

    def _background_loop(self) -> None:
        """Drives periodic, time-based, and conditional schedules."""
        while self._running:
            try:
                if not self._paused:
                    self._process_periodic()
                    self._process_time_based()
                    self._process_conditional()
                    self._priority_scheduler.tick()
            except Exception:  # noqa: BLE001
                logger.exception("Scheduler background loop error")
            time.sleep(self._TICK_INTERVAL_S)

    def _process_periodic(self) -> None:
        now = datetime.now(timezone.utc)
        for entry in self._schedule_registry.enabled_entries():
            if entry.schedule_type != ScheduleType.PERIODIC:
                continue
            if entry.interval_seconds <= 0:
                continue
            last = entry.last_triggered_at
            if last is None:
                elapsed = entry.interval_seconds + 1.0  # trigger on first pass
            else:
                last_aware = last if last.tzinfo else last.replace(tzinfo=timezone.utc)
                elapsed = (now - last_aware).total_seconds()
            if elapsed >= entry.interval_seconds:
                self._schedule_registry.update_last_triggered(entry.strategy_id)
                self._try_submit(entry, context=None)

    def _process_time_based(self) -> None:
        now = datetime.now(timezone.utc)
        current_hhmm = now.strftime("%H:%M")
        for entry in self._schedule_registry.enabled_entries():
            if entry.schedule_type != ScheduleType.TIME_BASED:
                continue
            if current_hhmm not in entry.trigger_times:
                continue
            last = entry.last_triggered_at
            if last is not None:
                last_aware = last if last.tzinfo else last.replace(tzinfo=timezone.utc)
                if (now - last_aware).total_seconds() < 60:
                    continue  # already fired within this minute
            self._schedule_registry.update_last_triggered(entry.strategy_id)
            self._try_submit(entry, context=None)

    def _process_conditional(self) -> None:
        for entry in self._schedule_registry.enabled_entries():
            if entry.schedule_type != ScheduleType.CONDITIONAL:
                continue
            if entry.condition_fn is None:
                continue
            try:
                should_run = entry.condition_fn()
            except Exception:  # noqa: BLE001
                logger.exception(
                    "Condition function error for strategy %s", entry.strategy_id
                )
                continue
            if should_run:
                self._schedule_registry.update_last_triggered(entry.strategy_id)
                self._try_submit(entry, context=None)

    def _try_submit(self, entry: ScheduleEntry, context: object) -> None:
        try:
            self._priority_scheduler.submit(
                strategy_id=entry.strategy_id,
                context=context,
                priority=SchedulePriority(entry.priority),
            )
        except QueueFullError:
            logger.warning(
                "Queue full — scheduled trigger skipped for %s", entry.strategy_id
            )
