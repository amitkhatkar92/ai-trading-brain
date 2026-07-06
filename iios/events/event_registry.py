"""
iios/events/event_registry.py
================================
Registry of event types and their metadata schemas.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Type

from .event_exceptions import EventAlreadyRegisteredError, EventNotFoundError

__all__ = ["EventTypeDescriptor", "EventRegistry", "get_event_registry", "reset_event_registry"]

_lock = threading.Lock()
_registry: Optional["EventRegistry"] = None


@dataclass
class EventTypeDescriptor:
    """Describes a registered event type."""
    event_type: str
    description: str = ""
    schema: dict[str, Any] = field(default_factory=dict)
    deprecated: bool = False
    version: str = "1"
    owner: str = ""
    tags: list[str] = field(default_factory=list)
    validator: Optional[Callable[[dict], bool]] = None


class EventRegistry:
    """Catalogue of all known event types in the IIOS system.

    Usage::

        registry = get_event_registry()
        registry.register(EventTypeDescriptor(
            event_type="trade.executed",
            description="A trade has been executed",
            owner="execution_engine",
            schema={"symbol": "str", "qty": "int", "price": "float"},
        ))

        descriptor = registry.get("trade.executed")
        all_types = registry.list_all()
    """

    def __init__(self) -> None:
        self._descriptors: dict[str, EventTypeDescriptor] = {}
        self._lock = threading.RLock()

    def register(
        self,
        descriptor: EventTypeDescriptor,
        allow_override: bool = False,
    ) -> None:
        with self._lock:
            if descriptor.event_type in self._descriptors and not allow_override:
                raise EventAlreadyRegisteredError(descriptor.event_type)
            self._descriptors[descriptor.event_type] = descriptor

    def register_many(self, *descriptors: EventTypeDescriptor) -> None:
        for d in descriptors:
            self.register(d)

    def get(self, event_type: str) -> EventTypeDescriptor:
        with self._lock:
            desc = self._descriptors.get(event_type)
        if desc is None:
            raise EventNotFoundError(event_type)
        return desc

    def get_optional(self, event_type: str) -> Optional[EventTypeDescriptor]:
        with self._lock:
            return self._descriptors.get(event_type)

    def has(self, event_type: str) -> bool:
        with self._lock:
            return event_type in self._descriptors

    def unregister(self, event_type: str) -> bool:
        with self._lock:
            return self._descriptors.pop(event_type, None) is not None

    def list_all(self) -> list[EventTypeDescriptor]:
        with self._lock:
            return list(self._descriptors.values())

    def list_types(self) -> list[str]:
        with self._lock:
            return list(self._descriptors.keys())

    def list_by_owner(self, owner: str) -> list[EventTypeDescriptor]:
        with self._lock:
            return [d for d in self._descriptors.values() if d.owner == owner]

    def validate_payload(self, event_type: str, payload: dict[str, Any]) -> bool:
        """Run the validator for *event_type* if one is registered."""
        desc = self.get_optional(event_type)
        if desc is None or desc.validator is None:
            return True
        return desc.validator(payload)

    def clear(self) -> None:
        with self._lock:
            self._descriptors.clear()

    def __len__(self) -> int:
        return len(self._descriptors)


def get_event_registry() -> EventRegistry:
    global _registry
    with _lock:
        if _registry is None:
            _registry = EventRegistry()
        return _registry


def reset_event_registry() -> None:
    global _registry
    with _lock:
        _registry = None
