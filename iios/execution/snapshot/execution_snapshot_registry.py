"""iios/execution/snapshot/execution_snapshot_registry.py
==================================================
ExecutionSnapshotRegistry — IIOS v1.0 thread-safe registry of
ExecutionSnapshot objects with secondary indexes and event dispatch.

C6 Execution Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import dataclasses
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

from iios.common.errors.error_context import ErrorContext
from iios.common.errors.error_manager import get_error_manager as _get_err_mgr
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ACTOR_REGISTRY,
    ACTOR_SYSTEM,
    DEFAULT_MAX_SNAPSHOTS,
    DEFAULT_MAX_HISTORY,
    REGISTRY_SYSTEM_ID,
    SnapshotLifecycle,
    VERSION,
)
from .exceptions import (
    DuplicateSnapshotError,
    SnapshotCapacityError,
    SnapshotNotFoundError,
    SnapshotStoreNotRunning,
)
from .execution_snapshot import ExecutionSnapshot
from .execution_snapshot_events import (
    SnapshotEvent,
    SnapshotEventType,
    make_snapshot_event,
)
from .execution_snapshot_history import (
    ExecutionSnapshotHistory,
    SnapshotRevision,
    make_snapshot_revision,
)
from .execution_snapshot_statistics import ExecutionSnapshotStats, SnapshotBuildStats

_log   = get_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=REGISTRY_SYSTEM_ID,
                          component="ExecutionSnapshotRegistry")


@dataclass
class SnapshotRecord:
    """Container for a registered snapshot and its history."""

    snapshot_id:  str
    execution_id: str
    snapshot:     ExecutionSnapshot
    history:      ExecutionSnapshotHistory = field(init=False)
    registered_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        self.history = ExecutionSnapshotHistory(
            self.execution_id,
            max_entries=DEFAULT_MAX_HISTORY,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id":    self.snapshot_id,
            "execution_id":   self.execution_id,
            "registered_at":  self.registered_at,
            "revision_count": self.history.count(),
        }


class ExecutionSnapshotRegistry(LifecycleAwareMixin):
    """
    IIOS v1.0 registry for ExecutionSnapshot objects.

    Thread-safe. Lifecycle-aware. Secondary indexes by execution, workflow,
    order, and lifecycle. Event dispatch on lifecycle changes.
    """

    SYSTEM_ID = REGISTRY_SYSTEM_ID
    VERSION   = VERSION

    def __init__(self, max_snapshots: int = DEFAULT_MAX_SNAPSHOTS) -> None:
        self._records:      dict[str, SnapshotRecord]          = {}
        self._by_execution: dict[str, list[str]]               = {}
        self._by_workflow:  dict[str, list[str]]               = {}
        self._by_order:     dict[str, list[str]]               = {}
        self._by_lifecycle: dict[SnapshotLifecycle, list[str]] = {
            lc: [] for lc in SnapshotLifecycle
        }
        self._max_snapshots = max_snapshots
        self._lock          = threading.RLock()
        self._listeners:    list[Callable[[SnapshotEvent], None]] = []
        self._stats         = ExecutionSnapshotStats()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(
            self.SYSTEM_ID, "STOPPED", "RUNNING", self.VERSION
        )
        _log.info("ExecutionSnapshotRegistry started.", capacity=self._max_snapshots)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            self.SYSTEM_ID, "RUNNING", "STOPPED", self.VERSION
        )
        _log.info("ExecutionSnapshotRegistry stopped.", registered=len(self._records))

    @property
    def is_running(self) -> bool:
        return self.lifecycle_state() == EngineState.RUNNING

    def _assert_running(self) -> None:
        if not self.is_running:
            raise SnapshotStoreNotRunning(
                "ExecutionSnapshotRegistry must be started before use."
            )

    # ── Registration ──────────────────────────────────────────────────────────

    def register(
        self,
        snapshot:  ExecutionSnapshot,
        overwrite: bool = False,
    ) -> SnapshotRecord:
        self._assert_running()
        sid = snapshot.snapshot_id
        with self._lock:
            if sid in self._records and not overwrite:
                raise DuplicateSnapshotError(sid)
            if len(self._records) >= self._max_snapshots and sid not in self._records:
                raise SnapshotCapacityError(
                    f"Registry capacity reached ({self._max_snapshots})"
                )
            record = SnapshotRecord(
                snapshot_id  = sid,
                execution_id = snapshot.execution_id,
                snapshot     = snapshot,
            )
            rev = make_snapshot_revision(
                snapshot, actor=ACTOR_REGISTRY, reason="registered",
            )
            record.history.record(rev)
            self._records[sid] = record
            self._by_execution.setdefault(snapshot.execution_id, []).append(sid)
            self._by_workflow.setdefault(snapshot.workflow_id,   []).append(sid)
            self._by_order.setdefault(snapshot.order_id,        []).append(sid)
            self._by_lifecycle[snapshot.lifecycle].append(sid)

        _log.info("Snapshot registered.",
                  snapshot_id=sid, execution_id=snapshot.execution_id,
                  state=snapshot.execution_state)
        _audit.log_workflow_event(
            self.SYSTEM_ID, "register", "SNAPSHOT_REGISTERED",
            actor=ACTOR_REGISTRY,
            snapshot_id=sid,
        )
        event = make_snapshot_event(
            SnapshotEventType.SNAPSHOT_CREATED,
            sid,
            execution_id = snapshot.execution_id,
            workflow_id  = snapshot.workflow_id,
            lifecycle    = snapshot.lifecycle,
        )
        self._dispatch(event)
        return record

    def update_lifecycle(
        self,
        snapshot_id: str,
        lifecycle:   SnapshotLifecycle,
        *,
        actor:  str = ACTOR_SYSTEM,
        reason: str = "",
    ) -> SnapshotRecord:
        """Transition lifecycle and append a revision."""
        self._assert_running()
        with self._lock:
            record = self._get_or_raise(snapshot_id)
            old_lc = record.snapshot.lifecycle

            new_snap = dataclasses.replace(record.snapshot, lifecycle=lifecycle)
            record.snapshot = new_snap

            if snapshot_id in self._by_lifecycle[old_lc]:
                self._by_lifecycle[old_lc].remove(snapshot_id)
            self._by_lifecycle[lifecycle].append(snapshot_id)

            rev = make_snapshot_revision(new_snap, actor=actor, reason=reason)
            record.history.record(rev)

        et_map = {
            SnapshotLifecycle.VALIDATED: SnapshotEventType.SNAPSHOT_VALIDATED,
            SnapshotLifecycle.PUBLISHED: SnapshotEventType.SNAPSHOT_PUBLISHED,
            SnapshotLifecycle.STORED:    SnapshotEventType.SNAPSHOT_STORED,
            SnapshotLifecycle.ARCHIVED:  SnapshotEventType.SNAPSHOT_ARCHIVED,
        }
        if lifecycle in et_map:
            event = make_snapshot_event(
                et_map[lifecycle], snapshot_id,
                execution_id = record.snapshot.execution_id,
                workflow_id  = record.snapshot.workflow_id,
                lifecycle    = lifecycle,
            )
            self._dispatch(event)
        return record

    # ── Queries ───────────────────────────────────────────────────────────────

    def get(self, snapshot_id: str) -> ExecutionSnapshot:
        self._assert_running()
        with self._lock:
            return self._get_or_raise(snapshot_id).snapshot

    def get_record(self, snapshot_id: str) -> SnapshotRecord:
        self._assert_running()
        with self._lock:
            return self._get_or_raise(snapshot_id)

    def contains(self, snapshot_id: str) -> bool:
        with self._lock:
            return snapshot_id in self._records

    def count(self) -> int:
        with self._lock:
            return len(self._records)

    def get_by_execution(self, execution_id: str) -> list[ExecutionSnapshot]:
        self._assert_running()
        with self._lock:
            ids = self._by_execution.get(execution_id, [])
            return [self._records[sid].snapshot for sid in ids if sid in self._records]

    def get_by_workflow(self, workflow_id: str) -> list[ExecutionSnapshot]:
        self._assert_running()
        with self._lock:
            ids = self._by_workflow.get(workflow_id, [])
            return [self._records[sid].snapshot for sid in ids if sid in self._records]

    def get_by_order(self, order_id: str) -> list[ExecutionSnapshot]:
        self._assert_running()
        with self._lock:
            ids = self._by_order.get(order_id, [])
            return [self._records[sid].snapshot for sid in ids if sid in self._records]

    def get_by_lifecycle(self, lifecycle: SnapshotLifecycle) -> list[ExecutionSnapshot]:
        self._assert_running()
        with self._lock:
            ids = self._by_lifecycle.get(lifecycle, [])
            return [self._records[sid].snapshot for sid in ids if sid in self._records]

    def get_history(self, snapshot_id: str) -> ExecutionSnapshotHistory:
        self._assert_running()
        with self._lock:
            return self._get_or_raise(snapshot_id).history

    def all_snapshot_ids(self) -> list[str]:
        with self._lock:
            return list(self._records.keys())

    # ── Statistics ────────────────────────────────────────────────────────────

    def record_build(self, build_stats: SnapshotBuildStats) -> None:
        self._stats.record_build(build_stats)

    def statistics(self) -> ExecutionSnapshotStats:
        return self._stats

    # ── Listeners ─────────────────────────────────────────────────────────────

    def add_listener(self, fn: Callable[[SnapshotEvent], None]) -> None:
        with self._lock:
            if fn not in self._listeners:
                self._listeners.append(fn)

    def remove_listener(self, fn: Callable[[SnapshotEvent], None]) -> None:
        with self._lock:
            self._listeners = [f for f in self._listeners if f != fn]

    def _dispatch(self, event: SnapshotEvent) -> None:
        with self._lock:
            listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn(event)
            except Exception:
                _log.warning("Snapshot event listener raised — continuing.")

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get_or_raise(self, snapshot_id: str) -> SnapshotRecord:
        record = self._records.get(snapshot_id)
        if record is None:
            raise SnapshotNotFoundError(snapshot_id)
        return record
