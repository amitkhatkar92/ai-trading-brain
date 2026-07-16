"""iios/execution/snapshot/execution_snapshot_store.py
==================================================
ExecutionSnapshotStore — bounded, thread-safe persistent store
for ExecutionSnapshot objects.

The store provides fast lookup by snapshot_id, execution_id,
order_id, and workflow_id. It owns the registry and orchestrates
all lifecycle transitions.

IIOS v1.0: LifecycleAwareMixin, logging, audit.

C6 Execution Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import time
from typing import Any, Callable, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ACTOR_STORE,
    ACTOR_SYSTEM,
    DEFAULT_MAX_SNAPSHOTS,
    STORE_SYSTEM_ID,
    SnapshotLifecycle,
    SnapshotTrigger,
    VERSION,
)
from .exceptions import SnapshotStoreNotRunning, SnapshotValidationError
from .execution_snapshot import ExecutionSnapshot
from .execution_snapshot_events import SnapshotEvent
from .execution_snapshot_history import ExecutionSnapshotHistory
from .execution_snapshot_registry import ExecutionSnapshotRegistry, SnapshotRecord
from .execution_snapshot_statistics import ExecutionSnapshotStats, SnapshotBuildStats
from .execution_snapshot_validator import ExecutionSnapshotValidator, SnapshotValidationResult

_log   = get_logger(__name__, engine_id=STORE_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=STORE_SYSTEM_ID,
                          component="ExecutionSnapshotStore")


class ExecutionSnapshotStore(LifecycleAwareMixin):
    """
    IIOS v1.0 persistent store for ExecutionSnapshot objects.

    Owns the ExecutionSnapshotRegistry and ExecutionSnapshotValidator.
    Coordinates:
      - Validation before storage
      - Lifecycle transitions (CREATED → VALIDATED → STORED → ARCHIVED)
      - Statistics accumulation
      - Event dispatch
    """

    SYSTEM_ID = STORE_SYSTEM_ID
    VERSION   = VERSION

    def __init__(self, max_snapshots: int = DEFAULT_MAX_SNAPSHOTS) -> None:
        self._registry  = ExecutionSnapshotRegistry(max_snapshots=max_snapshots)
        self._validator = ExecutionSnapshotValidator()
        self._started_at: float = 0.0

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        self._registry.start()
        self._started_at = time.time()
        _audit.log_lifecycle_event(
            self.SYSTEM_ID, "STOPPED", "RUNNING", self.VERSION
        )
        _log.info("ExecutionSnapshotStore started.")

    def _on_stop(self) -> None:
        if self._registry.is_running:
            self._registry.stop()
        _audit.log_lifecycle_event(
            self.SYSTEM_ID, "RUNNING", "STOPPED", self.VERSION
        )
        _log.info("ExecutionSnapshotStore stopped.")

    @property
    def is_running(self) -> bool:
        return self.lifecycle_state() == EngineState.RUNNING

    def _assert_running(self) -> None:
        if not self.is_running:
            raise SnapshotStoreNotRunning(
                "ExecutionSnapshotStore must be started before use."
            )

    # ── Main store interface ──────────────────────────────────────────────────

    def store(
        self,
        snapshot:   ExecutionSnapshot,
        *,
        validate:   bool = True,
        overwrite:  bool = False,
    ) -> SnapshotRecord:
        """
        Validate (optionally) and store an ExecutionSnapshot.

        Transitions lifecycle: CREATED → VALIDATED → STORED.

        Parameters
        ----------
        validate  : Run validator before storing. Default True.
        overwrite : Allow replacing an existing snapshot. Default False.

        Raises
        ------
        SnapshotValidationError  If validation fails.
        SnapshotStoreNotRunning  If store not started.
        """
        self._assert_running()
        t0 = time.time()

        if validate:
            result = self._validator.validate(snapshot)
            val_ms = (time.time() - t0) * 1_000
            if not result.passed:
                build_stats = SnapshotBuildStats(
                    snapshot_id       = snapshot.snapshot_id,
                    execution_id      = snapshot.execution_id,
                    build_time_ms     = 0.0,
                    validation_passed = False,
                    validation_time_ms = val_ms,
                    errors            = result.errors,
                )
                self._registry.record_build(build_stats)
                raise SnapshotValidationError(
                    "ExecutionSnapshot validation failed.",
                    errors=result.errors,
                )
        else:
            val_ms = 0.0

        record = self._registry.register(snapshot, overwrite=overwrite)
        self._registry.update_lifecycle(
            snapshot.snapshot_id,
            SnapshotLifecycle.STORED,
            actor  = ACTOR_STORE,
            reason = "stored",
        )

        total_ms = (time.time() - t0) * 1_000
        build_stats = SnapshotBuildStats(
            snapshot_id        = snapshot.snapshot_id,
            execution_id       = snapshot.execution_id,
            build_time_ms      = total_ms,
            validation_passed  = True,
            validation_time_ms = val_ms,
            sequence_number    = snapshot.sequence_number,
        )
        self._registry.record_build(build_stats)
        self._registry._stats.record_stored()

        _log.info(
            "Snapshot stored.",
            snapshot_id  = snapshot.snapshot_id,
            execution_id = snapshot.execution_id,
            state        = snapshot.execution_state,
        )
        return record

    def publish(self, snapshot_id: str) -> SnapshotRecord:
        """Transition a stored snapshot to PUBLISHED."""
        self._assert_running()
        record = self._registry.update_lifecycle(
            snapshot_id,
            SnapshotLifecycle.PUBLISHED,
            actor  = ACTOR_STORE,
            reason = "published",
        )
        self._registry._stats.record_published()
        return record

    def archive(self, snapshot_id: str) -> SnapshotRecord:
        """Transition a snapshot to ARCHIVED."""
        self._assert_running()
        record = self._registry.update_lifecycle(
            snapshot_id,
            SnapshotLifecycle.ARCHIVED,
            actor  = ACTOR_STORE,
            reason = "archived",
        )
        self._registry._stats.record_archived()
        return record

    # ── Queries ───────────────────────────────────────────────────────────────

    def get(self, snapshot_id: str) -> ExecutionSnapshot:
        self._assert_running()
        return self._registry.get(snapshot_id)

    def contains(self, snapshot_id: str) -> bool:
        return self._registry.contains(snapshot_id)

    def count(self) -> int:
        return self._registry.count()

    def get_by_execution(self, execution_id: str) -> list[ExecutionSnapshot]:
        self._assert_running()
        return self._registry.get_by_execution(execution_id)

    def get_by_workflow(self, workflow_id: str) -> list[ExecutionSnapshot]:
        self._assert_running()
        return self._registry.get_by_workflow(workflow_id)

    def get_by_order(self, order_id: str) -> list[ExecutionSnapshot]:
        self._assert_running()
        return self._registry.get_by_order(order_id)

    def get_history(self, snapshot_id: str) -> ExecutionSnapshotHistory:
        self._assert_running()
        return self._registry.get_history(snapshot_id)

    def validate(self, snapshot: ExecutionSnapshot) -> SnapshotValidationResult:
        return self._validator.validate(snapshot)

    def statistics(self) -> ExecutionSnapshotStats:
        return self._registry.statistics()

    # ── Listeners ─────────────────────────────────────────────────────────────

    def add_listener(self, fn: Callable[[SnapshotEvent], None]) -> None:
        self._registry.add_listener(fn)

    def remove_listener(self, fn: Callable[[SnapshotEvent], None]) -> None:
        self._registry.remove_listener(fn)

    # ── Internals ─────────────────────────────────────────────────────────────

    @property
    def uptime_sec(self) -> float:
        if self._started_at == 0.0:
            return 0.0
        return time.time() - self._started_at
