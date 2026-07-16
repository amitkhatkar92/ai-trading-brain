"""iios/execution/context/execution_context_history.py
==================================================
ExecutionContextHistory — append-only, immutable-entry history
of ExecutionContext revisions for a single execution.

C6 Execution Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

from iios.execution.context.constants import ContextStatus
from iios.execution.context.execution_context import ExecutionContext


@dataclass(frozen=True)
class ContextRevision:
    """
    Immutable record of one revision in an execution context's history.
    """
    revision_id:  str           = field(default_factory=lambda: str(uuid.uuid4()))
    context_id:   str           = ""
    execution_id: str           = ""
    revision:     int           = 0
    status:       ContextStatus = ContextStatus.BUILDING
    recorded_at:  float         = field(default_factory=time.time)
    actor:        str           = "iios:system"
    reason:       str           = ""
    snapshot:     Optional[dict[str, Any]] = None   # minimal context snapshot

    def to_dict(self) -> dict[str, Any]:
        return {
            "revision_id":  self.revision_id,
            "context_id":   self.context_id,
            "execution_id": self.execution_id,
            "revision":     self.revision,
            "status":       self.status.value,
            "recorded_at":  self.recorded_at,
            "actor":        self.actor,
            "reason":       self.reason,
        }

    def __repr__(self) -> str:
        return (
            f"ContextRevision("
            f"rev={self.revision}, "
            f"status={self.status.value}, "
            f"context={self.context_id[:8]})"
        )


class ExecutionContextHistory:
    """
    Append-only, thread-safe history of ExecutionContext revisions.

    Maintains one history per execution_id.
    Oldest entries are evicted when max_entries is reached.
    """

    def __init__(
        self,
        execution_id: str,
        max_entries:  int = 100,
    ) -> None:
        self._execution_id = execution_id
        self._max_entries  = max_entries
        self._entries:     deque[ContextRevision] = deque(maxlen=max_entries)
        self._lock         = threading.Lock()
        self._total:       int = 0
        self._evicted:     int = 0

    # ── Append ────────────────────────────────────────────────────────────────

    def record(self, revision: ContextRevision) -> None:
        with self._lock:
            if len(self._entries) == self._max_entries:
                self._evicted += 1
            self._entries.append(revision)
            self._total += 1

    # ── Queries ───────────────────────────────────────────────────────────────

    def entries(self) -> list[ContextRevision]:
        with self._lock:
            return list(self._entries)

    def first(self) -> Optional[ContextRevision]:
        with self._lock:
            return self._entries[0] if self._entries else None

    def last(self) -> Optional[ContextRevision]:
        with self._lock:
            return self._entries[-1] if self._entries else None

    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    @property
    def execution_id(self) -> str:
        return self._execution_id

    @property
    def total_recorded(self) -> int:
        return self._total

    @property
    def evicted_count(self) -> int:
        return self._evicted

    def statuses(self) -> list[ContextStatus]:
        with self._lock:
            return [e.status for e in self._entries]

    # ── Comparison ────────────────────────────────────────────────────────────

    def compare(
        self,
        rev_a: int,
        rev_b: int,
    ) -> dict[str, Any]:
        """Return a simple comparison dict for two revision numbers."""
        with self._lock:
            entries_by_rev = {e.revision: e for e in self._entries}
        a = entries_by_rev.get(rev_a)
        b = entries_by_rev.get(rev_b)
        return {
            "revision_a": a.to_dict() if a else None,
            "revision_b": b.to_dict() if b else None,
            "status_changed": (
                a.status != b.status
                if (a is not None and b is not None) else None
            ),
        }

    # ── Iteration ─────────────────────────────────────────────────────────────

    def __iter__(self) -> Iterator[ContextRevision]:
        with self._lock:
            entries = list(self._entries)
        return iter(entries)

    def __len__(self) -> int:
        return self.count()


def make_revision(
    context:    ExecutionContext,
    revision:   int,
    *,
    actor:      str = "iios:system",
    reason:     str = "",
    include_snapshot: bool = False,
) -> ContextRevision:
    """Factory helper for ContextRevision."""
    return ContextRevision(
        context_id   = context.context_id,
        execution_id = context.execution_id,
        revision     = revision,
        status       = context.status,
        actor        = actor,
        reason       = reason,
        snapshot     = context.to_dict() if include_snapshot else None,
    )
