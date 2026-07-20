"""
iios/execution/analytics/snapshot/analytics_snapshot_store.py
=============================================================
AnalyticsSnapshotStore — primary store for ExecutionAnalyticsSnapshot
objects.

Provides:
  - CRUD operations
  - Version history per analytics session
  - Latest snapshot lookup
  - Full query support:
    By Snapshot ID, Analytics Session ID, Execution Session ID,
    Workflow ID, Portfolio ID, Strategy ID, Analytics Status,
    Operational Health, Timestamp, Latest, Historical Versions

C8 Execution Analytics & Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import collections
import threading
import time
from typing import Dict, List, Optional, Tuple

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .analytics_snapshot_cache import AnalyticsSnapshotCache
from .analytics_snapshot_events import (
    make_snapshot_archived_event,
    make_snapshot_published_event,
    make_snapshot_retrieved_event,
)
from .analytics_snapshot_history import AnalyticsSnapshotHistory
from .analytics_snapshot_statistics import AnalyticsSnapshotStatistics
from .constants import (
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SNAPSHOTS,
    STORE_SYSTEM_ID,
    AnalyticsStatus,
    SnapshotLifecycleState,
)
from .exceptions import SnapshotEngineNotRunningError, SnapshotNotFoundError
from .execution_analytics_snapshot import ExecutionAnalyticsSnapshot

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class AnalyticsSnapshotStore(LifecycleAwareMixin):
    """
    Thread-safe primary store for ExecutionAnalyticsSnapshot objects.

    Combines:
      - In-memory index for fast lookups
      - Per-session version history (via AnalyticsSnapshotHistory)
      - LRU cache (via AnalyticsSnapshotCache)
      - Statistics tracking
      - Event emission

    Must be started before use.
    """

    def __init__(
        self,
        max_snapshots: int = DEFAULT_MAX_SNAPSHOTS,
        max_history:   int = DEFAULT_MAX_HISTORY,
    ) -> None:
        super().__init__()
        self._max_snapshots = max_snapshots
        self._lock          = threading.RLock()

        # Primary store: snapshot_id → snapshot
        self._store: Dict[str, ExecutionAnalyticsSnapshot] = {}
        # Insertion order for LRU eviction when at capacity
        self._insertion_order: List[str] = []

        # Sub-components
        self._history  = AnalyticsSnapshotHistory(maxlen=max_history)
        self._cache    = AnalyticsSnapshotCache()
        self._stats    = AnalyticsSnapshotStatistics()

        # All events produced by the store
        self._events: collections.deque = collections.deque(maxlen=max_history)

    def _on_start(self) -> None:
        self._cache.start()
        _log.info("AnalyticsSnapshotStore started.", system_id=STORE_SYSTEM_ID)

    def _on_stop(self) -> None:
        try:
            self._cache.stop()
        except Exception:
            pass
        _log.info("AnalyticsSnapshotStore stopped.", system_id=STORE_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise SnapshotEngineNotRunningError()

    # ── Write operations ──────────────────────────────────────────────────────

    def save(self, snapshot: ExecutionAnalyticsSnapshot) -> None:
        """
        Persist a snapshot.

        If a snapshot with the same ID already exists it is replaced.
        Old snapshots are evicted when the store is at capacity.
        """
        self._assert_running()
        t0 = time.perf_counter()
        with self._lock:
            sid = snapshot.snapshot_id
            if sid not in self._store:
                if len(self._store) >= self._max_snapshots:
                    oldest = self._insertion_order.pop(0)
                    del self._store[oldest]
                self._insertion_order.append(sid)
            self._store[sid] = snapshot

        # Update supporting structures (outside main lock)
        self._history.add(snapshot)
        self._cache.put(snapshot)

        # Statistics
        build_ms = (time.perf_counter() - t0) * 1_000.0
        size_bytes = len(snapshot.to_json())
        self._stats.record_created(build_ms)
        self._stats.record_size(size_bytes)

        # Created event
        from .analytics_snapshot_events import make_snapshot_created_event
        ev = make_snapshot_created_event(
            snapshot.snapshot_id,
            snapshot.analytics_session_id,
        )
        with self._lock:
            self._events.append(ev)

    def publish(self, snapshot_id: str) -> ExecutionAnalyticsSnapshot:
        """
        Mark a snapshot as PUBLISHED.

        Returns the updated snapshot (new immutable object with
        lifecycle_state = PUBLISHED).
        """
        self._assert_running()
        snap = self.get_by_id(snapshot_id)
        # Re-create with updated state
        updated = ExecutionAnalyticsSnapshot(
            snapshot_id          = snap.snapshot_id,
            snapshot_version     = snap.snapshot_version,
            analytics_session_id = snap.analytics_session_id,
            execution_session_id = snap.execution_session_id,
            workflow_id          = snap.workflow_id,
            portfolio_id         = snap.portfolio_id,
            strategy_id          = snap.strategy_id,
            analytics_scope      = snap.analytics_scope,
            analytics_mode       = snap.analytics_mode,
            lifecycle_state      = SnapshotLifecycleState.PUBLISHED,
            analytics_status     = snap.analytics_status,
            analytics_health     = snap.analytics_health,
            performance_summary  = snap.performance_summary,
            performance_kpis     = snap.performance_kpis,
            performance_scorecard= snap.performance_scorecard,
            trend_summary        = snap.trend_summary,
            benchmark_summary    = snap.benchmark_summary,
            historical_summary   = snap.historical_summary,
            prediction_summary   = snap.prediction_summary,
            forecast_summary     = snap.forecast_summary,
            confidence_summary   = snap.confidence_summary,
            operational_health_score = snap.operational_health_score,
            capacity_forecast    = snap.capacity_forecast,
            risk_forecast        = snap.risk_forecast,
            analytics_statistics = snap.analytics_statistics,
            analytics_metadata   = snap.analytics_metadata,
            audit_metadata       = snap.audit_metadata,
            framework_version    = snap.framework_version,
            timestamp            = snap.timestamp,
        )
        self.save(updated)
        self._stats.record_published()
        ev = make_snapshot_published_event(snapshot_id)
        with self._lock:
            self._events.append(ev)
        return updated

    def archive(self, snapshot_id: str, reason: str = "") -> None:
        """Archive a snapshot (marks it as ARCHIVED)."""
        self._assert_running()
        snap = self.get_by_id(snapshot_id)
        updated = ExecutionAnalyticsSnapshot(
            snapshot_id          = snap.snapshot_id,
            snapshot_version     = snap.snapshot_version,
            analytics_session_id = snap.analytics_session_id,
            execution_session_id = snap.execution_session_id,
            workflow_id          = snap.workflow_id,
            portfolio_id         = snap.portfolio_id,
            strategy_id          = snap.strategy_id,
            analytics_scope      = snap.analytics_scope,
            analytics_mode       = snap.analytics_mode,
            lifecycle_state      = SnapshotLifecycleState.ARCHIVED,
            analytics_status     = snap.analytics_status,
            analytics_health     = snap.analytics_health,
            performance_summary  = snap.performance_summary,
            performance_kpis     = snap.performance_kpis,
            performance_scorecard= snap.performance_scorecard,
            trend_summary        = snap.trend_summary,
            benchmark_summary    = snap.benchmark_summary,
            historical_summary   = snap.historical_summary,
            prediction_summary   = snap.prediction_summary,
            forecast_summary     = snap.forecast_summary,
            confidence_summary   = snap.confidence_summary,
            operational_health_score = snap.operational_health_score,
            capacity_forecast    = snap.capacity_forecast,
            risk_forecast        = snap.risk_forecast,
            analytics_statistics = snap.analytics_statistics,
            analytics_metadata   = snap.analytics_metadata,
            audit_metadata       = snap.audit_metadata,
            framework_version    = snap.framework_version,
            timestamp            = snap.timestamp,
        )
        self.save(updated)
        self._stats.record_archived()
        ev = make_snapshot_archived_event(snapshot_id, reason)
        with self._lock:
            self._events.append(ev)

    # ── Query operations ──────────────────────────────────────────────────────

    def get_by_id(self, snapshot_id: str) -> ExecutionAnalyticsSnapshot:
        """Retrieve by snapshot_id; raise SnapshotNotFoundError if absent."""
        self._assert_running()
        cached = self._cache.get(snapshot_id)
        if cached is not None:
            ev = make_snapshot_retrieved_event(snapshot_id)
            with self._lock:
                self._events.append(ev)
            return cached
        with self._lock:
            snap = self._store.get(snapshot_id)
        if snap is None:
            raise SnapshotNotFoundError(snapshot_id)
        self._cache.put(snap)
        ev = make_snapshot_retrieved_event(snapshot_id)
        with self._lock:
            self._events.append(ev)
        return snap

    def get_by_analytics_session(
        self, session_id: str
    ) -> List[ExecutionAnalyticsSnapshot]:
        """Return all snapshots for an analytics session, oldest first."""
        self._assert_running()
        return self._history.by_session(session_id)

    def get_by_execution_session(
        self, exec_id: str
    ) -> List[ExecutionAnalyticsSnapshot]:
        """Return all snapshots for an execution session, oldest first."""
        self._assert_running()
        return self._history.by_execution_session(exec_id)

    def get_by_workflow(self, workflow_id: str) -> List[ExecutionAnalyticsSnapshot]:
        """Return all snapshots for a workflow."""
        self._assert_running()
        return self._history.by_workflow(workflow_id)

    def get_by_portfolio(self, portfolio_id: str) -> List[ExecutionAnalyticsSnapshot]:
        """Return all snapshots for a portfolio."""
        self._assert_running()
        return self._history.by_portfolio(portfolio_id)

    def get_by_strategy(self, strategy_id: str) -> List[ExecutionAnalyticsSnapshot]:
        """Return all snapshots for a strategy."""
        self._assert_running()
        return self._history.by_strategy(strategy_id)

    def get_by_status(
        self, status: AnalyticsStatus
    ) -> List[ExecutionAnalyticsSnapshot]:
        """Return all snapshots with a given analytics status."""
        self._assert_running()
        with self._lock:
            return [s for s in self._store.values() if s.analytics_status == status]

    def get_by_health(
        self, min_score: float
    ) -> List[ExecutionAnalyticsSnapshot]:
        """Return all snapshots where operational_health_score >= min_score."""
        self._assert_running()
        with self._lock:
            return [
                s for s in self._store.values()
                if s.operational_health_score >= min_score
            ]

    def get_by_timestamp_range(
        self, from_ts: float, to_ts: float
    ) -> List[ExecutionAnalyticsSnapshot]:
        """Return snapshots with timestamp in [from_ts, to_ts]."""
        self._assert_running()
        with self._lock:
            return [
                s for s in self._store.values()
                if from_ts <= s.timestamp <= to_ts
            ]

    def get_latest(self) -> Optional[ExecutionAnalyticsSnapshot]:
        """Return the most recently saved snapshot (by timestamp)."""
        self._assert_running()
        items = self._history.recent(1)
        return items[-1] if items else None

    def get_latest_for_session(
        self, session_id: str
    ) -> Optional[ExecutionAnalyticsSnapshot]:
        """Return the most recent snapshot for an analytics session."""
        self._assert_running()
        return self._history.latest_for_session(session_id)

    def historical_versions(
        self, session_id: str
    ) -> List[ExecutionAnalyticsSnapshot]:
        """Return all historical versions for a session, ordered by timestamp."""
        self._assert_running()
        return sorted(
            self._history.by_session(session_id),
            key=lambda s: s.timestamp,
        )

    def list_all(self) -> List[ExecutionAnalyticsSnapshot]:
        """Return all stored snapshots."""
        self._assert_running()
        with self._lock:
            return list(self._store.values())

    # ── Observability ─────────────────────────────────────────────────────────

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._store)

    @property
    def statistics(self) -> AnalyticsSnapshotStatistics:
        return self._stats

    @property
    def history(self) -> AnalyticsSnapshotHistory:
        return self._history

    @property
    def cache(self) -> AnalyticsSnapshotCache:
        return self._cache

    def recent_events(self, n: int = 20) -> List:
        with self._lock:
            items = list(self._events)
        return items[-n:] if n > 0 else items

    def clear(self) -> None:
        """Remove all snapshots from the store (does not reset statistics)."""
        with self._lock:
            self._store.clear()
            self._insertion_order.clear()
        self._history.clear()
        self._cache.clear()
