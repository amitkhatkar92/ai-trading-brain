"""
iios/infrastructure/events/event_dispatcher.py
===============================================
Dispatches events to matching subscribers with retry and dead-letter handling.
"""

from __future__ import annotations

import logging
import time
import threading
from typing import Callable, Optional

from ..infrastructure_constants import DEFAULT_RETRY_BACKOFF_SECONDS, DEFAULT_RETRY_ATTEMPTS
from ..infrastructure_models import EventEnvelope
from .event_subscriber import SubscriberDescriptor
from .event_queue import DeadLetterQueue

__all__ = ["EventDispatcher"]

_LOG = logging.getLogger("iios.infrastructure.events.dispatcher")


class EventDispatcher:
    """Delivers an ``EventEnvelope`` to a list of matching subscribers.

    Retries failed deliveries with exponential backoff, then moves
    undeliverable events to the dead-letter queue.
    """

    def __init__(
        self,
        dead_letter: Optional[DeadLetterQueue] = None,
        default_max_retries: int = DEFAULT_RETRY_ATTEMPTS,
        backoff_base: float = DEFAULT_RETRY_BACKOFF_SECONDS,
    ) -> None:
        self._dlq = dead_letter or DeadLetterQueue()
        self._default_retries = default_max_retries
        self._backoff_base = backoff_base
        self._dispatch_count = 0
        self._error_count = 0
        self._lock = threading.Lock()

    def dispatch(
        self,
        envelope: EventEnvelope,
        subscribers: list[SubscriberDescriptor],
    ) -> dict[str, bool]:
        """Dispatch *envelope* to all matching *subscribers*.

        Returns:
            Mapping of subscription_id → success flag.
        """
        results: dict[str, bool] = {}
        matching = [s for s in subscribers if s.matches(envelope.event_type) and s.enabled]

        # Sort by priority descending (higher priority first)
        matching.sort(key=lambda s: s.priority, reverse=True)

        for sub in matching:
            ok = self._deliver(envelope, sub)
            results[sub.subscription_id] = ok

        with self._lock:
            self._dispatch_count += 1

        return results

    def _deliver(self, envelope: EventEnvelope, sub: SubscriberDescriptor) -> bool:
        max_retries = sub.max_retries
        handler = sub.handler
        if handler is None:
            return False

        for attempt in range(max_retries + 1):
            try:
                handler(envelope)
                sub.call_count += 1
                return True
            except Exception as exc:
                sub.error_count += 1
                with self._lock:
                    self._error_count += 1
                if attempt < max_retries:
                    delay = self._backoff_base * (2 ** attempt)
                    _LOG.warning(
                        "Event %s delivery attempt %d/%d failed for '%s': %s — retrying in %.2fs",
                        envelope.event_type, attempt + 1, max_retries + 1,
                        sub.name, exc, delay,
                    )
                    time.sleep(delay)
                else:
                    _LOG.error(
                        "Event %s permanently failed for '%s' after %d attempts: %s",
                        envelope.event_type, sub.name, max_retries + 1, exc,
                    )
                    self._dlq.add(envelope, str(exc), subscriber=sub.name)
                    return False

        return False

    @property
    def dispatch_count(self) -> int:
        return self._dispatch_count

    @property
    def error_count(self) -> int:
        return self._error_count

    @property
    def dead_letter_queue(self) -> DeadLetterQueue:
        return self._dlq
