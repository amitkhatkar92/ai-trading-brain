"""
iios/events/messaging/message_router.py
========================================
Routes messages to named destination queues based on rules.
"""

from __future__ import annotations

import fnmatch
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .message import Message
from ..event_exceptions import NoRouteError

__all__ = ["MessageRoute", "MessageRouter"]


@dataclass
class MessageRoute:
    name: str
    pattern: str                   # fnmatch pattern on message type / destination
    destination: str
    predicate: Optional[Callable[[Message], bool]] = None
    priority: int = 100
    transform: Optional[Callable[[Message], Message]] = None

    def matches(self, msg: Message) -> bool:
        dest = msg.envelope.destination or msg.payload.get("type", "")
        if self.pattern != "*" and not fnmatch.fnmatch(dest, self.pattern):
            return False
        if self.predicate and not self.predicate(msg):
            return False
        return True


class MessageRouter:
    """Routes messages to named destinations.

    Usage::

        router = MessageRouter(default_destination="main_queue")
        router.add_route(MessageRoute(
            name="urgent",
            pattern="order.*",
            destination="priority_queue",
            predicate=lambda m: m.envelope.priority < 20,
            priority=10,
        ))
        destinations = router.route(message)
    """

    def __init__(self, default_destination: Optional[str] = None) -> None:
        self._routes: dict[str, MessageRoute] = {}
        self._default = default_destination
        self._lock = threading.RLock()

    def add_route(self, route: MessageRoute) -> None:
        with self._lock:
            self._routes[route.name] = route

    def remove_route(self, name: str) -> bool:
        with self._lock:
            return self._routes.pop(name, None) is not None

    def route(self, msg: Message) -> list[str]:
        with self._lock:
            rules = sorted(self._routes.values(), key=lambda r: r.priority)
        destinations = [r.destination for r in rules if r.matches(msg)]
        if not destinations and self._default:
            destinations.append(self._default)
        return destinations

    def route_first(self, msg: Message) -> str:
        destinations = self.route(msg)
        if not destinations:
            raise NoRouteError(msg.envelope.destination or "?")
        return destinations[0]

    def has_route(self, msg: Message) -> bool:
        return bool(self.route(msg))

    def clear(self) -> None:
        with self._lock:
            self._routes.clear()
