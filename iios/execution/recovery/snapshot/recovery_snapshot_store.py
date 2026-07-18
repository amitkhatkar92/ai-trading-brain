"""
iios/execution/recovery/snapshot/recovery_snapshot_store.py
===========================================================
RecoverySnapshotStore — lifecycle-aware primary in-memory store for
ExecutionRecoverySnapshot objects.

Supports all query patterns required by the spec:
  • By Snapshot ID
  • By Recovery Session ID
  • By Failure ID
  • By Execution ID (execution_session_id)
  • By Workflow ID
  • By Gateway ID
  • By Broker ID
  • By Recovery Status (SnapshotStatus)
  • By Verification Status (VerificationOutcome)
  • By Timestamp range
  • Latest Snapshot (globally most recent)
  • Historical Versions (by session)

C7 Execution Recovery & Resilience — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional, TYPE_CHECKING

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import DEFAULT_MAX_SNAPSHOTS, STORE_ID, VERSION, SnapshotStatus, VerificationOutcome
from .exceptions import SnapshotDuplicateError, SnapshotNotFoundError, SnapshotNotRunningError, SnapshotStoreError

if TYPE_CHECKING:
    from .execution_recovery_snapshot import ExecutionRecoverySnapshot

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class RecoverySnapshotStore(LifecycleAwareMixin):
    """
    Lifecycle-aware in-memory store for ExecutionRecoverySnapshot objects.

    Maintains indexes for fast lookup by session, failure, execution,
    workflow, gateway, broker, status, and verification outcome.

    Enforces capacity limits (DEFAULT_MAX_SNAPSHOTS).
    Raises SnapshotDuplicateError when saving a snapshot with an existing ID.
    """

    VERSION   = VERSION
    SYSTEM_ID = STORE_ID

    def __init__(self, max_snapshots: int = DEFAULT_MAX_SNAPSHOTS) -> None:
        super().__init__()
        self._max_snapshots = max_snapshots
        self._lock = threading.Lock()
        # Primary store: snapshot_id → snapshot
        self._store: Dict[str, "ExecutionRecoverySnapshot"] = {}
        # Insertion-order list for "latest globally" queries
        self._ordered: List[str] = []  # snapshot_ids in insertion order

    def _on_start(self) -> None:
        _log.info("RecoverySnapshotStore started", system_id=STORE_ID)

    def _on_stop(self) -> None:
        _log.info("RecoverySnapshotStore stopped", system_id=STORE_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise SnapshotNotRunningError()

    # ── Write ─────────────────────────────────────────────────────────────────

    def save(self, snapshot: "ExecutionRecoverySnapshot") -> None:
        """Persist a snapshot.  Raises SnapshotDuplicateError if snapshot_id exists."""
        self._assert_running()
        with self._lock:
            if snapshot.snapshot_id in self._store:
                raise SnapshotDuplicateError(snapshot.snapshot_id)
            if len(self._store) >= self._max_snapshots:
                raise SnapshotStoreError(
                    f"Store capacity reached ({self._max_snapshots}). "
                    "Archive older snapshots before saving new ones."
                )
            self._store[snapshot.snapshot_id] = snapshot
            self._ordered.append(snapshot.snapshot_id)
            _log.debug(
                "Snapshot saved",
                snapshot_id=snapshot.snapshot_id,
                session_id=snapshot.recovery_session_id,
            )

    def update(self, snapshot: "ExecutionRecoverySnapshot") -> None:
        """Overwrite an existing snapshot (e.g., status change).
        Raises SnapshotNotFoundError if the ID does not exist."""
        self._assert_running()
        with self._lock:
            if snapshot.snapshot_id not in self._store:
                raise SnapshotNotFoundError(snapshot.snapshot_id)
            self._store[snapshot.snapshot_id] = snapshot

    # ── Read ──────────────────────────────────────────────────────────────────

    def get(self, snapshot_id: str) -> Optional["ExecutionRecoverySnapshot"]:
        """Return snapshot by ID, or None."""
        self._assert_running()
        with self._lock:
            return self._store.get(snapshot_id)

    def get_or_raise(self, snapshot_id: str) -> "ExecutionRecoverySnapshot":
        """Return snapshot by ID.  Raises SnapshotNotFoundError if absent."""
        snap = self.get(snapshot_id)
        if snap is None:
            raise SnapshotNotFoundError(snapshot_id)
        return snap

    def all(self) -> List["ExecutionRecoverySnapshot"]:
        """Return all stored snapshots in insertion order."""
        self._assert_running()
        with self._lock:
            return [self._store[sid] for sid in self._ordered if sid in self._store]

    def latest(self) -> Optional["ExecutionRecoverySnapshot"]:
        """Return the most recently saved snapshot, or None."""
        self._assert_running()
        with self._lock:
            if not self._ordered:
                return None
            return self._store.get(self._ordered[-1])

    # ── Indexed queries ───────────────────────────────────────────────────────

    def by_session(self, recovery_session_id: str) -> List["ExecutionRecoverySnapshot"]:
        self._assert_running()
        with self._lock:
            return [s for s in self._store.values()
                    if s.recovery_session_id == recovery_session_id]

    def by_failure(self, failure_id: str) -> List["ExecutionRecoverySnapshot"]:
        self._assert_running()
        with self._lock:
            return [s for s in self._store.values() if s.failure_id == failure_id]

    def by_execution(self, execution_session_id: str) -> List["ExecutionRecoverySnapshot"]:
        self._assert_running()
        with self._lock:
            return [s for s in self._store.values()
                    if s.execution_session_id == execution_session_id]

    def by_workflow(self, workflow_id: str) -> List["ExecutionRecoverySnapshot"]:
        self._assert_running()
        with self._lock:
            return [s for s in self._store.values() if s.workflow_id == workflow_id]

    def by_gateway(self, gateway_id: str) -> List["ExecutionRecoverySnapshot"]:
        self._assert_running()
        with self._lock:
            return [s for s in self._store.values() if s.gateway_id == gateway_id]

    def by_broker(self, broker_id: str) -> List["ExecutionRecoverySnapshot"]:
        self._assert_running()
        with self._lock:
            return [s for s in self._store.values() if s.broker_id == broker_id]

    def by_status(self, status: SnapshotStatus) -> List["ExecutionRecoverySnapshot"]:
        self._assert_running()
        with self._lock:
            return [s for s in self._store.values() if s.recovery_status == status]

    def by_result(self, recovery_result) -> List["ExecutionRecoverySnapshot"]:
        self._assert_running()
        with self._lock:
            return [s for s in self._store.values() if s.recovery_result == recovery_result]

    def by_verification(
        self, verification_result: VerificationOutcome
    ) -> List["ExecutionRecoverySnapshot"]:
        self._assert_running()
        with self._lock:
            return [s for s in self._store.values()
                    if s.verification_result == verification_result]

    def by_timestamp_range(
        self,
        since: float,
        before: Optional[float] = None,
    ) -> List["ExecutionRecoverySnapshot"]:
        """Return snapshots whose timestamp >= since (and < before if given)."""
        self._assert_running()
        with self._lock:
            results = [s for s in self._store.values() if s.timestamp >= since]
            if before is not None:
                results = [s for s in results if s.timestamp < before]
            return sorted(results, key=lambda s: s.timestamp)

    def latest_for_session(
        self, recovery_session_id: str
    ) -> Optional["ExecutionRecoverySnapshot"]:
        """Return the latest (highest snapshot_version) for a session, or None."""
        self._assert_running()
        with self._lock:
            candidates = [
                s for s in self._store.values()
                if s.recovery_session_id == recovery_session_id
            ]
            if not candidates:
                return None
            return max(candidates, key=lambda s: s.snapshot_version)

    # ── Counts ────────────────────────────────────────────────────────────────

    @property
    def snapshot_count(self) -> int:
        with self._lock:
            return len(self._store)

    def contains(self, snapshot_id: str) -> bool:
        with self._lock:
            return snapshot_id in self._store

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._ordered.clear()
