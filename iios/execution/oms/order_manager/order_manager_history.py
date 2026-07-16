"""iios/execution/oms/order_manager/order_manager_history.py
==================================================
OrderManagerHistory — append-only immutable-entry history
of OMS state transitions for a single managed order.

C6 Execution Intelligence — Phase 2, Module 1
"""
from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

from iios.execution.oms.order_manager.constants import ManagerOrderState


@dataclass(frozen=True)
class ManagerTransition:
    """Immutable record of one OMS state transition."""

    transition_id: str              = field(default_factory=lambda: str(uuid.uuid4()))
    order_id:      str              = ""
    from_state:    ManagerOrderState = ManagerOrderState.INITIALIZED
    to_state:      ManagerOrderState = ManagerOrderState.READY
    occurred_at:   float            = field(default_factory=time.time)
    actor:         str              = "iios:system"
    reason:        str              = ""
    metadata:      dict[str, Any]   = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "order_id":      self.order_id,
            "from_state":    self.from_state.value,
            "to_state":      self.to_state.value,
            "occurred_at":   self.occurred_at,
            "actor":         self.actor,
            "reason":        self.reason,
        }

    def __repr__(self) -> str:
        return (
            f"ManagerTransition("
            f"{self.from_state.value} → {self.to_state.value}, "
            f"order={self.order_id!r})"
        )


class OrderManagerHistory:
    """
    Append-only, thread-safe history of OMS state transitions
    for a single managed order.
    """

    def __init__(
        self,
        order_id:    str,
        max_entries: int = 500,
    ) -> None:
        self._order_id   = order_id
        self._max_entries = max_entries
        self._entries:   deque[ManagerTransition] = deque(maxlen=max_entries)
        self._lock       = threading.Lock()
        self._total:     int = 0
        self._evicted:   int = 0

    def record(self, transition: ManagerTransition) -> None:
        with self._lock:
            if len(self._entries) == self._max_entries:
                self._evicted += 1
            self._entries.append(transition)
            self._total += 1

    def entries(self) -> list[ManagerTransition]:
        with self._lock:
            return list(self._entries)

    def first(self) -> Optional[ManagerTransition]:
        with self._lock:
            return self._entries[0] if self._entries else None

    def last(self) -> Optional[ManagerTransition]:
        with self._lock:
            return self._entries[-1] if self._entries else None

    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    def states_visited(self) -> list[ManagerOrderState]:
        with self._lock:
            seen: list[ManagerOrderState] = []
            for t in self._entries:
                if not seen or seen[-1] != t.to_state:
                    seen.append(t.to_state)
        return seen

    @property
    def order_id(self) -> str:
        return self._order_id

    @property
    def total_recorded(self) -> int:
        return self._total

    @property
    def evicted_count(self) -> int:
        return self._evicted

    def __iter__(self) -> Iterator[ManagerTransition]:
        with self._lock:
            entries = list(self._entries)
        return iter(entries)

    def __len__(self) -> int:
        return self.count()


def make_transition(
    order_id:   str,
    from_state: ManagerOrderState,
    to_state:   ManagerOrderState,
    *,
    actor:  str = "iios:system",
    reason: str = "",
    occurred_at: float = 0.0,
) -> ManagerTransition:
    return ManagerTransition(
        order_id   = order_id,
        from_state = from_state,
        to_state   = to_state,
        occurred_at = occurred_at or time.time(),
        actor      = actor,
        reason     = reason,
    )
