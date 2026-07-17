"""iios/execution/gateway/snapshot/gateway_snapshot_store.py
==================================================
GatewaySnapshotStore — lifecycle-aware coordinator for the full
snapshot publication, retrieval, and archival workflow.

Ownership
---------
  GatewaySnapshotRegistry    — primary indexed storage
  GatewaySnapshotCache       — LRU fast-access layer
  GatewaySnapshotHistory     — bounded event + snapshot log
  GatewaySnapshotStatistics  — cumulative metrics
  GatewaySnapshotValidator   — validation

Publication workflow (publish())
---------------------------------
  1.  Assert RUNNING
  2.  Fire SNAPSHOT_CREATED
  3.  Validate → fire SNAPSHOT_VALIDATED
  4.  Store in registry (raises DuplicateSnapshotError)
  5.  Add to cache → fire SNAPSHOT_CACHED
  6.  Append to history
  7.  Update statistics
  8.  Fire SNAPSHOT_PUBLISHED

Retrieval workflow (get())
--------------------------
  1.  Check cache → return on hit
  2.  Query registry → SnapshotNotFoundError on miss
  3.  Populate cache
  4.  Fire SNAPSHOT_RETRIEVED
  5.  Update statistics

C6 Execution Intelligence — Phase 5, Module 5
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    DEFAULT_MAX_CACHE_SIZE,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SNAPSHOTS,
    SNAPSHOT_STORE_SYSTEM_ID,
    VERSION,
)
from .exceptions import SnapshotStoreNotRunningError, SnapshotValidationError
from .execution_gateway_snapshot import ExecutionGatewaySnapshot
from .gateway_snapshot_cache import GatewaySnapshotCache
from .gateway_snapshot_events import (
    SnapshotEvent,
    make_snapshot_archived_event,
    make_snapshot_cached_event,
    make_snapshot_created_event,
    make_snapshot_published_event,
    make_snapshot_retrieved_event,
    make_snapshot_validated_event,
)
from .gateway_snapshot_history import GatewaySnapshotHistory
from .gateway_snapshot_registry import GatewaySnapshotRegistry
from .gateway_snapshot_statistics import GatewaySnapshotStatistics
from .gateway_snapshot_validation import GatewaySnapshotValidator

_log   = get_logger(__name__, engine_id=SNAPSHOT_STORE_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=SNAPSHOT_STORE_SYSTEM_ID)


class GatewaySnapshotStore(LifecycleAwareMixin):
    """
    Lifecycle-aware store coordinating all snapshot operations.

    This is the primary public-facing component.  Downstream systems
    use the store to publish and retrieve ExecutionGatewaySnapshot.
    """

    SYSTEM_ID = SNAPSHOT_STORE_SYSTEM_ID

    def __init__(
        self,
        max_snapshots:  int = DEFAULT_MAX_SNAPSHOTS,
        max_history:    int = DEFAULT_MAX_HISTORY,
        max_cache_size: int = DEFAULT_MAX_CACHE_SIZE,
    ) -> None:
        super().__init__()
        self._registry  = GatewaySnapshotRegistry(max_snapshots=max_snapshots)
        self._cache     = GatewaySnapshotCache(max_size=max_cache_size)
        self._history   = GatewaySnapshotHistory(
            max_snapshots=max_history, max_events=max_history
        )
        self._stats     = GatewaySnapshotStatistics()
        self._validator = GatewaySnapshotValidator()
        self._listeners: List[Callable[[SnapshotEvent], None]] = []

        # per-execution version counter
        self._version_counters: Dict[str, int] = {}

        self._lock = threading.RLock()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        self._registry.start()
        _audit.log_lifecycle_event(
            SNAPSHOT_STORE_SYSTEM_ID,
            EngineState.STOPPED,
            EngineState.RUNNING,
            VERSION,
        )
        _log.info("GatewaySnapshotStore started.", version=VERSION)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            SNAPSHOT_STORE_SYSTEM_ID,
            EngineState.RUNNING,
            EngineState.STOPPED,
            VERSION,
        )
        self._registry.stop()
        _log.info(
            "GatewaySnapshotStore stopped.",
            published=self._stats.snapshots_published,
        )

    # ── Core operations ───────────────────────────────────────────────────────

    def publish(self, snapshot: ExecutionGatewaySnapshot) -> None:
        """
        Validate, store, and publish a snapshot.

        Raises SnapshotStoreNotRunningError  — if not RUNNING.
        Raises SnapshotValidationError       — if snapshot fails validation.
        Raises DuplicateSnapshotError        — if snapshot_id already stored.
        Raises SnapshotStoreCapacityError    — if store is full.
        """
        if self.lifecycle_state() != EngineState.RUNNING:
            raise SnapshotStoreNotRunningError()

        # Step 1 — fire CREATED
        self._fire(make_snapshot_created_event(
            snapshot.snapshot_id,
            execution_id=snapshot.execution_id,
            gateway_id=snapshot.gateway_id,
        ))

        # Step 2 — validate
        result = self._validator.validate_snapshot(snapshot)
        if not result.is_valid:
            with self._lock:
                self._stats.record_validation_failure()
            raise SnapshotValidationError(
                f"Snapshot '{snapshot.snapshot_id}' failed validation.",
                errors=result.errors,
            )
        with self._lock:
            self._stats.record_validation_success()

        self._fire(make_snapshot_validated_event(
            snapshot.snapshot_id,
            execution_id=snapshot.execution_id,
            gateway_id=snapshot.gateway_id,
        ))

        # Step 3 — store in registry
        self._registry.store(snapshot)

        # Step 4 — cache + CACHED event
        self._cache.put(snapshot)
        self._fire(make_snapshot_cached_event(
            snapshot.snapshot_id,
            execution_id=snapshot.execution_id,
            gateway_id=snapshot.gateway_id,
        ))

        # Step 5 — history
        self._history.append(snapshot)

        # Step 6 — statistics
        with self._lock:
            self._stats.record_published()
            self._stats.record_size(snapshot.estimated_size_bytes)

        # Step 7 — PUBLISHED event
        self._fire(make_snapshot_published_event(
            snapshot.snapshot_id,
            execution_id=snapshot.execution_id,
            gateway_id=snapshot.gateway_id,
        ))

        _log.debug(
            "Snapshot published.",
            snapshot_id=snapshot.snapshot_id,
            gateway_state=snapshot.gateway_state.value,
        )

    def get(self, snapshot_id: str) -> ExecutionGatewaySnapshot:
        """
        Retrieve a snapshot by ID.

        Checks cache first; falls back to registry.
        Fires SNAPSHOT_RETRIEVED and updates statistics.

        Raises SnapshotNotFoundError — if not found.
        """
        # Check cache
        cached = self._cache.get(snapshot_id)
        if cached is not None:
            with self._lock:
                self._stats.record_retrieved()
            self._fire(make_snapshot_retrieved_event(
                snapshot_id,
                execution_id=cached.execution_id,
                gateway_id=cached.gateway_id,
            ))
            return cached

        # Fall back to registry
        snapshot = self._registry.get(snapshot_id)   # raises SnapshotNotFoundError
        self._cache.put(snapshot)

        with self._lock:
            self._stats.record_retrieved()
        self._fire(make_snapshot_retrieved_event(
            snapshot_id,
            execution_id=snapshot.execution_id,
            gateway_id=snapshot.gateway_id,
        ))
        return snapshot

    def archive(self, snapshot_id: str) -> None:
        """
        Mark a snapshot as archived.

        Raises SnapshotStoreNotRunningError — if not RUNNING.
        Raises SnapshotNotFoundError        — if not found.
        """
        if self.lifecycle_state() != EngineState.RUNNING:
            raise SnapshotStoreNotRunningError()

        snapshot = self._registry.get(snapshot_id)  # raises if not found
        self._registry.archive(snapshot_id)

        with self._lock:
            self._stats.record_archived()

        self._fire(make_snapshot_archived_event(
            snapshot_id,
            execution_id=snapshot.execution_id,
            gateway_id=snapshot.gateway_id,
        ))

    # ── Version tracking ──────────────────────────────────────────────────────

    def next_version_for(self, execution_id: str) -> int:
        """Return the next snapshot_version number for execution_id."""
        with self._lock:
            v = self._version_counters.get(execution_id, 0) + 1
            self._version_counters[execution_id] = v
            return v

    # ── Query methods ─────────────────────────────────────────────────────────

    def latest(self) -> Optional[ExecutionGatewaySnapshot]:
        return self._registry.latest()

    def latest_for_execution(
        self, execution_id: str
    ) -> Optional[ExecutionGatewaySnapshot]:
        return self._registry.latest_for_execution(execution_id)

    def by_execution_id(self, execution_id: str) -> List[ExecutionGatewaySnapshot]:
        return self._registry.by_execution_id(execution_id)

    def by_order_id(self, order_id: str) -> List[ExecutionGatewaySnapshot]:
        return self._registry.by_order_id(order_id)

    def by_position_id(self, position_id: str) -> List[ExecutionGatewaySnapshot]:
        return self._registry.by_position_id(position_id)

    def by_portfolio_id(self, portfolio_id: str) -> List[ExecutionGatewaySnapshot]:
        return self._registry.by_portfolio_id(portfolio_id)

    def by_workflow_id(self, workflow_id: str) -> List[ExecutionGatewaySnapshot]:
        return self._registry.by_workflow_id(workflow_id)

    def by_strategy_id(self, strategy_id: str) -> List[ExecutionGatewaySnapshot]:
        return self._registry.by_strategy_id(strategy_id)

    def by_gateway_id(self, gateway_id: str) -> List[ExecutionGatewaySnapshot]:
        return self._registry.by_gateway_id(gateway_id)

    def by_broker_id(self, broker_id: str) -> List[ExecutionGatewaySnapshot]:
        return self._registry.by_broker_id(broker_id)

    def by_gateway_state(self, state_value: str) -> List[ExecutionGatewaySnapshot]:
        return self._registry.by_gateway_state(state_value)

    def is_archived(self, snapshot_id: str) -> bool:
        return self._registry.is_archived(snapshot_id)

    # ── Event listeners ───────────────────────────────────────────────────────

    def add_event_listener(
        self, listener: Callable[[SnapshotEvent], None]
    ) -> None:
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_event_listener(
        self, listener: Callable[[SnapshotEvent], None]
    ) -> None:
        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)

    def _fire(self, event: SnapshotEvent) -> None:
        self._history.append_event(event)
        with self._lock:
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception:
                _log.exception(
                    "Event listener raised.", event_type=event.event_type.value
                )

    # ── Observability ─────────────────────────────────────────────────────────

    def statistics(self) -> GatewaySnapshotStatistics:
        with self._lock:
            return self._stats.copy()

    def history(self) -> GatewaySnapshotHistory:
        return self._history

    def snapshot_count(self) -> int:
        return self._registry.snapshot_count

    def snapshot(self) -> Dict[str, Any]:
        """Return a dict summary of the store's current state."""
        return {
            "system_id":       SNAPSHOT_STORE_SYSTEM_ID,
            "version":         VERSION,
            "lifecycle_state": self.lifecycle_state().value,
            "snapshot_count":  self._registry.snapshot_count,
            "archived_count":  self._registry.archived_count,
            "cache_size":      self._cache.size,
            "history_count":   self._history.snapshot_count,
            "statistics":      self._stats.to_dict(),
        }
