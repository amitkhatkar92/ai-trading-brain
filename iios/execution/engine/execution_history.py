"""iios/execution/engine/execution_history.py
==================================================
ExecutionHistory — append-only, thread-safe per-execution state log.
ExecutionArchive  — searchable archive of completed execution records.

C6 Execution Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

from .execution_state import EngineExecutionState


@dataclass(frozen=True)
class ExecutionHistoryEntry:
    """
    Immutable record of one engine state transition.

    Attributes
    ----------
    entry_id      : Unique entry identifier.
    execution_id  : Owning execution session.
    from_state    : State before the transition.
    to_state      : State after the transition.
    reason        : Human-readable reason for the transition.
    actor         : System or user that triggered the transition.
    occurred_at   : Unix timestamp.
    metadata      : Arbitrary extra data.
    """
    entry_id:     str                = field(default_factory=lambda: str(uuid.uuid4()))
    execution_id: str                = ""
    from_state:   EngineExecutionState = EngineExecutionState.IDLE
    to_state:     EngineExecutionState = EngineExecutionState.VALIDATING
    reason:       str                = ""
    actor:        str                = ""
    occurred_at:  float              = field(default_factory=time.time)
    metadata:     dict[str, Any]     = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id":     self.entry_id,
            "execution_id": self.execution_id,
            "from_state":   self.from_state.value,
            "to_state":     self.to_state.value,
            "reason":       self.reason,
            "actor":        self.actor,
            "occurred_at":  self.occurred_at,
        }

    def __repr__(self) -> str:
        return (
            f"ExecutionHistoryEntry("
            f"{self.from_state.value} → {self.to_state.value}, "
            f"actor={self.actor!r})"
        )


class ExecutionHistory:
    """
    Append-only, thread-safe state transition log for one execution.

    Parameters
    ----------
    execution_id : Owning execution session.
    max_entries  : Ring-buffer size.  Oldest entries are evicted when full.
    """

    def __init__(self, execution_id: str, max_entries: int = 1_000) -> None:
        if not execution_id:
            raise ValueError("execution_id must not be empty")
        self._execution_id = execution_id
        self._entries: deque[ExecutionHistoryEntry] = deque(maxlen=max(1, max_entries))
        self._total_recorded: int = 0
        self._lock = threading.Lock()

    # ── Mutation ──────────────────────────────────────────────────────────────

    def record(self, entry: ExecutionHistoryEntry) -> None:
        """
        Append *entry* to the history.

        Raises
        ------
        ValueError
            If entry.execution_id does not match this history's execution_id.
        """
        if entry.execution_id != self._execution_id:
            raise ValueError(
                f"entry.execution_id {entry.execution_id!r} does not match "
                f"history execution_id {self._execution_id!r}"
            )
        with self._lock:
            self._entries.append(entry)
            self._total_recorded += 1

    # ── Queries ───────────────────────────────────────────────────────────────

    def entries(self) -> tuple[ExecutionHistoryEntry, ...]:
        """Return all retained entries as an immutable tuple."""
        with self._lock:
            return tuple(self._entries)

    def first(self) -> Optional[ExecutionHistoryEntry]:
        """Oldest retained entry, or None if empty."""
        with self._lock:
            return self._entries[0] if self._entries else None

    def last(self) -> Optional[ExecutionHistoryEntry]:
        """Most recent entry, or None if empty."""
        with self._lock:
            return self._entries[-1] if self._entries else None

    def count(self) -> int:
        """Number of entries currently retained (≤ max_entries)."""
        with self._lock:
            return len(self._entries)

    def states_visited(self) -> frozenset[EngineExecutionState]:
        """Set of all to_states recorded."""
        with self._lock:
            return frozenset(e.to_state for e in self._entries)

    @property
    def total_recorded(self) -> int:
        """Total entries ever appended, including evicted ones."""
        with self._lock:
            return self._total_recorded

    @property
    def evicted_count(self) -> int:
        """Number of entries that were evicted due to ring-buffer overflow."""
        with self._lock:
            return max(0, self._total_recorded - len(self._entries))

    @property
    def execution_id(self) -> str:
        return self._execution_id

    # ── Protocol methods ──────────────────────────────────────────────────────

    def __iter__(self) -> Iterator[ExecutionHistoryEntry]:
        with self._lock:
            return iter(list(self._entries))

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)


def make_history_entry(
    execution_id: str,
    from_state:   EngineExecutionState,
    to_state:     EngineExecutionState,
    reason:       str  = "",
    actor:        str  = "",
    metadata:     Optional[dict[str, Any]] = None,
    occurred_at:  Optional[float]          = None,
) -> ExecutionHistoryEntry:
    """Create an ExecutionHistoryEntry with a generated entry_id."""
    return ExecutionHistoryEntry(
        entry_id     = str(uuid.uuid4()),
        execution_id = execution_id,
        from_state   = from_state,
        to_state     = to_state,
        reason       = reason,
        actor        = actor,
        occurred_at  = occurred_at if occurred_at is not None else time.time(),
        metadata     = dict(metadata) if metadata else {},
    )
