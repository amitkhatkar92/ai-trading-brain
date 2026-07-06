"""
iios/infrastructure/events/event_router.py
==========================================
Routes events to the correct set of subscribers based on event type.
"""

from __future__ import annotations

import threading
from typing import Optional

from ..infrastructure_models import EventEnvelope
from .event_subscriber import SubscriberDescriptor

__all__ = ["EventRouter"]


class EventRouter:
    """Routes an EventEnvelope to matching SubscriberDescriptors.

    Maintains two indexes:
      - exact type index:  event_type → list[descriptor]
      - wildcard list:     descriptors with event_type == "*" or glob patterns

    All lookups are O(1) for exact matches plus O(n_wildcards) for globs.
    """

    def __init__(self) -> None:
        self._exact: dict[str, list[SubscriberDescriptor]] = {}
        self._wildcards: list[SubscriberDescriptor] = []
        self._all_subs: dict[str, SubscriberDescriptor] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def add(self, descriptor: SubscriberDescriptor) -> None:
        """Register *descriptor* in the routing table."""
        with self._lock:
            self._all_subs[descriptor.subscription_id] = descriptor
            if descriptor.event_type == "*":
                self._wildcards.append(descriptor)
            elif descriptor.event_type.endswith(".*"):
                # Prefix glob — keep in wildcard list
                self._wildcards.append(descriptor)
            else:
                self._exact.setdefault(descriptor.event_type, []).append(descriptor)

    def remove(self, subscription_id: str) -> bool:
        """Remove a subscriber by ID. Returns True if found."""
        with self._lock:
            descriptor = self._all_subs.pop(subscription_id, None)
            if descriptor is None:
                return False
            # Remove from exact index
            if descriptor.event_type in self._exact:
                self._exact[descriptor.event_type] = [
                    d for d in self._exact[descriptor.event_type]
                    if d.subscription_id != subscription_id
                ]
            # Remove from wildcard list
            self._wildcards = [
                d for d in self._wildcards
                if d.subscription_id != subscription_id
            ]
            return True

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def route(self, envelope: EventEnvelope) -> list[SubscriberDescriptor]:
        """Return all enabled subscribers that match *envelope.event_type*."""
        with self._lock:
            exact = list(self._exact.get(envelope.event_type, []))
            wildcards = [
                d for d in self._wildcards
                if d.matches(envelope.event_type)
            ]
        combined = exact + wildcards
        return [d for d in combined if d.enabled]

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def all_subscriptions(self) -> list[SubscriberDescriptor]:
        with self._lock:
            return list(self._all_subs.values())

    def subscriptions_for(self, event_type: str) -> list[SubscriberDescriptor]:
        with self._lock:
            exact = list(self._exact.get(event_type, []))
            wilds = [d for d in self._wildcards if d.matches(event_type)]
        return exact + wilds

    def subscription_count(self) -> int:
        with self._lock:
            return len(self._all_subs)

    def clear(self) -> None:
        with self._lock:
            self._exact.clear()
            self._wildcards.clear()
            self._all_subs.clear()

    def __len__(self) -> int:
        return self.subscription_count()
