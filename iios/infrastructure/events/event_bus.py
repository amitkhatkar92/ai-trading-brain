"""
iios/infrastructure/events/event_bus.py
========================================
Main event bus facade — publish, subscribe, and process events.

Architecture:
  - EventPublisher  — creates and enqueues EventEnvelopes
  - EventQueue      — thread-safe priority queue
  - EventRouter     — maps event_type → subscribers
  - EventDispatcher — delivers to each subscriber with retry + DLQ
  - Background worker thread — drains the queue continuously
"""

from __future__ import annotations

import logging
import queue
import threading
import uuid
from typing import Any, Callable, Optional

from ..infrastructure_constants import (
    DEFAULT_EVENT_QUEUE_SIZE,
    MAX_EVENT_SUBSCRIBERS,
    EventPriority,
)
from ..infrastructure_exceptions import EventBusError
from ..infrastructure_models import EventEnvelope, DeadLetterEntry
from .event_dispatcher import EventDispatcher
from .event_publisher import EventPublisher
from .event_queue import DeadLetterQueue, EventQueue
from .event_router import EventRouter
from .event_subscriber import Subscriber, SubscriberDescriptor, EventHandler

__all__ = ["EventBus", "get_event_bus", "reset_event_bus"]

_LOG = logging.getLogger("iios.infrastructure.events.bus")

_bus_lock = threading.Lock()
_bus: Optional["EventBus"] = None


class EventBus:
    """Asynchronous in-process event bus.

    Usage::

        bus = get_event_bus()
        bus.start()

        # Subscribe
        sub_id = bus.subscribe("risk.breach", my_handler)

        # Publish
        pub = bus.publisher("risk_guardian")
        pub.publish("risk.breach", {"vix": 47.2})

        bus.stop()
    """

    def __init__(
        self,
        queue_size: int = DEFAULT_EVENT_QUEUE_SIZE,
        max_retries: int = 3,
    ) -> None:
        self._queue = EventQueue(maxsize=queue_size)
        self._dlq = DeadLetterQueue()
        self._router = EventRouter()
        self._dispatcher = EventDispatcher(dead_letter=self._dlq, default_max_retries=max_retries)
        self._worker: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        self._lock = threading.RLock()
        self._events_processed = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background dispatch worker."""
        with self._lock:
            if self._running:
                return
            self._stop_event.clear()
            self._worker = threading.Thread(
                target=self._dispatch_loop,
                daemon=True,
                name="iios.event_bus.worker",
            )
            self._worker.start()
            self._running = True
        _LOG.info("EventBus started")

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the worker to stop and wait for it to finish."""
        with self._lock:
            if not self._running:
                return
            self._stop_event.set()
            self._running = False

        if self._worker is not None:
            self._worker.join(timeout=timeout)
            self._worker = None
        _LOG.info("EventBus stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------
    # Subscription API
    # ------------------------------------------------------------------

    def subscribe(
        self,
        event_type: str,
        handler: EventHandler,
        *,
        priority: int = EventPriority.NORMAL.value,
        name: str = "",
        max_retries: int = 3,
    ) -> str:
        """Register *handler* for *event_type*.

        Args:
            event_type: Exact type, prefix glob (``"risk.*"``), or ``"*"`` for all.
            handler:    Callable ``(EventEnvelope) -> None``.
            priority:   Dispatch order among peers (higher = first).
            name:       Human-readable label.
            max_retries: Max delivery attempts before dead-lettering.

        Returns:
            Subscription ID (use to unsubscribe).
        """
        if self._router.subscription_count() >= MAX_EVENT_SUBSCRIBERS:
            raise EventBusError(
                "Maximum subscriber limit reached",
                code="INF-EVT-001",
                context={"max": MAX_EVENT_SUBSCRIBERS},
            )
        descriptor = SubscriberDescriptor(
            event_type=event_type,
            handler=handler,
            priority=priority,
            name=name or getattr(handler, "__name__", str(handler)),
            max_retries=max_retries,
        )
        self._router.add(descriptor)
        return descriptor.subscription_id

    def subscribe_class(self, subscriber: Subscriber) -> str:
        """Register a ``Subscriber`` subclass instance."""
        self._router.add(subscriber.descriptor)
        return subscriber.subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription. Returns True if it was found."""
        return self._router.remove(subscription_id)

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def publisher(self, source: str = "") -> EventPublisher:
        """Create an ``EventPublisher`` bound to this bus."""
        return EventPublisher(self._queue, source=source)

    def publish(
        self,
        event_type: str,
        payload: Any = None,
        *,
        source: str = "",
        priority: int = EventPriority.NORMAL.value,
        correlation_id: Optional[str] = None,
        max_retries: int = 3,
    ) -> EventEnvelope:
        """Publish a single event directly."""
        pub = self.publisher(source)
        return pub.publish(
            event_type,
            payload,
            priority=priority,
            correlation_id=correlation_id,
            max_retries=max_retries,
        )

    def publish_sync(
        self,
        event_type: str,
        payload: Any = None,
        *,
        source: str = "",
        priority: int = EventPriority.NORMAL.value,
    ) -> dict[str, bool]:
        """Publish and dispatch synchronously (no queue — for testing)."""
        envelope = EventEnvelope(
            event_type=event_type,
            payload=payload,
            source=source,
            priority=priority,
        )
        subscribers = self._router.route(envelope)
        return self._dispatcher.dispatch(envelope, subscribers)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def subscription_count(self) -> int:
        return self._router.subscription_count()

    def queue_size(self) -> int:
        return self._queue.qsize

    def events_processed(self) -> int:
        return self._events_processed

    def dead_letters(self) -> list[DeadLetterEntry]:
        return self._dlq.all()

    def drain_dead_letters(self, n: int = 100) -> list[DeadLetterEntry]:
        return self._dlq.drain(n)

    def stats(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "queue_size": self._queue.qsize,
            "events_enqueued": self._queue.total_enqueued,
            "events_processed": self._events_processed,
            "dispatcher_errors": self._dispatcher.error_count,
            "dead_letter_count": self._dlq.size,
            "subscription_count": self._router.subscription_count(),
        }

    def reset(self) -> None:
        """Stop and clear all state (for testing)."""
        self.stop()
        self._router.clear()
        self._dlq.clear()
        self._events_processed = 0

    # ------------------------------------------------------------------
    # Internal worker
    # ------------------------------------------------------------------

    def _dispatch_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                envelope = self._queue.get(block=True, timeout=0.1)
            except queue.Empty:
                continue
            try:
                subscribers = self._router.route(envelope)
                self._dispatcher.dispatch(envelope, subscribers)
                self._queue.task_done()
            except Exception as exc:
                _LOG.exception("Unexpected error dispatching %s: %s", envelope.event_type, exc)
                self._queue.task_done()
            finally:
                self._events_processed += 1


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------


def get_event_bus() -> EventBus:
    """Return (or create) the global EventBus instance."""
    global _bus
    with _bus_lock:
        if _bus is None:
            _bus = EventBus()
        return _bus


def reset_event_bus() -> None:
    """Reset the global EventBus (for testing)."""
    global _bus
    with _bus_lock:
        if _bus is not None:
            _bus.reset()
        _bus = None
