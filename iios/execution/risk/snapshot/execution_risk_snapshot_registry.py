"""iios/execution/risk/snapshot/execution_risk_snapshot_registry.py
==================================================
SnapshotRegistry — LifecycleAwareMixin coordinator for the snapshot
subsystem.

Owns:
  • SnapshotStore   — primary multi-index persistent store
  • SnapshotCache   — bounded LRU fast lookup
  • SnapshotHistory — per risk_id version list
  • SnapshotStatistics — runtime metrics
  • List[SnapshotEvent] — event log

C6 Execution Intelligence — Phase 4, Module 5
"""
from __future__ import annotations

import threading
import time
from typing import Dict, List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from .constants import (
    DEFAULT_MAX_CACHE_SIZE,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_STORE_SIZE,
    REGISTRY_SYSTEM_ID,
    VERSION,
    SnapshotStatus,
)
from .exceptions import (
    DuplicateSnapshotError,
    SnapshotNotFoundError,
    SnapshotRegistryNotRunningError,
)
from .execution_risk_snapshot import ExecutionRiskSnapshot
from .execution_risk_snapshot_cache import SnapshotCache
from .execution_risk_snapshot_events import (
    SnapshotEvent,
    make_snapshot_archived_event,
    make_snapshot_cached_event,
    make_snapshot_created_event,
    make_snapshot_published_event,
    make_snapshot_retrieved_event,
)
from .execution_risk_snapshot_history import SnapshotHistory
from .execution_risk_snapshot_statistics import SnapshotStatistics
from .execution_risk_snapshot_store import SnapshotStore
from .execution_risk_snapshot_validation import SnapshotValidator

_log   = get_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)


class SnapshotRegistry(LifecycleAwareMixin):
    """
    Central coordinator for ExecutionRiskSnapshot lifecycle.

    The registry MUST be started before any write operations.
    Read operations are permitted regardless of lifecycle state.

    Thread-safety:
      All public write operations acquire the internal lock.
      Store, Cache, and History are independently thread-safe.
    """

    SYSTEM_ID = REGISTRY_SYSTEM_ID
    VERSION   = VERSION

    def __init__(
        self,
        max_store_size:  int = DEFAULT_MAX_STORE_SIZE,
        max_cache_size:  int = DEFAULT_MAX_CACHE_SIZE,
        max_history:     int = DEFAULT_MAX_HISTORY,
    ) -> None:
        super().__init__()
        self._store    = SnapshotStore(max_size=max_store_size)
        self._cache    = SnapshotCache(max_size=max_cache_size)
        self._history  = SnapshotHistory(max_versions_per_risk=max_history)
        self._stats    = SnapshotStatistics()
        self._events:  List[SnapshotEvent] = []
        self._lock     = threading.RLock()

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise SnapshotRegistryNotRunningError()

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(
            REGISTRY_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        _log.info("SnapshotRegistry started.")

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            REGISTRY_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        _log.info(
            "SnapshotRegistry stopped.",
            snapshot_count=self._store.count,
        )

    @property
    def is_running(self) -> bool:
        return self.lifecycle_state() == EngineState.RUNNING

    # ── Write ─────────────────────────────────────────────────────────────────

    def register(self, snapshot: ExecutionRiskSnapshot) -> ExecutionRiskSnapshot:
        """
        Register a new snapshot.

        Steps:
          1. assert running
          2. validate no duplicate
          3. put in store
          4. put in cache
          5. update history
          6. emit SNAPSHOT_CREATED event
          7. record stats

        Returns the registered snapshot.
        """
        self._assert_running()

        start_ts = time.perf_counter()

        with self._lock:
            if self._store.contains(snapshot.snapshot_id):
                raise DuplicateSnapshotError(snapshot.snapshot_id)

            # Optional: validate snapshot before storing
            val = SnapshotValidator.validate_snapshot(snapshot)
            if val.is_valid:
                self._stats.record_validation_success()
            else:
                self._stats.record_validation_failure()
                _log.warning(
                    "Registering snapshot with validation warnings.",
                    snapshot_id=snapshot.snapshot_id,
                    errors=val.errors,
                )

            self._store.put(snapshot)
            self._cache.put(snapshot)
            self._history.append(snapshot)

            elapsed_ms = (time.perf_counter() - start_ts) * 1_000
            self._stats.record_created(elapsed_ms=elapsed_ms)
            self._stats.record_cached()

            event = make_snapshot_created_event(
                snapshot.snapshot_id,
                snapshot.risk_id,
                evaluation_id=snapshot.risk_id,
            )
            self._events.append(event)

        _log.info(
            "Snapshot registered.",
            snapshot_id=snapshot.snapshot_id,
            risk_id=snapshot.risk_id,
            final_action=snapshot.final_action,
        )
        return snapshot

    def publish(self, snapshot_id: str, published_by: str = "") -> ExecutionRiskSnapshot:
        """
        Mark snapshot as PUBLISHED and update audit metadata.

        Returns the updated snapshot.
        """
        self._assert_running()
        with self._lock:
            existing = self._store.require(snapshot_id)

            if existing.status in (SnapshotStatus.ARCHIVED, SnapshotStatus.INVALID):
                raise SnapshotNotFoundError(
                    f"Cannot publish snapshot in terminal state '{existing.status.value}'"
                )

            updated = existing.with_published_audit(published_by=published_by)
            # Replace in store
            self._store.remove(snapshot_id)
            self._store.put(updated)
            # Refresh cache
            self._cache.evict(snapshot_id)
            self._cache.put(updated)

            self._stats.record_published()

            event = make_snapshot_published_event(
                snapshot_id, updated.risk_id, actor=published_by or "registry"
            )
            self._events.append(event)

        _log.info("Snapshot published.", snapshot_id=snapshot_id)
        return updated

    def archive(self, snapshot_id: str, archived_by: str = "") -> ExecutionRiskSnapshot:
        """
        Mark snapshot as ARCHIVED and update audit metadata.

        Returns the updated snapshot.
        """
        self._assert_running()
        with self._lock:
            existing = self._store.require(snapshot_id)

            if existing.status == SnapshotStatus.ARCHIVED:
                return existing  # idempotent

            updated = existing.with_archived_audit(archived_by=archived_by)
            # Replace in store
            self._store.remove(snapshot_id)
            self._store.put(updated)
            # Evict from cache (archived snapshots are not actively retrieved)
            self._cache.evict(snapshot_id)

            self._stats.record_archived()

            event = make_snapshot_archived_event(
                snapshot_id, updated.risk_id, actor=archived_by or "registry"
            )
            self._events.append(event)

        _log.info("Snapshot archived.", snapshot_id=snapshot_id)
        return updated

    # ── Read ──────────────────────────────────────────────────────────────────

    def get(self, snapshot_id: str) -> Optional[ExecutionRiskSnapshot]:
        """Cache-first lookup.  Returns None if not found."""
        # Try cache first
        cached = self._cache.get(snapshot_id)
        if cached is not None:
            with self._lock:
                self._stats.record_cache_hit()
                event = make_snapshot_retrieved_event(snapshot_id, cached.risk_id)
                self._events.append(event)
            return cached

        # Fall back to store
        with self._lock:
            self._stats.record_cache_miss()
            s = self._store.get(snapshot_id)
            if s is not None:
                self._cache.put(s)
                self._stats.record_cached()
                event = make_snapshot_retrieved_event(snapshot_id, s.risk_id)
                self._events.append(event)
            return s

    def require(self, snapshot_id: str) -> ExecutionRiskSnapshot:
        """Cache-first lookup.  Raises SnapshotNotFoundError if not found."""
        s = self.get(snapshot_id)
        if s is None:
            raise SnapshotNotFoundError(snapshot_id)
        return s

    # ── Query methods ─────────────────────────────────────────────────────────

    def get_by_risk_id(self, risk_id: str) -> List[ExecutionRiskSnapshot]:
        return self._store.get_by_risk_id(risk_id)

    def get_by_execution_id(self, execution_id: str) -> List[ExecutionRiskSnapshot]:
        return self._store.get_by_execution_id(execution_id)

    def get_by_order_id(self, order_id: str) -> List[ExecutionRiskSnapshot]:
        return self._store.get_by_order_id(order_id)

    def get_by_position_id(self, position_id: str) -> List[ExecutionRiskSnapshot]:
        return self._store.get_by_position_id(position_id)

    def get_by_portfolio_id(self, portfolio_id: str) -> List[ExecutionRiskSnapshot]:
        return self._store.get_by_portfolio_id(portfolio_id)

    def get_by_workflow_id(self, workflow_id: str) -> List[ExecutionRiskSnapshot]:
        return self._store.get_by_workflow_id(workflow_id)

    def get_by_strategy_id(self, strategy_id: str) -> List[ExecutionRiskSnapshot]:
        return self._store.get_by_strategy_id(strategy_id)

    def latest(self, n: int = 10) -> List[ExecutionRiskSnapshot]:
        """Return the *n* most-recently inserted snapshots."""
        return self._store.latest(n)

    def history_for_risk_id(self, risk_id: str) -> List[ExecutionRiskSnapshot]:
        """Return all snapshot versions for *risk_id* in insertion order."""
        return self._history.versions(risk_id)

    def latest_for_risk_id(self, risk_id: str) -> Optional[ExecutionRiskSnapshot]:
        """Return the most recent snapshot for *risk_id*, or None."""
        return self._history.latest(risk_id)

    def all(self) -> List[ExecutionRiskSnapshot]:
        return self._store.all()

    # ── Statistics / events ───────────────────────────────────────────────────

    def statistics(self) -> SnapshotStatistics:
        """Return a copy of current statistics."""
        with self._lock:
            return self._stats.copy()

    def events(self) -> List[SnapshotEvent]:
        """Return a copy of the event log."""
        with self._lock:
            return list(self._events)

    @property
    def snapshot_count(self) -> int:
        return self._store.count

    @property
    def cache_size(self) -> int:
        return self._cache.size
