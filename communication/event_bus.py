"""
Event Bus — The Central Nervous System of the Agent Network
============================================================

Architecture:
  Publisher ──►  EventBus.publish(event)
                      │
                      ▼
             ┌────────────────┐
             │  Subscription  │  matches EventType (or wildcard "*")
             │  Registry      │
             └────────────────┘
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
     Subscriber1  Subscriber2  Subscriber3
     (RiskMgr)   (Monitor)    (LearningEng)

Features:
  • Type-safe subscriptions via EventType enum
  • Wildcard subscription ("*") — receives ALL events
  • Priority-ordered delivery: CRITICAL > HIGH > NORMAL
  • Dead-letter queue: undelivered events are captured for debugging
  • Thread-safe: can be used from scheduler thread + main thread
  • Sync delivery by default; async-compatible via asyncio extension
  • Per-event middleware hooks (logging, metrics, replay)

Global singleton:
  Use `get_bus()` anywhere in the project to get the shared bus.
  Use `EventBus()` to create an isolated bus (e.g. for testing).
"""

from __future__ import annotations

import threading
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from .events import Event, EventType, SystemEvent
from utils import get_logger

log = get_logger(__name__)

# Subscriber callable type
Handler = Callable[[Event], None]

# ── Subscription record ───────────────────────────────────────────────────────

class Subscription:
    """Represents one agent's subscription to one event type."""
    __slots__ = ("sub_id", "event_type", "handler", "agent_name",
                 "priority", "active")

    def __init__(self, event_type: str, handler: Handler,
                 agent_name: str, priority: int):
        self.sub_id     = str(uuid.uuid4())[:8]
        self.event_type = event_type   # EventType value or "*"
        self.handler    = handler
        self.agent_name = agent_name
        self.priority   = priority     # Lower number = delivered first
        self.active     = True

    def __repr__(self) -> str:
        return (f"<Subscription sub_id={self.sub_id} "
                f"agent={self.agent_name} event={self.event_type}>")


# ── Event Bus ─────────────────────────────────────────────────────────────────

class EventBus:
    """
    Thread-safe publish/subscribe event bus.

    Usage:
        bus = get_bus()

        # Subscribe
        bus.subscribe(EventType.TRADE_APPROVED, my_handler, agent_name="ExecutionEngine")

        # Publish
        bus.publish(DecisionEvent(
            event_type=EventType.TRADE_APPROVED,
            source_agent="DecisionEngine",
            symbol="RELIANCE",
            approved=True,
        ))
    """

    def __init__(self, name: str = "main"):
        self._name          = name
        self._lock          = threading.Lock()
        # event_type_value → List[Subscription]  (sorted by priority)
        self._subscriptions: Dict[str, List[Subscription]] = defaultdict(list)
        self._wildcard_subs: List[Subscription] = []
        self._dead_letters:  List[Event] = []          # Events with 0 handlers
        self._event_log:     List[Event] = []           # Full audit trail
        self._max_log_size  = 5_000
        self._published     = 0
        self._delivered     = 0
        self._middleware: List[Callable[[Event], None]] = []
        log.info("[EventBus:%s] Initialised.", self._name)

    # ─────────────────────────────────────────────────────────────────
    # SUBSCRIBE
    # ─────────────────────────────────────────────────────────────────

    def subscribe(self, event_type: EventType | str, handler: Handler,
                  agent_name: str = "unknown",
                  priority: int = 50) -> str:
        """
        Register a handler for a specific EventType.
        Use event_type="*" to receive all events (monitoring/logging agents).

        Args:
            event_type:  The EventType to listen for, or "*" for all.
            handler:     Callable(Event) → None
            agent_name:  Human-readable name for debugging.
            priority:    Delivery order — lower = earlier (0–100).

        Returns:
            sub_id — use with unsubscribe() to remove the subscription.
        """
        key = event_type if isinstance(event_type, str) else event_type.value
        sub = Subscription(key, handler, agent_name, priority)

        with self._lock:
            if key == "*":
                self._wildcard_subs.append(sub)
                self._wildcard_subs.sort(key=lambda s: s.priority)
            else:
                self._subscriptions[key].append(sub)
                self._subscriptions[key].sort(key=lambda s: s.priority)

        log.debug("[EventBus:%s] %s subscribed to '%s' (sub_id=%s)",
                  self._name, agent_name, key, sub.sub_id)
        return sub.sub_id

    def unsubscribe(self, sub_id: str) -> bool:
        """Deactivate a subscription by its sub_id."""
        with self._lock:
            for subs in self._subscriptions.values():
                for sub in subs:
                    if sub.sub_id == sub_id:
                        sub.active = False
                        log.debug("[EventBus:%s] Unsubscribed %s", self._name, sub_id)
                        return True
            for sub in self._wildcard_subs:
                if sub.sub_id == sub_id:
                    sub.active = False
                    return True
        return False

    # ─────────────────────────────────────────────────────────────────
    # PUBLISH
    # ─────────────────────────────────────────────────────────────────

    def publish(self, event: Event) -> int:
        """
        Publish an event to all matching subscribers.

        Returns the number of handlers that received the event.
        """
        if not event.correlation_id:
            event.correlation_id = str(uuid.uuid4())[:12]

        # Run middleware (logging, metrics, etc.)
        for mw in self._middleware:
            try:
                mw(event)
            except Exception:
                pass

        self._log_event(event)
        self._published += 1

        key = event.event_type.value if isinstance(event.event_type, EventType) else str(event.event_type)

        with self._lock:
            specific = [s for s in self._subscriptions.get(key, []) if s.active]
            wildcard = [s for s in self._wildcard_subs if s.active]
            all_subs = specific + wildcard

        if not all_subs:
            self._dead_letters.append(event)
            log.debug("[EventBus:%s] Dead letter: %s (no subscribers)", self._name, event)
            return 0

        delivered = 0
        for sub in sorted(all_subs, key=lambda s: s.priority):
            try:
                sub.handler(event)
                delivered += 1
            except Exception as exc:
                log.error("[EventBus:%s] Handler error in %s for %s: %s",
                          self._name, sub.agent_name, key, exc)

        self._delivered += delivered
        return delivered

    def publish_system(self, message: str, source: str = "system",
                       severity: str = "INFO") -> int:
        """Convenience method for system-level events."""
        evt = SystemEvent(
            event_type  = EventType.AGENT_ERROR if severity == "CRITICAL" else EventType.SYSTEM_STARTUP,
            source_agent= source,
            message     = message,
            severity    = severity,
        )
        return self.publish(evt)

    # ─────────────────────────────────────────────────────────────────
    # MIDDLEWARE
    # ─────────────────────────────────────────────────────────────────

    def add_middleware(self, fn: Callable[[Event], None]):
        """
        Add a middleware function called on every published event.
        Use for: structured logging, metrics, event replay, tracing.
        """
        self._middleware.append(fn)

    # ─────────────────────────────────────────────────────────────────
    # DIAGNOSTICS
    # ─────────────────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            n_subs = sum(len(v) for v in self._subscriptions.values())
            n_wild = len(self._wildcard_subs)
        return {
            "bus_name":        self._name,
            "published":       self._published,
            "delivered":       self._delivered,
            "subscriptions":   n_subs,
            "wildcard_subs":   n_wild,
            "dead_letters":    len(self._dead_letters),
            "event_log_size":  len(self._event_log),
        }

    def get_event_log(self, event_type: Optional[EventType] = None,
                      limit: int = 100) -> List[Event]:
        """Return recent events, optionally filtered by type."""
        log_ = self._event_log[-limit:]
        if event_type:
            key = event_type.value
            log_ = [e for e in log_ if
                    (e.event_type.value if isinstance(e.event_type, EventType) else e.event_type) == key]
        return log_

    def get_dead_letters(self) -> List[Event]:
        return list(self._dead_letters)

    def clear_dead_letters(self):
        self._dead_letters.clear()

    def print_stats(self):
        s = self.stats()
        log.info("[EventBus:%s] Published=%d Delivered=%d Subs=%d Wildcards=%d "
                 "DeadLetters=%d",
                 s["bus_name"], s["published"], s["delivered"],
                 s["subscriptions"], s["wildcard_subs"], s["dead_letters"])

    # ─────────────────────────────────────────────────────────────────
    # PRIVATE
    # ─────────────────────────────────────────────────────────────────

    def _log_event(self, event: Event):
        self._event_log.append(event)
        if len(self._event_log) > self._max_log_size:
            self._event_log = self._event_log[-self._max_log_size:]


# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL SINGLETON
# ─────────────────────────────────────────────────────────────────────────────

_global_bus: Optional[EventBus] = None
_bus_lock    = threading.Lock()


def get_bus() -> EventBus:
    """
    Return the global shared EventBus (creates it on first call).
    All agents in the system share this single bus.
    """
    global _global_bus
    if _global_bus is None:
        with _bus_lock:
            if _global_bus is None:
                _global_bus = EventBus(name="global")
                _attach_default_middleware(_global_bus)
    return _global_bus


def _attach_default_middleware(bus: EventBus):
    """Attach built-in middleware: structured event logging."""
    def _log_mw(event: Event):
        lvl = ("WARNING" if "reject" in str(event.event_type).lower()
               or "halt"  in str(event.event_type).lower()
               else "DEBUG")
        if lvl == "WARNING":
            log.warning("📨 %s", event)
        else:
            log.debug("📨 %s", event)

    bus.add_middleware(_log_mw)
