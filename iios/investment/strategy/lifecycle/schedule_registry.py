"""iios/investment/strategy/lifecycle/schedule_registry.py
Registry of per-strategy schedule configurations.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Dict, List, Optional


class ScheduleType(str, Enum):
    """How a strategy's execution is triggered."""

    IMMEDIATE   = "immediate"    # run once immediately
    PERIODIC    = "periodic"     # run every N seconds
    TIME_BASED  = "time_based"   # run at specific wall-clock UTC times (HH:MM)
    EVENT       = "event"        # run when a named event fires
    CONDITIONAL = "conditional"  # run when a predicate returns True


@dataclass
class ScheduleEntry:
    """
    Scheduling configuration for a single strategy.

    Field usage by schedule_type:
      PERIODIC    → interval_seconds
      TIME_BASED  → trigger_times  (list of "HH:MM" UTC strings)
      EVENT       → trigger_event  (event name)
      CONDITIONAL → condition_fn   (callable() → bool)
      IMMEDIATE   → no extra fields; fired once by the caller
    """

    strategy_id: str
    schedule_type: ScheduleType
    priority: int = 20   # default SchedulePriority.NORMAL

    # PERIODIC
    interval_seconds: float = 0.0

    # TIME_BASED
    trigger_times: List[str] = field(default_factory=list)

    # EVENT
    trigger_event: str = ""

    # CONDITIONAL
    condition_fn: Optional[Callable[[], bool]] = field(default=None, repr=False)

    # Housekeeping
    entry_id: str = field(
        default_factory=lambda: f"sch-{uuid.uuid4().hex[:8]}"
    )
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_triggered_at: Optional[datetime] = None
    enabled: bool = True


class ScheduleRegistry:
    """
    Thread-safe registry of ScheduleEntry objects.

    One strategy may have at most one schedule entry; re-registration
    with replace=True replaces the existing entry.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._entries: Dict[str, ScheduleEntry] = {}  # strategy_id → entry

    # ── Mutation ──────────────────────────────────────────────────────────────

    def register(self, entry: ScheduleEntry, replace: bool = False) -> None:
        with self._lock:
            if entry.strategy_id in self._entries and not replace:
                raise ValueError(
                    f"Schedule already registered for strategy "
                    f"{entry.strategy_id!r}. Use replace=True to overwrite."
                )
            self._entries[entry.strategy_id] = entry

    def unregister(self, strategy_id: str) -> bool:
        with self._lock:
            return self._entries.pop(strategy_id, None) is not None

    def enable(self, strategy_id: str) -> None:
        with self._lock:
            entry = self._entries.get(strategy_id)
            if entry:
                entry.enabled = True

    def disable(self, strategy_id: str) -> None:
        with self._lock:
            entry = self._entries.get(strategy_id)
            if entry:
                entry.enabled = False

    def update_last_triggered(self, strategy_id: str) -> None:
        with self._lock:
            entry = self._entries.get(strategy_id)
            if entry:
                entry.last_triggered_at = datetime.now(timezone.utc)

    # ── Query ─────────────────────────────────────────────────────────────────

    def get(self, strategy_id: str) -> Optional[ScheduleEntry]:
        with self._lock:
            return self._entries.get(strategy_id)

    def all_entries(self) -> List[ScheduleEntry]:
        with self._lock:
            return list(self._entries.values())

    def enabled_entries(self) -> List[ScheduleEntry]:
        with self._lock:
            return [e for e in self._entries.values() if e.enabled]

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)
