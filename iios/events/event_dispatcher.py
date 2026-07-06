"""
iios/events/event_dispatcher.py
================================
Core dispatcher: invokes handlers for a given event, with retry, isolation,
priority ordering, and timing.
"""

from __future__ import annotations

import fnmatch
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Union

from .event_metadata import Event
from .event_priority import EventPriority
from .event_exceptions import HandlerError, RetryExhaustedError
from .event_constants import DEFAULT_MAX_RETRIES, DEFAULT_RETRY_DELAY, DEFAULT_RETRY_BACKOFF, WILDCARD

__all__ = ["SubscriberRecord", "DispatchResult", "EventDispatcher"]

_LOG = logging.getLogger("iios.events.dispatcher")

EventHandler = Callable[[Event], None]


@dataclass
class SubscriberRecord:
    """Registered handler with delivery metadata."""
    sub_id: str
    handler: EventHandler
    event_type: str                        # "" = wildcard
    priority: EventPriority = EventPriority.NORMAL
    one_time: bool = False
    predicate: Optional[Callable[[Event], bool]] = None
    max_retries: int = 0
    retry_delay: float = DEFAULT_RETRY_DELAY
    name: str = ""
    created_at: float = field(default_factory=time.monotonic)
    calls: int = 0
    failures: int = 0

    def matches(self, event: Event) -> bool:
        if self.event_type:
            if self.event_type == WILDCARD:
                pass  # match everything
            elif "*" in self.event_type or "?" in self.event_type or "[" in self.event_type:
                if not fnmatch.fnmatch(event.event_type, self.event_type):
                    return False
            elif self.event_type != event.event_type:
                return False
        if self.predicate and not self.predicate(event):
            return False
        return True


@dataclass
class DispatchResult:
    """Outcome of dispatching one event."""
    event_id: str
    event_type: str
    total_handlers: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    duration_ms: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def all_succeeded(self) -> bool:
        return self.failed == 0


class EventDispatcher:
    """Invokes all matching handlers for a given event.

    Handlers are sorted by priority, isolated (one failure doesn't stop others),
    and optionally retried with exponential backoff.

    Usage::

        dispatcher = EventDispatcher()
        sub = SubscriberRecord(sub_id="s1", handler=my_fn, event_type="trade.*")
        dispatcher.add_subscriber(sub)
        result = dispatcher.dispatch(event)
    """

    def __init__(self, isolate_failures: bool = True) -> None:
        self._subscribers: dict[str, SubscriberRecord] = {}
        self._lock = threading.RLock()
        self._isolate = isolate_failures
        self._remove_queue: list[str] = []  # one-time subs to remove after dispatch

    def subscribe(
        self,
        event_type: str,
        handler: EventHandler,
        *,
        priority: Union[EventPriority, int] = EventPriority.NORMAL,
        one_time: bool = False,
        predicate: Optional[Callable[[Event], bool]] = None,
        max_retries: int = 0,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        name: str = "",
    ) -> str:
        """Convenience wrapper: create a SubscriberRecord and register it."""
        sub_id = str(uuid.uuid4())
        record = SubscriberRecord(
            sub_id=sub_id,
            handler=handler,
            event_type=event_type,
            priority=priority,  # type: ignore[arg-type]
            one_time=one_time,
            predicate=predicate,
            max_retries=max_retries,
            retry_delay=retry_delay,
            name=name or getattr(handler, "__name__", ""),
        )
        self.add_subscriber(record)
        return sub_id

    def add_subscriber(self, record: SubscriberRecord) -> None:
        with self._lock:
            self._subscribers[record.sub_id] = record

    def remove_subscriber(self, sub_id: str) -> bool:
        with self._lock:
            return self._subscribers.pop(sub_id, None) is not None

    def has_subscriber(self, sub_id: str) -> bool:
        with self._lock:
            return sub_id in self._subscribers

    def subscriber_count(self, event_type: Optional[str] = None) -> int:
        with self._lock:
            if event_type is None:
                return len(self._subscribers)
            return sum(
                1 for s in self._subscribers.values()
                if s.event_type == event_type or s.event_type == ""
            )

    def dispatch(self, event: Event) -> DispatchResult:
        t0 = time.monotonic()
        result = DispatchResult(event_id=event.event_id, event_type=event.event_type)

        with self._lock:
            candidates = [
                s for s in self._subscribers.values()
                if s.matches(event)
            ]
        # Sort by priority (lower int = higher priority); accept raw int too
        candidates.sort(key=lambda s: int(s.priority))

        for sub in candidates:
            result.total_handlers += 1
            try:
                _invoke_with_retry(sub, event)
                sub.calls += 1
                result.succeeded += 1
            except Exception as exc:
                sub.failures += 1
                result.failed += 1
                result.errors.append(f"{sub.name or sub.sub_id}: {exc}")
                _LOG.warning("Handler %s failed for %s: %s", sub.name or sub.sub_id, event.event_type, exc)
                if not self._isolate:
                    raise

        # Remove one-time subscribers after dispatch (outside lock to avoid deadlock)
        with self._lock:
            for sub in candidates:
                if sub.one_time:
                    self._subscribers.pop(sub.sub_id, None)

        result.duration_ms = (time.monotonic() - t0) * 1000
        return result

    def list_subscribers(self, event_type: Optional[str] = None) -> list[SubscriberRecord]:
        with self._lock:
            subs = list(self._subscribers.values())
        if event_type:
            subs = [s for s in subs if s.event_type == event_type or s.event_type == ""]
        return subs

    def clear(self) -> None:
        with self._lock:
            self._subscribers.clear()


def _invoke_with_retry(sub: SubscriberRecord, event: Event) -> None:
    attempts = 0
    last_exc: Optional[Exception] = None
    while attempts <= sub.max_retries:
        try:
            sub.handler(event)
            return
        except Exception as exc:
            last_exc = exc
            attempts += 1
            if attempts <= sub.max_retries:
                delay = sub.retry_delay * (DEFAULT_RETRY_BACKOFF ** (attempts - 1))
                time.sleep(min(delay, 5.0))
    raise last_exc  # type: ignore[misc]
