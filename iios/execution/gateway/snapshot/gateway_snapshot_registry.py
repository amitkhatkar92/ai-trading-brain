"""iios/execution/gateway/snapshot/gateway_snapshot_registry.py
==================================================
GatewaySnapshotRegistry — lifecycle-aware primary storage for
ExecutionGatewaySnapshot objects with multi-dimensional indexes.

C6 Execution Intelligence — Phase 5, Module 5
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional, Set

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    DEFAULT_MAX_SNAPSHOTS,
    SNAPSHOT_REGISTRY_SYSTEM_ID,
    VERSION,
)
from .exceptions import (
    DuplicateSnapshotError,
    SnapshotNotFoundError,
    SnapshotStoreCapacityError,
    SnapshotStoreNotRunningError,
)
from .execution_gateway_snapshot import ExecutionGatewaySnapshot

_log = get_logger(__name__, engine_id=SNAPSHOT_REGISTRY_SYSTEM_ID)


class GatewaySnapshotRegistry(LifecycleAwareMixin):
    """
    Lifecycle-aware primary store for ExecutionGatewaySnapshot objects.

    Maintains secondary indexes for all supported query dimensions so
    each query runs in O(1) average time.

    Write operations require RUNNING state.
    Read operations are permitted in any state.
    """

    SYSTEM_ID = SNAPSHOT_REGISTRY_SYSTEM_ID

    def __init__(self, max_snapshots: int = DEFAULT_MAX_SNAPSHOTS) -> None:
        super().__init__()
        self._max_snapshots = max(1, max_snapshots)

        # Primary store
        self._snapshots: Dict[str, ExecutionGatewaySnapshot] = {}

        # Archived set (snapshot_id values)
        self._archived: Set[str] = set()

        # Secondary indexes: dimension → list of snapshot_ids (ordered by creation)
        self._idx_execution:  Dict[str, List[str]] = {}
        self._idx_order:      Dict[str, List[str]] = {}
        self._idx_position:   Dict[str, List[str]] = {}
        self._idx_portfolio:  Dict[str, List[str]] = {}
        self._idx_workflow:   Dict[str, List[str]] = {}
        self._idx_strategy:   Dict[str, List[str]] = {}
        self._idx_gateway:    Dict[str, List[str]] = {}
        self._idx_broker:     Dict[str, List[str]] = {}
        self._idx_gw_state:   Dict[str, List[str]] = {}

        self._lock = threading.RLock()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        _log.info("GatewaySnapshotRegistry started.", version=VERSION)

    def _on_stop(self) -> None:
        _log.info(
            "GatewaySnapshotRegistry stopped.",
            stored_count=len(self._snapshots),
        )

    def _guard_write(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise SnapshotStoreNotRunningError()

    # ── Storage ───────────────────────────────────────────────────────────────

    def store(self, snapshot: ExecutionGatewaySnapshot) -> None:
        """
        Store a snapshot.  Requires RUNNING state.

        Raises DuplicateSnapshotError if snapshot_id already exists.
        Raises SnapshotStoreCapacityError if at max capacity.
        """
        self._guard_write()
        with self._lock:
            if snapshot.snapshot_id in self._snapshots:
                raise DuplicateSnapshotError(snapshot.snapshot_id)
            if len(self._snapshots) >= self._max_snapshots:
                raise SnapshotStoreCapacityError(self._max_snapshots)
            self._snapshots[snapshot.snapshot_id] = snapshot
            self._index(snapshot)
            _log.debug("Snapshot stored.", snapshot_id=snapshot.snapshot_id)

    def archive(self, snapshot_id: str) -> None:
        """
        Mark a snapshot as archived.  Requires RUNNING state.

        Archived snapshots remain retrievable but are flagged.
        """
        self._guard_write()
        with self._lock:
            if snapshot_id not in self._snapshots:
                raise SnapshotNotFoundError(snapshot_id)
            self._archived.add(snapshot_id)
            _log.debug("Snapshot archived.", snapshot_id=snapshot_id)

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def get(self, snapshot_id: str) -> ExecutionGatewaySnapshot:
        """Return a snapshot by ID.  Raises SnapshotNotFoundError."""
        with self._lock:
            if snapshot_id not in self._snapshots:
                raise SnapshotNotFoundError(snapshot_id)
            return self._snapshots[snapshot_id]

    def get_optional(self, snapshot_id: str) -> Optional[ExecutionGatewaySnapshot]:
        with self._lock:
            return self._snapshots.get(snapshot_id)

    def all(self) -> List[ExecutionGatewaySnapshot]:
        with self._lock:
            return list(self._snapshots.values())

    def latest(self) -> Optional[ExecutionGatewaySnapshot]:
        """Return the most recently stored snapshot."""
        with self._lock:
            if not self._snapshots:
                return None
            return max(self._snapshots.values(), key=lambda s: s.created_at)

    def is_archived(self, snapshot_id: str) -> bool:
        with self._lock:
            return snapshot_id in self._archived

    # ── Query by dimension ────────────────────────────────────────────────────

    def by_execution_id(self, execution_id: str) -> List[ExecutionGatewaySnapshot]:
        return self._query(self._idx_execution, execution_id)

    def by_order_id(self, order_id: str) -> List[ExecutionGatewaySnapshot]:
        return self._query(self._idx_order, order_id)

    def by_position_id(self, position_id: str) -> List[ExecutionGatewaySnapshot]:
        return self._query(self._idx_position, position_id)

    def by_portfolio_id(self, portfolio_id: str) -> List[ExecutionGatewaySnapshot]:
        return self._query(self._idx_portfolio, portfolio_id)

    def by_workflow_id(self, workflow_id: str) -> List[ExecutionGatewaySnapshot]:
        return self._query(self._idx_workflow, workflow_id)

    def by_strategy_id(self, strategy_id: str) -> List[ExecutionGatewaySnapshot]:
        return self._query(self._idx_strategy, strategy_id)

    def by_gateway_id(self, gateway_id: str) -> List[ExecutionGatewaySnapshot]:
        return self._query(self._idx_gateway, gateway_id)

    def by_broker_id(self, broker_id: str) -> List[ExecutionGatewaySnapshot]:
        return self._query(self._idx_broker, broker_id)

    def by_gateway_state(self, state_value: str) -> List[ExecutionGatewaySnapshot]:
        return self._query(self._idx_gw_state, state_value)

    def latest_for_execution(
        self, execution_id: str
    ) -> Optional[ExecutionGatewaySnapshot]:
        snaps = self.by_execution_id(execution_id)
        return max(snaps, key=lambda s: s.created_at) if snaps else None

    # ── State ─────────────────────────────────────────────────────────────────

    @property
    def snapshot_count(self) -> int:
        with self._lock:
            return len(self._snapshots)

    @property
    def archived_count(self) -> int:
        with self._lock:
            return len(self._archived)

    # ── Indexing helpers ──────────────────────────────────────────────────────

    def _index(self, snapshot: ExecutionGatewaySnapshot) -> None:
        sid = snapshot.snapshot_id
        self._append_index(self._idx_execution, snapshot.execution_id, sid)
        self._append_index(self._idx_order,     snapshot.order_id,     sid)
        self._append_index(self._idx_portfolio, snapshot.portfolio_id, sid)
        self._append_index(self._idx_strategy,  snapshot.strategy_id,  sid)
        self._append_index(self._idx_gateway,   snapshot.gateway_id,   sid)
        self._append_index(self._idx_gw_state,  snapshot.gateway_state.value, sid)
        if snapshot.position_id:
            self._append_index(self._idx_position, snapshot.position_id, sid)
        if snapshot.workflow_id:
            self._append_index(self._idx_workflow, snapshot.workflow_id, sid)
        if snapshot.selected_broker_id:
            self._append_index(self._idx_broker, snapshot.selected_broker_id, sid)

    @staticmethod
    def _append_index(idx: Dict[str, List[str]], key: str, sid: str) -> None:
        if key not in idx:
            idx[key] = []
        idx[key].append(sid)

    def _query(
        self,
        idx: Dict[str, List[str]],
        key: str,
    ) -> List[ExecutionGatewaySnapshot]:
        with self._lock:
            ids = idx.get(key, [])
            return [
                self._snapshots[sid]
                for sid in ids
                if sid in self._snapshots
            ]
