"""
iios/events/event_manager.py
==============================================
High-level façade for the IIOS Event & Messaging Framework.
Combines EventBus, Registry, Router, Factory, and Context.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Optional

from .event_bus import EventBus, get_event_bus, reset_event_bus
from .event_factory import EventFactory
from .event_metadata import Event
from .event_priority import EventPriority
from .event_registry import EventRegistry, EventTypeDescriptor, get_event_registry, reset_event_registry
from .event_router import EventRouter, RouteRule
from .event_context import EventContext, get_event_context, event_scope
from .event_constants import WILDCARD

__all__ = ["EventManager", "get_event_manager", "reset_event_manager"]

_LOG = logging.getLogger("iios.events.manager")
_mgr_lock = threading.Lock()
_manager: Optional["EventManager"] = None


class EventManager:
    """Single entry point for all event operations in IIOS.

    Usage::

        mgr = get_event_manager()

        # Register an event type
        mgr.register_event("trade.executed",
                           description="Trade was executed",
                           owner="execution_engine")

        # Subscribe
        sub_id = mgr.on("trade.executed", handler)

        # Publish
        mgr.emit("trade.executed", {"symbol": "RELIANCE", "qty": 100})

        # Wildcard subscriptions
        mgr.on("trade.*", handle_all_trade_events)

        # Cleanup
        mgr.off(sub_id)
    """

    def __init__(
        self,
        bus: Optional[EventBus] = None,
        registry: Optional[EventRegistry] = None,
        default_source: str = "iios",
    ) -> None:
        self._bus = bus or get_event_bus()
        self._registry = registry or get_event_registry()
        self._router = EventRouter()
        self._factory = EventFactory(source=default_source)
        self._context = get_event_context()
        self._source = default_source

    # ── Register event types ──────────────────────────────────────────────────

    def register_event(
        self,
        event_type: str,
        description: str = "",
        owner: str = "",
        schema: Optional[dict[str, Any]] = None,
        tags: Optional[list[str]] = None,
    ) -> None:
        self._registry.register(EventTypeDescriptor(
            event_type=event_type,
            description=description,
            owner=owner,
            schema=schema or {},
            tags=tags or [],
        ), allow_override=True)

    # ── Subscribe ─────────────────────────────────────────────────────────────

    def on(
        self,
        event_type: str,
        handler: Callable[[Event], None],
        *,
        priority: EventPriority = EventPriority.NORMAL,
        predicate: Optional[Callable[[Event], bool]] = None,
        once: bool = False,
        name: str = "",
    ) -> str:
        if once:
            return self._bus.subscribe_once(event_type, handler, priority=priority, name=name)
        return self._bus.subscribe(
            event_type, handler, priority=priority, predicate=predicate, name=name
        )

    def on_all(self, handler: Callable[[Event], None], **kw: Any) -> str:
        """Subscribe to all events (wildcard)."""
        return self.on(WILDCARD, handler, **kw)

    def off(self, sub_id: str) -> bool:
        return self._bus.unsubscribe(sub_id)

    # ── Publish ───────────────────────────────────────────────────────────────

    def emit(
        self,
        event_type: str,
        payload: Optional[dict[str, Any]] = None,
        *,
        priority: EventPriority = EventPriority.NORMAL,
        sticky: bool = False,
        tags: Optional[dict[str, str]] = None,
        correlation_id: Optional[str] = None,
        ttl: Optional[float] = None,
        source: Optional[str] = None,
    ) -> int:
        """Create and publish an event. Returns the number of successful deliveries."""
        event = self._factory.create(
            event_type,
            payload,
            priority=priority,
            sticky=sticky,
            tags=tags,
            correlation_id=correlation_id,
            ttl=ttl,
            source=source or self._source,
        )
        result = self._bus.publish(event)
        return result.succeeded

    def emit_event(self, event: Event) -> int:
        result = self._bus.publish(event)
        return result.succeeded

    def emit_delayed(self, event_type: str, delay: float, payload: Optional[dict[str, Any]] = None) -> str:
        event = self._factory.delayed(event_type, delay, payload)
        return self._bus.publish_delayed(event, delay=0.0)  # delay already in scheduled_at

    def broadcast(self, event_type: str, payload: Optional[dict[str, Any]] = None) -> int:
        event = self._factory.create(event_type, payload)
        return self._bus.broadcast(event)

    # ── Routing ───────────────────────────────────────────────────────────────

    def add_route(self, rule: RouteRule) -> None:
        self._router.add_rule(rule)

    def route(self, event: Event) -> list[str]:
        return self._router.route(event)

    # ── Query ─────────────────────────────────────────────────────────────────

    def history(self, event_type: Optional[str] = None, limit: int = 100) -> list[Event]:
        return self._bus.history(event_type=event_type, limit=limit)

    def stats(self) -> dict[str, Any]:
        bus_stats = self._bus.stats()
        ctx_stats = self._context.stats()
        return {
            "published": bus_stats.published,
            "consumed": bus_stats.consumed,
            "failed": bus_stats.failed,
            "dead_lettered": bus_stats.dead_lettered,
            "sticky_hits": bus_stats.sticky_hits,
            "scheduled_fired": bus_stats.scheduled_fired,
            "registered_types": len(self._registry),
            **ctx_stats,
        }

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def bus(self) -> EventBus:
        return self._bus

    @property
    def registry(self) -> EventRegistry:
        return self._registry

    @property
    def router(self) -> EventRouter:
        return self._router

    @property
    def factory(self) -> EventFactory:
        return self._factory


def get_event_manager() -> EventManager:
    global _manager
    with _mgr_lock:
        if _manager is None:
            _manager = EventManager()
        return _manager


def reset_event_manager() -> None:
    global _manager
    with _mgr_lock:
        if _manager is not None:
            _manager.bus.stop()
        _manager = None
    reset_event_bus()
    reset_event_registry()
