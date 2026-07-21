"""
decision_snapshot_registry.py — iios.decision.snapshot
=======================================================
Thread-safe in-memory registry for DecisionSnapshot objects.

Provides:
- Snapshot storage by snapshot_id (primary key)
- Secondary indices for all query dimensions
- Version tracking per decision_id
- Capacity limits with DuplicateSnapshotError on collision

C9 Decision Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from collections import defaultdict
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_SNAPSHOTS, DEFAULT_MAX_VERSIONS
from .decision_snapshot import DecisionSnapshot
from .exceptions import DuplicateSnapshotError, SnapshotNotFoundError, SnapshotRegistryError


class DecisionSnapshotRegistry:
    """
    Thread-safe in-memory registry for :class:`DecisionSnapshot` objects.

    Parameters
    ----------
    max_snapshots :  Maximum snapshots in the registry.
    max_versions :   Maximum versions per decision_id.
    """

    def __init__(
        self,
        max_snapshots: int = DEFAULT_MAX_SNAPSHOTS,
        max_versions:  int = DEFAULT_MAX_VERSIONS,
    ) -> None:
        self._lock         = threading.RLock()
        self._by_id:       Dict[str, DecisionSnapshot] = {}
        self._max          = max_snapshots
        self._max_versions = max_versions

        # Secondary indices
        self._by_session:   Dict[str, List[str]] = defaultdict(list)   # session_id → [snapshot_ids]
        self._by_decision:  Dict[str, List[str]] = defaultdict(list)   # decision_id → [snapshot_ids]
        self._by_workflow:  Dict[str, List[str]] = defaultdict(list)
        self._by_portfolio: Dict[str, List[str]] = defaultdict(list)
        self._by_strategy:  Dict[str, List[str]] = defaultdict(list)
        self._by_status:    Dict[str, List[str]] = defaultdict(list)   # DecisionStatus.value
        self._by_type:      Dict[str, List[str]] = defaultdict(list)   # decision_type
        self._by_priority:  Dict[str, List[str]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def register(self, snapshot: DecisionSnapshot) -> None:
        """
        Register a snapshot.

        Raises
        ------
        :class:`DuplicateSnapshotError` : If snapshot_id already exists.
        :class:`SnapshotRegistryError`  : If registry is at capacity.
        """
        with self._lock:
            sid = snapshot.snapshot_id
            if sid in self._by_id:
                raise DuplicateSnapshotError(sid)
            if len(self._by_id) >= self._max:
                raise SnapshotRegistryError(
                    f"Registry full (max {self._max})"
                )
            # Version limit per decision
            did = snapshot.decision_id
            existing_versions = self._by_decision.get(did, [])
            if len(existing_versions) >= self._max_versions:
                raise SnapshotRegistryError(
                    f"Version limit ({self._max_versions}) reached "
                    f"for decision {did!r}"
                )

            self._by_id[sid] = snapshot
            self._by_session[snapshot.session_id].append(sid)
            self._by_decision[did].append(sid)
            if snapshot.workflow_id:
                self._by_workflow[snapshot.workflow_id].append(sid)
            if snapshot.portfolio_id:
                self._by_portfolio[snapshot.portfolio_id].append(sid)
            if snapshot.strategy_id:
                self._by_strategy[snapshot.strategy_id].append(sid)
            self._by_status[snapshot.decision_status.value].append(sid)
            self._by_type[snapshot.decision_type].append(sid)
            self._by_priority[snapshot.decision_priority].append(sid)

    def deregister(self, snapshot_id: str) -> Optional[DecisionSnapshot]:
        """Remove and return the snapshot for *snapshot_id*, or None."""
        with self._lock:
            snap = self._by_id.pop(snapshot_id, None)
            if snap is None:
                return None
            self._remove_from_index(self._by_session,  snap.session_id,              snapshot_id)
            self._remove_from_index(self._by_decision, snap.decision_id,             snapshot_id)
            self._remove_from_index(self._by_workflow, snap.workflow_id,             snapshot_id)
            self._remove_from_index(self._by_portfolio,snap.portfolio_id,            snapshot_id)
            self._remove_from_index(self._by_strategy, snap.strategy_id,             snapshot_id)
            self._remove_from_index(self._by_status,   snap.decision_status.value,   snapshot_id)
            self._remove_from_index(self._by_type,     snap.decision_type,           snapshot_id)
            self._remove_from_index(self._by_priority, snap.decision_priority,       snapshot_id)
            return snap

    # ------------------------------------------------------------------
    # Read — primary key
    # ------------------------------------------------------------------

    def get(self, snapshot_id: str) -> DecisionSnapshot:
        with self._lock:
            if snapshot_id not in self._by_id:
                raise SnapshotNotFoundError(snapshot_id)
            return self._by_id[snapshot_id]

    def find(self, snapshot_id: str) -> Optional[DecisionSnapshot]:
        with self._lock:
            return self._by_id.get(snapshot_id)

    def contains(self, snapshot_id: str) -> bool:
        with self._lock:
            return snapshot_id in self._by_id

    # ------------------------------------------------------------------
    # Read — secondary indices
    # ------------------------------------------------------------------

    def by_session(self, session_id: str) -> List[DecisionSnapshot]:
        return self._resolve(self._by_session.get(session_id, []))

    def by_decision(self, decision_id: str) -> List[DecisionSnapshot]:
        return self._resolve(self._by_decision.get(decision_id, []))

    def by_workflow(self, workflow_id: str) -> List[DecisionSnapshot]:
        return self._resolve(self._by_workflow.get(workflow_id, []))

    def by_portfolio(self, portfolio_id: str) -> List[DecisionSnapshot]:
        return self._resolve(self._by_portfolio.get(portfolio_id, []))

    def by_strategy(self, strategy_id: str) -> List[DecisionSnapshot]:
        return self._resolve(self._by_strategy.get(strategy_id, []))

    def by_status(self, status: str) -> List[DecisionSnapshot]:
        return self._resolve(self._by_status.get(status, []))

    def by_type(self, decision_type: str) -> List[DecisionSnapshot]:
        return self._resolve(self._by_type.get(decision_type, []))

    def by_priority(self, priority: str) -> List[DecisionSnapshot]:
        return self._resolve(self._by_priority.get(priority, []))

    def latest_for_decision(self, decision_id: str) -> Optional[DecisionSnapshot]:
        """Return the snapshot with the highest version for *decision_id*."""
        snaps = self.by_decision(decision_id)
        if not snaps:
            return None
        return max(snaps, key=lambda s: s.snapshot_version)

    def all_snapshots(self) -> List[DecisionSnapshot]:
        with self._lock:
            return list(self._by_id.values())

    def count(self) -> int:
        with self._lock:
            return len(self._by_id)

    def clear(self) -> None:
        with self._lock:
            self._by_id.clear()
            self._by_session.clear()
            self._by_decision.clear()
            self._by_workflow.clear()
            self._by_portfolio.clear()
            self._by_strategy.clear()
            self._by_status.clear()
            self._by_type.clear()
            self._by_priority.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _remove_from_index(
        index: Dict[str, List[str]], key: str, snapshot_id: str
    ) -> None:
        if key in index:
            try:
                index[key].remove(snapshot_id)
            except ValueError:
                pass
            if not index[key]:
                del index[key]

    def _resolve(self, ids: List[str]) -> List[DecisionSnapshot]:
        with self._lock:
            return [self._by_id[sid] for sid in ids if sid in self._by_id]
