"""iios/execution/positions/snapshot/position_snapshot_registry.py
==================================================
PositionSnapshotRegistry — LifecycleAwareMixin internal storage layer.

Maintains:
  * Per-position version history (latest + all historical versions)
  * O(1) lookup by snapshot_id
  * Secondary indexes: portfolio, strategy, workflow, instrument

Write operations require RUNNING state.
Read operations are always permitted.

C6 Execution Intelligence — Phase 3, Module 5
"""
from __future__ import annotations

import threading
from collections import defaultdict
from typing import Dict, List, Optional, Set

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from .constants import (
    DEFAULT_MAX_STORE_POSITIONS,
    DEFAULT_MAX_VERSIONS_PER_POSITION,
    REGISTRY_SYSTEM_ID,
    VERSION,
)
from .exceptions import (
    DuplicateSnapshotError,
    PositionSnapshotNotRunningError,
    SnapshotCapacityError,
    SnapshotNotFoundError,
)
from .position_snapshot import PositionSnapshot
from .position_snapshot_history import SnapshotVersionHistory

_log   = get_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)


class PositionSnapshotRegistry(LifecycleAwareMixin):
    """
    Thread-safe internal storage and index layer for position snapshots.

    Write operations (store, remove) require RUNNING state.
    Read operations (get, query) are always permitted.
    """

    def __init__(
        self,
        max_positions:          int = DEFAULT_MAX_STORE_POSITIONS,
        max_versions_per_position: int = DEFAULT_MAX_VERSIONS_PER_POSITION,
    ) -> None:
        super().__init__()
        self._max_positions = max(1, max_positions)
        self._versions      = SnapshotVersionHistory(max_versions_per_position)
        # Fast lookup by snapshot_id
        self._by_snapshot_id: Dict[str, PositionSnapshot] = {}
        # Secondary indexes: value = set of position_ids
        self._by_portfolio:   Dict[str, Set[str]] = defaultdict(set)
        self._by_strategy:    Dict[str, Set[str]] = defaultdict(set)
        self._by_workflow:    Dict[str, Set[str]] = defaultdict(set)
        self._by_instrument:  Dict[str, Set[str]] = defaultdict(set)
        self._lock = threading.Lock()

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(
            REGISTRY_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        _log.info("PositionSnapshotRegistry started.", max_positions=self._max_positions)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            REGISTRY_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        _log.info("PositionSnapshotRegistry stopped.", tracked=self.count())

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise PositionSnapshotNotRunningError()

    # ── Write ─────────────────────────────────────────────────────────────────

    def store(self, snapshot: PositionSnapshot) -> None:
        """
        Store *snapshot* in the registry and update all indexes.

        Raises
        ------
        PositionSnapshotNotRunningError
        SnapshotCapacityError   — too many positions tracked
        DuplicateSnapshotError  — snapshot_id already exists
        """
        self._assert_running()
        pid = snapshot.position_id
        sid = snapshot.snapshot_id

        with self._lock:
            if sid in self._by_snapshot_id:
                raise DuplicateSnapshotError(sid)

            # Capacity check: only when first snapshot for a new position
            if pid not in self._versions._history:
                if len(self._versions._history) >= self._max_positions:
                    raise SnapshotCapacityError(self._max_positions)

            # Persist
            self._versions.add(snapshot)
            self._by_snapshot_id[sid] = snapshot

            # Update secondary indexes
            if pid and snapshot.portfolio_id:
                self._by_portfolio[snapshot.portfolio_id].add(pid)
            if pid and snapshot.strategy_id:
                self._by_strategy[snapshot.strategy_id].add(pid)
            if pid and snapshot.workflow_id:
                self._by_workflow[snapshot.workflow_id].add(pid)
            if pid and snapshot.instrument:
                self._by_instrument[snapshot.instrument].add(pid)

        _log.debug(
            "Snapshot stored.",
            snapshot_id=sid[:8],
            position_id=pid,
            version=snapshot.snapshot_version,
        )

    def update(self, snapshot: PositionSnapshot) -> None:
        """
        Replace the latest snapshot for a position with *snapshot*.

        Used when status transitions produce a new frozen instance
        (e.g. DRAFT → VALID → PUBLISHED).  The snapshot_id does not
        change across transitions — this method replaces the indexed entry.

        Raises
        ------
        PositionSnapshotNotRunningError
        """
        self._assert_running()
        sid = snapshot.snapshot_id

        with self._lock:
            # Status transitions keep the same snapshot_id — always overwrite
            self._versions.add(snapshot)
            self._by_snapshot_id[sid] = snapshot

    def remove(self, position_id: str) -> List[PositionSnapshot]:
        """
        Remove ALL snapshot versions for *position_id*.

        Returns the list of removed snapshots.

        Raises
        ------
        PositionSnapshotNotRunningError
        SnapshotNotFoundError
        """
        self._assert_running()
        with self._lock:
            all_versions = self._versions.get_all_versions(position_id)
            if not all_versions:
                raise SnapshotNotFoundError(position_id)

            self._versions.purge(position_id)
            for snap in all_versions:
                self._by_snapshot_id.pop(snap.snapshot_id, None)

            # Clean up secondary indexes
            for idx in (self._by_portfolio, self._by_strategy,
                        self._by_workflow, self._by_instrument):
                for key in list(idx.keys()):
                    idx[key].discard(position_id)
                    if not idx[key]:
                        del idx[key]

        _log.debug("Snapshots removed.", position_id=position_id, count=len(all_versions))
        return all_versions

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_latest(self, position_id: str) -> Optional[PositionSnapshot]:
        return self._versions.get_latest(position_id)

    def require_latest(self, position_id: str) -> PositionSnapshot:
        snap = self.get_latest(position_id)
        if snap is None:
            raise SnapshotNotFoundError(position_id)
        return snap

    def get_by_snapshot_id(self, snapshot_id: str) -> Optional[PositionSnapshot]:
        with self._lock:
            return self._by_snapshot_id.get(snapshot_id)

    def require_by_snapshot_id(self, snapshot_id: str) -> PositionSnapshot:
        snap = self.get_by_snapshot_id(snapshot_id)
        if snap is None:
            raise SnapshotNotFoundError(snapshot_id)
        return snap

    def get_all_versions(self, position_id: str) -> List[PositionSnapshot]:
        return self._versions.get_all_versions(position_id)

    def get_version(self, position_id: str, version: int) -> Optional[PositionSnapshot]:
        return self._versions.get_version(position_id, version)

    def all_latest_snapshots(self) -> List[PositionSnapshot]:
        return [
            snap
            for pid in self._versions.all_position_ids()
            for snap in [self._versions.get_latest(pid)]
            if snap is not None
        ]

    def get_by_portfolio(self, portfolio_id: str) -> List[PositionSnapshot]:
        with self._lock:
            pids = list(self._by_portfolio.get(portfolio_id, set()))
        return [
            snap
            for pid in pids
            for snap in [self._versions.get_latest(pid)]
            if snap is not None
        ]

    def get_by_strategy(self, strategy_id: str) -> List[PositionSnapshot]:
        with self._lock:
            pids = list(self._by_strategy.get(strategy_id, set()))
        return [
            snap
            for pid in pids
            for snap in [self._versions.get_latest(pid)]
            if snap is not None
        ]

    def get_by_workflow(self, workflow_id: str) -> List[PositionSnapshot]:
        with self._lock:
            pids = list(self._by_workflow.get(workflow_id, set()))
        return [
            snap
            for pid in pids
            for snap in [self._versions.get_latest(pid)]
            if snap is not None
        ]

    def get_by_instrument(self, instrument: str) -> List[PositionSnapshot]:
        with self._lock:
            pids = list(self._by_instrument.get(instrument, set()))
        return [
            snap
            for pid in pids
            for snap in [self._versions.get_latest(pid)]
            if snap is not None
        ]

    def get_by_timestamp_range(self, start: float, end: float) -> List[PositionSnapshot]:
        with self._lock:
            all_snaps = list(self._by_snapshot_id.values())
        return [s for s in all_snaps if start <= s.snapshot_taken_at <= end]

    def contains(self, position_id: str) -> bool:
        return self._versions.get_latest(position_id) is not None

    def count(self) -> int:
        return len(self._versions.all_position_ids())

    def is_empty(self) -> bool:
        return self._versions.is_empty()
