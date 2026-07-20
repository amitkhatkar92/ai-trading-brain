"""
iios/execution/analytics/snapshot/analytics_snapshot_factory.py
===============================================================
AnalyticsSnapshotFactory — convenience factory for building and
managing ExecutionAnalyticsSnapshot objects.

C8 Execution Analytics & Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

from typing import Any, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .analytics_snapshot_builder import AnalyticsSnapshotBuilder
from .analytics_snapshot_statistics import AnalyticsSnapshotStatistics
from .analytics_snapshot_store import AnalyticsSnapshotStore
from .analytics_snapshot_validation import AnalyticsSnapshotValidator
from .constants import (
    FACTORY_SYSTEM_ID,
    AnalyticsMode,
    AnalyticsScope,
    AnalyticsStatus,
)
from .exceptions import SnapshotEngineNotRunningError
from .execution_analytics_snapshot import ExecutionAnalyticsSnapshot

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class AnalyticsSnapshotFactory(LifecycleAwareMixin):
    """
    Convenience factory: builds, validates, stores, and publishes
    ExecutionAnalyticsSnapshot objects in a single call.

    Must be started before use.
    """

    def __init__(self, store: Optional[AnalyticsSnapshotStore] = None) -> None:
        super().__init__()
        self._builder   = AnalyticsSnapshotBuilder()
        self._validator = AnalyticsSnapshotValidator()
        self._stats     = AnalyticsSnapshotStatistics()
        self._store     = store

    def _on_start(self) -> None:
        self._builder.start()
        if self._store is not None and self._store.lifecycle_state() not in _RUNNING:
            self._store.start()
        _log.info("AnalyticsSnapshotFactory started.", system_id=FACTORY_SYSTEM_ID)

    def _on_stop(self) -> None:
        try:
            self._builder.stop()
        except Exception:
            pass
        _log.info("AnalyticsSnapshotFactory stopped.", system_id=FACTORY_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise SnapshotEngineNotRunningError()

    # ── Factory methods ───────────────────────────────────────────────────────

    def create(
        self,
        *,
        analytics_session:    Optional[Any] = None,
        analytics_statistics: Optional[Any] = None,
        engine_snapshot:      Optional[Any] = None,
        engine_statistics:    Optional[Any] = None,
        performance_report:   Optional[Any] = None,
        performance_stats:    Optional[Any] = None,
        prediction_report:    Optional[Any] = None,
        predictive_stats:     Optional[Any] = None,
        analytics_session_id: str           = "",
        execution_session_id: str           = "",
        workflow_id:          str           = "",
        portfolio_id:         str           = "",
        strategy_id:          str           = "",
        analytics_scope:      Optional[AnalyticsScope] = None,
        analytics_mode:       Optional[AnalyticsMode]  = None,
        analytics_status:     Optional[AnalyticsStatus] = None,
        snapshot_id:          Optional[str] = None,
        validate:             bool          = True,
        publish:              bool          = False,
    ) -> ExecutionAnalyticsSnapshot:
        """
        Build, optionally validate, and optionally store+publish a snapshot.

        Parameters
        ----------
        validate: Run full validation after building (default True).
        publish:  If True and a store is attached, save and publish the snapshot.
        """
        self._assert_running()

        snapshot = self._builder.build(
            analytics_session    = analytics_session,
            analytics_statistics = analytics_statistics,
            engine_snapshot      = engine_snapshot,
            engine_statistics    = engine_statistics,
            performance_report   = performance_report,
            performance_stats    = performance_stats,
            prediction_report    = prediction_report,
            predictive_stats     = predictive_stats,
            analytics_session_id = analytics_session_id,
            execution_session_id = execution_session_id,
            workflow_id          = workflow_id,
            portfolio_id         = portfolio_id,
            strategy_id          = strategy_id,
            analytics_scope      = analytics_scope,
            analytics_mode       = analytics_mode,
            analytics_status     = analytics_status,
            snapshot_id          = snapshot_id,
        )

        if validate:
            result = self._validator.validate(snapshot)
            if result.is_valid:
                self._stats.record_validation_success()
            else:
                self._stats.record_validation_failure()
                # Non-fatal — return snapshot but do not publish
                return snapshot

        if publish and self._store is not None:
            self._store.save(snapshot)
            self._store.publish(snapshot.snapshot_id)

        return snapshot

    def create_minimal(
        self,
        *,
        analytics_session_id: str,
        execution_session_id: str,
        workflow_id:          str           = "",
        portfolio_id:         str           = "",
        strategy_id:          str           = "",
    ) -> ExecutionAnalyticsSnapshot:
        """Build the smallest possible valid snapshot (no M3/M4 data)."""
        self._assert_running()
        return self.create(
            analytics_session_id = analytics_session_id,
            execution_session_id = execution_session_id,
            workflow_id          = workflow_id,
            portfolio_id         = portfolio_id,
            strategy_id          = strategy_id,
        )

    # ── Observability ─────────────────────────────────────────────────────────

    @property
    def statistics(self) -> AnalyticsSnapshotStatistics:
        return self._stats

    @property
    def store(self) -> Optional[AnalyticsSnapshotStore]:
        return self._store

    @property
    def builder(self) -> AnalyticsSnapshotBuilder:
        return self._builder
