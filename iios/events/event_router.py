"""
iios/events/event_router.py
================================
Content-based event router — routes events to named channels/topics based on
rules (predicate functions or pattern matching on event_type).
"""

from __future__ import annotations

import fnmatch
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .event_metadata import Event
from .event_exceptions import NoRouteError, RouterError
from .event_constants import WILDCARD

__all__ = ["RouteRule", "EventRouter"]


@dataclass
class RouteRule:
    """A single routing rule."""
    name: str
    pattern: str              # event_type pattern; supports fnmatch wildcards
    destination: str          # channel/topic name
    predicate: Optional[Callable[[Event], bool]] = None
    priority: int = 100
    transform: Optional[Callable[[Event], Event]] = None  # optional payload transform

    def matches(self, event: Event) -> bool:
        if self.pattern != WILDCARD and not fnmatch.fnmatch(event.event_type, self.pattern):
            return False
        if self.predicate and not self.predicate(event):
            return False
        return True


class EventRouter:
    """Routes events to destination channels based on registered rules.

    Rules are evaluated in priority order (lowest int first).
    Multiple rules can match the same event — all matching destinations are returned.

    Usage::

        router = EventRouter()
        router.add_rule(RouteRule(
            name="high_priority_trades",
            pattern="trade.*",
            destination="priority_queue",
            predicate=lambda e: e.payload.get("qty", 0) > 1000,
            priority=10,
        ))
        router.add_rule(RouteRule(name="all_trades", pattern="trade.*", destination="main_queue"))

        destinations = router.route(event)  # returns list of destination names
    """

    def __init__(self, default_destination: Optional[str] = None) -> None:
        self._rules: dict[str, RouteRule] = {}
        self._default = default_destination
        self._lock = threading.RLock()

    def add_rule(self, rule: RouteRule, allow_override: bool = True) -> None:
        with self._lock:
            if rule.name in self._rules and not allow_override:
                raise RouterError(f"Route rule '{rule.name}' already exists")
            self._rules[rule.name] = rule

    def remove_rule(self, name: str) -> bool:
        with self._lock:
            return self._rules.pop(name, None) is not None

    def route(self, event: Event) -> list[str]:
        """Return all destination names that match *event*."""
        with self._lock:
            rules = sorted(self._rules.values(), key=lambda r: r.priority)

        destinations = []
        for rule in rules:
            if rule.matches(event):
                destinations.append(rule.destination)

        if not destinations and self._default:
            destinations.append(self._default)

        return destinations

    def route_first(self, event: Event) -> str:
        """Return the first matching destination or raise NoRouteError."""
        destinations = self.route(event)
        if not destinations:
            raise NoRouteError(event.event_type)
        return destinations[0]

    def transform(self, rule_name: str, event: Event) -> Event:
        """Apply the transform function of a rule to *event*."""
        with self._lock:
            rule = self._rules.get(rule_name)
        if rule is None or rule.transform is None:
            return event
        return rule.transform(event)

    def has_route(self, event: Event) -> bool:
        return bool(self.route(event))

    def rules(self) -> list[RouteRule]:
        with self._lock:
            return sorted(self._rules.values(), key=lambda r: r.priority)

    def clear(self) -> None:
        with self._lock:
            self._rules.clear()
