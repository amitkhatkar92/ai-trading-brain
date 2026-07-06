"""
iios/events/event_bus.py
=========================
Main Event Bus — the central publish/subscribe hub for IIOS.

Features:
  - Publish (sync dispatch)
  - Subscribe / Unsubscribe with priority, predicate, one_time
  - Broadcast (deliver to ALL subscribers regardless of event_type)
  - Sticky events (replay last value to new subscribers)
  - Delayed / Scheduled events (background timer thread)
  - Persistent event log (in-memory ring buffer)
  - Dead-letter storage for failed events
  - Idempotency (optional duplicate detection by event_id)
  - Thread-safe
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .event_dispatcher import EventDispatcher, SubscriberRecord, DispatchResult
from .event_metadata import Event, EventMetadata
from .event_priority import EventPriority
from .event_factory import EventFactory
from .event_exceptions import SubscribeError, PublishError, IdempotencyError
from .event_constants import (
    WILDCARD, BROADCAST_TOPIC, DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_DELAY, DEFAULT_QUEUE_SIZE,
)

__all__ = ["EventBus", "BusStats", "get_event_bus", "reset_event_bus"]

_LOG = logging.getLogger("iios.events.bus")

EventHandler = Callable[[Event], None]

_bus_lock = threading.Lock()
_bus: Optional["EventBus"] = None


@dataclass
class BusStats:
    published: int = 0
    consumed: int = 0
    failed: int = 0
    sticky_hits: int = 0
    dead_lettered: int = 0
    duplicates_rejected: int = 0
    scheduled_fired: int = 0


class EventBus:
    """Central event bus for the IIOS platform.

    Usage::

        bus = get_event_bus()

        # Subscribe
        sub_id = bus.subscribe("trade.executed", handle_trade)
        bus.subscribe("trade.*", handle_all_trades)   # wildcard

        # Publish
        event = EventFactory.make("trade.executed", {"symbol": "RELIANCE", "qty": 10})
        result = bus.publish(event)

        # Broadcast to ALL subscribers
        bus.broadcast(event)

        # Sticky — new subscribers receive the last value immediately
        bus.subscribe_sticky("market.regime", handle_regime)

        # One-time
        bus.subscribe_once("session.started", handle_once)

        # Delayed
        bus.publish_delayed(event, delay=5.0)
    """

    def __init__(
        self,
        max_history: int = DEFAULT_QUEUE_SIZE,
        detect_duplicates: bool = False,
    ) -> None:
        self._dispatcher = EventDispatcher(isolate_failures=True)
        self._sticky_cache: dict[str, Event] = {}            # event_type → last event
        self._history: deque[Event] = deque(maxlen=max_history)
        self._dlq: list[tuple[Event, str]] = []              # (event, reason)
        self._seen_ids: deque[str] = deque(maxlen=10_000)    # for duplicate detection
        self._detect_duplicates = detect_duplicates
        self._stats = BusStats()
        self._scheduled: list[tuple[float, Event]] = []     # (fire_at, event)
        self._scheduler_thread: Optional[threading.Thread] = None
        self._scheduler_running = False
        self._lock = threading.RLock()

    # ── Subscribe ─────────────────────────────────────────────────────────────

    def subscribe(
        self,
        event_type: str,
        handler: EventHandler,
        *,
        priority: EventPriority = EventPriority.NORMAL,
        predicate: Optional[Callable[[Event], bool]] = None,
        max_retries: int = 0,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        name: str = "",
    ) -> str:
        sub_id = str(uuid.uuid4())
        record = SubscriberRecord(
            sub_id=sub_id,
            handler=handler,
            event_type=event_type,
            priority=priority,
            predicate=predicate,
            max_retries=max_retries,
            retry_delay=retry_delay,
            name=name or handler.__name__,
        )
        self._dispatcher.add_subscriber(record)

        # Sticky replay: if there's a cached event, deliver immediately
        with self._lock:
            cached = self._sticky_cache.get(event_type)
        if cached is not None:
            try:
                handler(cached)
                with self._lock:
                    self._stats.sticky_hits += 1
            except Exception as exc:
                _LOG.warning("Sticky replay failed for %s: %s", event_type, exc)

        return sub_id

    def subscribe_once(
        self,
        event_type: str,
        handler: EventHandler,
        **kw: Any,
    ) -> str:
        sub_id = str(uuid.uuid4())
        record = SubscriberRecord(
            sub_id=sub_id,
            handler=handler,
            event_type=event_type,
            one_time=True,
            name=kw.get("name", handler.__name__),
            priority=kw.get("priority", EventPriority.NORMAL),
            predicate=kw.get("predicate"),
        )
        self._dispatcher.add_subscriber(record)
        return sub_id

    def subscribe_sticky(
        self,
        event_type: str,
        handler: EventHandler,
        **kw: Any,
    ) -> str:
        """Subscribe and receive the last sticky event immediately if available."""
        return self.subscribe(event_type, handler, **kw)

    def unsubscribe(self, sub_id: str) -> bool:
        return self._dispatcher.remove_subscriber(sub_id)

    # ── Publish ───────────────────────────────────────────────────────────────

    def publish(self, event: Event) -> DispatchResult:
        if event.is_expired:
            _LOG.debug("Dropping expired event %s", event.event_type)
            result = DispatchResult(event_id=event.event_id, event_type=event.event_type)
            result.skipped = 1
            return result

        if self._detect_duplicates:
            with self._lock:
                if event.event_id in self._seen_ids:
                    self._stats.duplicates_rejected += 1
                    raise IdempotencyError(event.event_id)
                self._seen_ids.append(event.event_id)

        # Cache sticky events
        if event.metadata.sticky:
            with self._lock:
                self._sticky_cache[event.event_type] = event

        # Store in history
        with self._lock:
            self._history.append(event)
            self._stats.published += 1

        result = self._dispatcher.dispatch(event)

        with self._lock:
            self._stats.consumed += result.succeeded
            self._stats.failed += result.failed

        # Dead-letter failed deliveries
        if result.failed > 0:
            for err in result.errors:
                with self._lock:
                    self._dlq.append((event, err))
                    self._stats.dead_lettered += 1

        return result

    def broadcast(self, event: Event) -> int:
        """Deliver event to every subscriber regardless of their event_type filter."""
        with self._lock:
            subs = self._dispatcher.list_subscribers()

        count = 0
        for sub in subs:
            try:
                sub.handler(event)
                count += 1
            except Exception as exc:
                _LOG.warning("Broadcast handler %s failed: %s", sub.name, exc)

        return count

    def publish_delayed(self, event: Event, delay: float) -> str:
        """Schedule event delivery after *delay* seconds."""
        event.metadata.scheduled_at = time.time() + delay
        with self._lock:
            self._scheduled.append((event.metadata.scheduled_at, event))
            self._scheduled.sort(key=lambda x: x[0])
        self._ensure_scheduler()
        return event.event_id

    def publish_scheduled(self, event: Event, at: float) -> str:
        """Schedule event delivery at Unix timestamp *at*."""
        event.metadata.scheduled_at = at
        with self._lock:
            self._scheduled.append((at, event))
            self._scheduled.sort(key=lambda x: x[0])
        self._ensure_scheduler()
        return event.event_id

    # ── Query ─────────────────────────────────────────────────────────────────

    def history(self, event_type: Optional[str] = None, limit: int = 100) -> list[Event]:
        with self._lock:
            events = list(self._history)
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def dead_letter_queue(self) -> list[tuple[Event, str]]:
        with self._lock:
            return list(self._dlq)

    def clear_dlq(self) -> int:
        with self._lock:
            count = len(self._dlq)
            self._dlq.clear()
        return count

    def stats(self) -> BusStats:
        with self._lock:
            return BusStats(
                published=self._stats.published,
                consumed=self._stats.consumed,
                failed=self._stats.failed,
                sticky_hits=self._stats.sticky_hits,
                dead_lettered=self._stats.dead_lettered,
                duplicates_rejected=self._stats.duplicates_rejected,
                scheduled_fired=self._stats.scheduled_fired,
            )

    def subscriber_count(self, event_type: Optional[str] = None) -> int:
        return self._dispatcher.subscriber_count(event_type)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        self._ensure_scheduler()

    def stop(self) -> None:
        self._scheduler_running = False
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=2.0)

    def reset(self) -> None:
        self.stop()
        self._dispatcher.clear()
        with self._lock:
            self._sticky_cache.clear()
            self._history.clear()
            self._dlq.clear()
            self._seen_ids.clear()
            self._scheduled.clear()
            self._stats = BusStats()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _ensure_scheduler(self) -> None:
        with self._lock:
            if self._scheduler_running:
                return
            self._scheduler_running = True
        t = threading.Thread(target=self._scheduler_loop, daemon=True, name="iios.event-scheduler")
        self._scheduler_thread = t
        t.start()

    def _scheduler_loop(self) -> None:
        while self._scheduler_running:
            now = time.time()
            due: list[Event] = []
            with self._lock:
                remaining = []
                for fire_at, event in self._scheduled:
                    if fire_at <= now:
                        due.append(event)
                    else:
                        remaining.append((fire_at, event))
                self._scheduled = remaining

            for event in due:
                try:
                    self.publish(event)
                    with self._lock:
                        self._stats.scheduled_fired += 1
                except Exception as exc:
                    _LOG.warning("Scheduled event %s failed: %s", event.event_type, exc)

            time.sleep(0.05)


def get_event_bus() -> EventBus:
    global _bus
    with _bus_lock:
        if _bus is None:
            _bus = EventBus()
        return _bus


def reset_event_bus() -> None:
    global _bus
    with _bus_lock:
        if _bus is not None:
            _bus.stop()
        _bus = None
