"""iios/execution/core/execution_history.py"""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from iios.execution.core.execution_result import ExecutionResult


@dataclass
class ExecutionHistoryRecord:
    """Thin wrapper stored in the history ring buffer."""

    execution_id: str
    result:       ExecutionResult
    index:        int = 0          # monotonic sequence number

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "index":        self.index,
            "result":       self.result.to_dict(),
        }


class ExecutionHistory:
    """
    Thread-safe ring buffer storing the most recent N execution results.

    Supports per-execution_id lookup as well as ordered iteration.
    """

    def __init__(self, max_size: int = 50_000) -> None:
        self._max_size   = max_size
        self._lock       = threading.RLock()
        self._ring:  deque[ExecutionHistoryRecord] = deque(maxlen=max_size)
        self._index: dict[str, list[ExecutionHistoryRecord]] = {}
        self._seq        = 0

    # ── Mutation ───────────────────────────────────────────────────────────────

    def add(self, execution_id: str, result: ExecutionResult) -> None:
        with self._lock:
            self._seq += 1
            record = ExecutionHistoryRecord(
                execution_id=execution_id,
                result=result,
                index=self._seq,
            )
            # If ring is full, evict oldest and remove from index.
            if len(self._ring) == self._max_size:
                evicted = self._ring[0]
                eids = self._index.get(evicted.execution_id, [])
                if evicted in eids:
                    eids.remove(evicted)

            self._ring.append(record)
            self._index.setdefault(execution_id, []).append(record)

    # ── Query ─────────────────────────────────────────────────────────────────

    def get_latest(self, execution_id: str) -> ExecutionResult | None:
        with self._lock:
            records = self._index.get(execution_id)
            if not records:
                return None
            return records[-1].result

    def get_all(self, execution_id: str) -> list[ExecutionResult]:
        with self._lock:
            return [r.result for r in self._index.get(execution_id, [])]

    def get_recent(self, n: int) -> list[ExecutionResult]:
        with self._lock:
            tail = list(self._ring)[-n:]
            return [r.result for r in reversed(tail)]

    def count(self) -> int:
        with self._lock:
            return len(self._ring)

    def execution_count(self, execution_id: str) -> int:
        with self._lock:
            return len(self._index.get(execution_id, []))

    def clear(self) -> None:
        with self._lock:
            self._ring.clear()
            self._index.clear()
            self._seq = 0

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "max_size":        self._max_size,
                "count":           len(self._ring),
                "unique_executions": len(self._index),
            }
