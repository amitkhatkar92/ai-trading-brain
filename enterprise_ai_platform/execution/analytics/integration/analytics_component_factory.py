"""
analytics_component_factory.py — enterprise_ai_platform.execution.analytics.integration
=======================================================================
Factory that instantiates M1-M5 analytics components.

Each ``create_*`` method returns a fresh, *un-started* instance of the
corresponding component.  The :class:`AnalyticsComponentRegistry` is
responsible for starting and stopping them.
"""
from __future__ import annotations

from enterprise_ai_platform.execution.analytics.lifecycle import AnalyticsLifecycle
from enterprise_ai_platform.execution.analytics.engine import ExecutionAnalyticsEngine
from enterprise_ai_platform.execution.analytics.performance import PerformanceAnalyticsEngine
from enterprise_ai_platform.execution.analytics.predictive import PredictiveIntelligenceEngine
from enterprise_ai_platform.execution.analytics.snapshot import (
    AnalyticsSnapshotFactory,
    AnalyticsSnapshotStore,
)
from enterprise_ai_platform.common.logging.logging_manager import get_logger

_log = get_logger(__name__)


class AnalyticsComponentFactory:
    """
    Factory for M1-M5 analytics component instances.

    All ``create_*`` methods return new, un-started instances.  They are
    intentionally thin wrappers so that downstream tests can subclass the
    factory and override individual creators.
    """

    # ------------------------------------------------------------------
    # M1 — Analytics Lifecycle
    # ------------------------------------------------------------------
    def create_lifecycle(self) -> AnalyticsLifecycle:
        """
        Return a new un-started :class:`~enterprise_ai_platform.execution.analytics.lifecycle.AnalyticsLifecycle`.
        """
        _log.debug("AnalyticsComponentFactory: creating M1 AnalyticsLifecycle")
        return AnalyticsLifecycle()

    # ------------------------------------------------------------------
    # M2 — Analytics Engine
    # ------------------------------------------------------------------
    def create_engine(self) -> ExecutionAnalyticsEngine:
        """
        Return a new un-started :class:`~enterprise_ai_platform.execution.analytics.engine.ExecutionAnalyticsEngine`.
        """
        _log.debug("AnalyticsComponentFactory: creating M2 ExecutionAnalyticsEngine")
        return ExecutionAnalyticsEngine()

    # ------------------------------------------------------------------
    # M3 — Performance Analytics
    # ------------------------------------------------------------------
    def create_performance(self) -> PerformanceAnalyticsEngine:
        """
        Return a new un-started :class:`~enterprise_ai_platform.execution.analytics.performance.PerformanceAnalyticsEngine`.
        """
        _log.debug("AnalyticsComponentFactory: creating M3 PerformanceAnalyticsEngine")
        return PerformanceAnalyticsEngine()

    # ------------------------------------------------------------------
    # M4 — Predictive Intelligence
    # ------------------------------------------------------------------
    def create_predictive(self) -> PredictiveIntelligenceEngine:
        """
        Return a new un-started :class:`~enterprise_ai_platform.execution.analytics.predictive.PredictiveIntelligenceEngine`.
        """
        _log.debug("AnalyticsComponentFactory: creating M4 PredictiveIntelligenceEngine")
        return PredictiveIntelligenceEngine()

    # ------------------------------------------------------------------
    # M5 — Snapshot Store + Factory
    # ------------------------------------------------------------------
    def create_snapshot_store(self) -> AnalyticsSnapshotStore:
        """
        Return a new un-started :class:`~enterprise_ai_platform.execution.analytics.snapshot.AnalyticsSnapshotStore`.
        """
        _log.debug("AnalyticsComponentFactory: creating M5 AnalyticsSnapshotStore")
        return AnalyticsSnapshotStore()

    def create_snapshot_factory(
        self,
        store: AnalyticsSnapshotStore,
    ) -> AnalyticsSnapshotFactory:
        """
        Return a new un-started :class:`~enterprise_ai_platform.execution.analytics.snapshot.AnalyticsSnapshotFactory`
        wired to *store*.

        The factory does NOT start *store* — the caller must ensure *store*
        is already started before the factory is started.
        """
        _log.debug("AnalyticsComponentFactory: creating M5 AnalyticsSnapshotFactory")
        return AnalyticsSnapshotFactory(store=store)
