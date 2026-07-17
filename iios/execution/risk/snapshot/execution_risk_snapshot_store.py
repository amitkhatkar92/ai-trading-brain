"""iios/execution/risk/snapshot/execution_risk_snapshot_store.py
==================================================
SnapshotStore — thread-safe, multi-index primary store.

Provides O(1) access by snapshot_id and O(n) list access by each
indexed field.  The store is append-friendly; snapshots are immutable
but their status can be updated (produces a new frozen object).

Indices built on:
  snapshot_id (primary)
  risk_id, execution_id, order_id, position_id,
  portfolio_id, workflow_id, strategy_id

C6 Execution Intelligence — Phase 4, Module 5
"""
from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import replace
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_STORE_SIZE, SnapshotStatus
from .exceptions import DuplicateSnapshotError, SnapshotNotFoundError, SnapshotStoreError
from .execution_risk_snapshot import ExecutionRiskSnapshot


class SnapshotStore:
    """
    Thread-safe, multi-index snapshot store with capacity limiting.

    When the store is full, new puts are rejected with SnapshotStoreError.
    Use ``remove()`` or ``archive()`` to reclaim capacity.
    """

    def __init__(self, max_size: int = DEFAULT_MAX_STORE_SIZE) -> None:
        self._max_size = max_size
        self._lock     = threading.RLock()

        # Primary store
        self._store: Dict[str, ExecutionRiskSnapshot] = {}

        # Secondary indices: field_value → List[snapshot_id]
        self._by_risk_id:      Dict[str, List[str]] = defaultdict(list)
        self._by_execution_id: Dict[str, List[str]] = defaultdict(list)
        self._by_order_id:     Dict[str, List[str]] = defaultdict(list)
        self._by_position_id:  Dict[str, List[str]] = defaultdict(list)
        self._by_portfolio_id: Dict[str, List[str]] = defaultdict(list)
        self._by_workflow_id:  Dict[str, List[str]] = defaultdict(list)
        self._by_strategy_id:  Dict[str, List[str]] = defaultdict(list)

    # ── Write ─────────────────────────────────────────────────────────────────

    def put(self, snapshot: ExecutionRiskSnapshot) -> None:
        with self._lock:
            sid = snapshot.snapshot_id
            if sid in self._store:
                raise DuplicateSnapshotError(sid)
            if len(self._store) >= self._max_size:
                raise SnapshotStoreError(
                    f"Store capacity exceeded ({self._max_size}). "
                    f"Archive or remove snapshots before adding more."
                )
            self._store[sid] = snapshot
            self._index(snapshot)

    def _index(self, snapshot: ExecutionRiskSnapshot) -> None:
        sid = snapshot.snapshot_id
        if snapshot.risk_id:
            self._by_risk_id[snapshot.risk_id].append(sid)
        if snapshot.execution_id:
            self._by_execution_id[snapshot.execution_id].append(sid)
        if snapshot.order_id:
            self._by_order_id[snapshot.order_id].append(sid)
        if snapshot.position_id:
            self._by_position_id[snapshot.position_id].append(sid)
        if snapshot.portfolio_id:
            self._by_portfolio_id[snapshot.portfolio_id].append(sid)
        if snapshot.workflow_id:
            self._by_workflow_id[snapshot.workflow_id].append(sid)
        if snapshot.strategy_id:
            self._by_strategy_id[snapshot.strategy_id].append(sid)

    def _deindex(self, snapshot: ExecutionRiskSnapshot) -> None:
        sid = snapshot.snapshot_id

        def _remove(idx: Dict[str, List[str]], key: str) -> None:
            if key and key in idx:
                try:
                    idx[key].remove(sid)
                except ValueError:
                    pass

        _remove(self._by_risk_id,      snapshot.risk_id)
        _remove(self._by_execution_id, snapshot.execution_id)
        _remove(self._by_order_id,     snapshot.order_id)
        _remove(self._by_position_id,  snapshot.position_id)
        _remove(self._by_portfolio_id, snapshot.portfolio_id)
        _remove(self._by_workflow_id,  snapshot.workflow_id)
        _remove(self._by_strategy_id,  snapshot.strategy_id)

    # ── Read ──────────────────────────────────────────────────────────────────

    def get(self, snapshot_id: str) -> Optional[ExecutionRiskSnapshot]:
        with self._lock:
            return self._store.get(snapshot_id)

    def require(self, snapshot_id: str) -> ExecutionRiskSnapshot:
        with self._lock:
            s = self._store.get(snapshot_id)
            if s is None:
                raise SnapshotNotFoundError(snapshot_id)
            return s

    def contains(self, snapshot_id: str) -> bool:
        with self._lock:
            return snapshot_id in self._store

    def get_by_risk_id(self, risk_id: str) -> List[ExecutionRiskSnapshot]:
        return self._resolve(self._by_risk_id, risk_id)

    def get_by_execution_id(self, execution_id: str) -> List[ExecutionRiskSnapshot]:
        return self._resolve(self._by_execution_id, execution_id)

    def get_by_order_id(self, order_id: str) -> List[ExecutionRiskSnapshot]:
        return self._resolve(self._by_order_id, order_id)

    def get_by_position_id(self, position_id: str) -> List[ExecutionRiskSnapshot]:
        return self._resolve(self._by_position_id, position_id)

    def get_by_portfolio_id(self, portfolio_id: str) -> List[ExecutionRiskSnapshot]:
        return self._resolve(self._by_portfolio_id, portfolio_id)

    def get_by_workflow_id(self, workflow_id: str) -> List[ExecutionRiskSnapshot]:
        return self._resolve(self._by_workflow_id, workflow_id)

    def get_by_strategy_id(self, strategy_id: str) -> List[ExecutionRiskSnapshot]:
        return self._resolve(self._by_strategy_id, strategy_id)

    def _resolve(
        self,
        idx: Dict[str, List[str]],
        key: str,
    ) -> List[ExecutionRiskSnapshot]:
        with self._lock:
            ids = list(idx.get(key, []))
            result = []
            for sid in ids:
                s = self._store.get(sid)
                if s is not None:
                    result.append(s)
            return result

    def all(self) -> List[ExecutionRiskSnapshot]:
        with self._lock:
            return list(self._store.values())

    def latest(self, n: int = 10) -> List[ExecutionRiskSnapshot]:
        """Return the *n* most-recently inserted snapshots."""
        with self._lock:
            items = list(self._store.values())
            return sorted(items, key=lambda s: s.snapshot_timestamp, reverse=True)[:n]

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._store)

    # ── Mutate ────────────────────────────────────────────────────────────────

    def update_status(
        self, snapshot_id: str, new_status: SnapshotStatus
    ) -> ExecutionRiskSnapshot:
        """
        Replace the snapshot with a copy that has ``status=new_status``.

        Returns the updated snapshot.
        """
        with self._lock:
            existing = self.require(snapshot_id)
            updated  = replace(existing, status=new_status)
            self._store[snapshot_id] = updated
            return updated

    def remove(self, snapshot_id: str) -> None:
        with self._lock:
            s = self._store.pop(snapshot_id, None)
            if s is not None:
                self._deindex(s)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._by_risk_id.clear()
            self._by_execution_id.clear()
            self._by_order_id.clear()
            self._by_position_id.clear()
            self._by_portfolio_id.clear()
            self._by_workflow_id.clear()
            self._by_strategy_id.clear()
