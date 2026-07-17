"""iios/execution/risk/snapshot/execution_risk_snapshot_history.py
==================================================
SnapshotHistory — per risk_id ordered version list.

Thread-safe.  All snapshots for a given risk_id are stored in insertion
order.  The oldest version is index 0; the most recent is index -1.

C6 Execution Intelligence — Phase 4, Module 5
"""
from __future__ import annotations

import threading
from collections import defaultdict
from typing import Dict, List, Optional

from .execution_risk_snapshot import ExecutionRiskSnapshot


class SnapshotHistory:
    """
    In-memory, thread-safe version history indexed by risk_id.

    Each ``risk_id`` can have multiple snapshot versions (e.g. when a
    snapshot is superseded after an override or a re-evaluation).
    """

    def __init__(self, max_versions_per_risk: int = 100) -> None:
        self._max = max_versions_per_risk
        self._lock = threading.RLock()
        # risk_id → List[ExecutionRiskSnapshot] (insertion order)
        self._history: Dict[str, List[ExecutionRiskSnapshot]] = defaultdict(list)

    # ── Write ─────────────────────────────────────────────────────────────────

    def append(self, snapshot: ExecutionRiskSnapshot) -> None:
        with self._lock:
            bucket = self._history[snapshot.risk_id]
            bucket.append(snapshot)
            # Enforce per-risk limit — evict oldest
            if len(bucket) > self._max:
                del bucket[0]

    # ── Read ──────────────────────────────────────────────────────────────────

    def versions(self, risk_id: str) -> List[ExecutionRiskSnapshot]:
        """Return all versions for *risk_id* in insertion (oldest-first) order."""
        with self._lock:
            return list(self._history.get(risk_id, []))

    def latest(self, risk_id: str) -> Optional[ExecutionRiskSnapshot]:
        """Return the most recent snapshot for *risk_id*, or None."""
        with self._lock:
            bucket = self._history.get(risk_id)
            return bucket[-1] if bucket else None

    def oldest(self, risk_id: str) -> Optional[ExecutionRiskSnapshot]:
        """Return the oldest snapshot for *risk_id*, or None."""
        with self._lock:
            bucket = self._history.get(risk_id)
            return bucket[0] if bucket else None

    def count_versions(self, risk_id: str) -> int:
        with self._lock:
            return len(self._history.get(risk_id, []))

    def all(self) -> List[ExecutionRiskSnapshot]:
        """Return all snapshots across all risk_ids (oldest-first within each)."""
        with self._lock:
            result: List[ExecutionRiskSnapshot] = []
            for bucket in self._history.values():
                result.extend(bucket)
            return result

    @property
    def total(self) -> int:
        """Total number of snapshots stored (sum across all risk_ids)."""
        with self._lock:
            return sum(len(v) for v in self._history.values())

    @property
    def tracked_risk_ids(self) -> List[str]:
        with self._lock:
            return list(self._history.keys())

    def clear(self) -> None:
        with self._lock:
            self._history.clear()
