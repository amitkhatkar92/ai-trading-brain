"""
iios/execution/analytics/performance/performance_analytics_engine.py
====================================================================
PerformanceAnalyticsEngine — primary public interface for the
Institutional Performance Analytics Framework (C8 M3).

This is the ONLY public entry point for external callers.

Responsibilities:
  - Accept and process PerformanceRequest objects (or str request_ids
    for M2 dispatcher compatibility)
  - Delegate the full analytics cycle to PerformanceManager
  - Provide focused convenience methods for individual analytics tasks
  - Expose statistics and history for observability

NO predictive forecasting.  NO alerts.  NO trade execution.

C8 Execution Analytics & Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ACTOR_ENGINE,
    ACTOR_SYSTEM,
    ENGINE_SYSTEM_ID,
    AggregationWindow,
    KPIType,
    PerformanceDomain,
)
from .exceptions import PerformanceEngineNotRunningError
from .performance_context import PerformanceContext, make_performance_context
from .performance_factory import PerformanceAnalyticsFactory
from .performance_history import PerformanceAnalyticsHistory
from .performance_kpi import KPIReport
from .performance_manager import PerformanceManager
from .performance_registry import PerformanceAnalyticsRegistry
from .performance_request import PerformanceRequest, make_performance_request
from .performance_response import (
    BenchmarkReport,
    PerformanceAnalyticsReport,
    PerformanceScorecard,
    TrendAnalysis,
)
from .performance_statistics import PerformanceAnalyticsStatistics

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=ENGINE_SYSTEM_ID)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class PerformanceAnalyticsEngine(LifecycleAwareMixin):
    """
    Institutional Performance Analytics Engine.

    Primary interface for the C8 M3 Performance Analytics Framework.
    Transforms execution operational data into institutional performance
    intelligence: KPIs, trends, benchmarks, aggregations, and efficiency
    metrics.

    Usage
    -----
    ::

        engine = PerformanceAnalyticsEngine()
        engine.start()

        request = engine.factory.create_request(
            domain             = PerformanceDomain.EXECUTION,
            window             = AggregationWindow.FIVE_MINUTES,
            include_trends     = True,
            include_benchmarks = True,
            include_scorecard  = True,
        )
        report = engine.process(request)
        engine.stop()
    """

    def __init__(self) -> None:
        super().__init__()
        self._manager = PerformanceManager()
        self._factory = PerformanceAnalyticsFactory()
        self._lock    = threading.RLock()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        self._manager.start()
        self._factory.start()
        _audit.log_lifecycle_event(
            engine_id  = ENGINE_SYSTEM_ID,
            from_state = "stopped",
            to_state   = "running",
            version    = "1.0.0",
            actor      = ACTOR_ENGINE,
        )
        _log.info("PerformanceAnalyticsEngine started.", system_id=ENGINE_SYSTEM_ID)

    def _on_stop(self) -> None:
        try:
            self._factory.stop()
        except Exception:
            pass
        try:
            self._manager.stop()
        except Exception:
            pass
        _audit.log_lifecycle_event(
            engine_id  = ENGINE_SYSTEM_ID,
            from_state = "running",
            to_state   = "stopped",
            version    = "1.0.0",
            actor      = ACTOR_ENGINE,
        )
        _log.info("PerformanceAnalyticsEngine stopped.", system_id=ENGINE_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise PerformanceEngineNotRunningError()

    # ── Primary interface ─────────────────────────────────────────────────────

    def process(
        self,
        request: "PerformanceRequest | str",
        context: Optional[PerformanceContext] = None,
    ) -> PerformanceAnalyticsReport:
        """
        Process a performance analytics request.

        Accepts either a PerformanceRequest object or a str (for M2
        dispatcher compatibility — the string is treated as a request_id
        and a minimal default request is synthesised for EXECUTION/REAL_TIME).

        Parameters
        ----------
        request:  PerformanceRequest or str request_id.
        context:  Optional PerformanceContext with snapshot data.

        Returns
        -------
        PerformanceAnalyticsReport
        """
        self._assert_running()
        if isinstance(request, str):
            request = make_performance_request(
                domain     = PerformanceDomain.EXECUTION,
                request_id = request,
                window     = AggregationWindow.REAL_TIME,
            )
        return self._manager.process(request, context)

    def submit(
        self,
        domain:             PerformanceDomain,
        window:             AggregationWindow             = AggregationWindow.REAL_TIME,
        *,
        kpi_types:          Tuple[KPIType, ...]            = (),
        include_trends:     bool                          = False,
        include_benchmarks: bool                          = True,
        include_scorecard:  bool                          = True,
        context:            Optional[PerformanceContext]  = None,
        requester:          str                           = ACTOR_SYSTEM,
        reason:             str                           = "",
    ) -> PerformanceAnalyticsReport:
        """
        Convenience method — create a request and process it immediately.
        """
        self._assert_running()
        request = make_performance_request(
            domain             = domain,
            window             = window,
            kpi_types          = kpi_types,
            include_trends     = include_trends,
            include_benchmarks = include_benchmarks,
            include_scorecard  = include_scorecard,
            requester          = requester,
            reason             = reason,
        )
        return self.process(request, context)

    # ── Focused convenience methods ───────────────────────────────────────────

    def calculate_kpis(
        self,
        domain:  PerformanceDomain,
        window:  AggregationWindow             = AggregationWindow.REAL_TIME,
        context: Optional[PerformanceContext]  = None,
    ) -> KPIReport:
        """
        Calculate KPIs for the given domain and window.

        Returns the KPIReport from the analytics cycle.
        """
        self._assert_running()
        report = self.submit(
            domain,
            window,
            include_trends     = False,
            include_benchmarks = False,
            include_scorecard  = False,
            context            = context,
        )
        return report.kpi_report

    def analyze_trends(
        self,
        domain:      PerformanceDomain,
        window:      AggregationWindow             = AggregationWindow.REAL_TIME,
        context:     Optional[PerformanceContext]  = None,
    ) -> List[TrendAnalysis]:
        """
        Run trend analysis for all available historical KPI series.

        Returns a list of TrendAnalysis objects.
        """
        self._assert_running()
        report = self.submit(
            domain,
            window,
            include_trends     = True,
            include_benchmarks = False,
            include_scorecard  = False,
            context            = context,
        )
        return list(report.trends)

    def compare_benchmarks(
        self,
        domain:  PerformanceDomain,
        window:  AggregationWindow             = AggregationWindow.REAL_TIME,
        context: Optional[PerformanceContext]  = None,
    ) -> Optional[BenchmarkReport]:
        """
        Compare KPIs against institutional benchmarks.

        Returns a BenchmarkReport, or None if no KPIs were computable.
        """
        self._assert_running()
        report = self.submit(
            domain,
            window,
            include_trends     = False,
            include_benchmarks = True,
            include_scorecard  = False,
            context            = context,
        )
        return report.benchmark_report

    def generate_scorecard(
        self,
        domain:  PerformanceDomain,
        window:  AggregationWindow             = AggregationWindow.REAL_TIME,
        context: Optional[PerformanceContext]  = None,
    ) -> Optional[PerformanceScorecard]:
        """
        Generate a performance scorecard.

        Returns a PerformanceScorecard, or None if no KPIs were computable.
        """
        self._assert_running()
        report = self.submit(
            domain,
            window,
            include_trends     = False,
            include_benchmarks = True,
            include_scorecard  = True,
            context            = context,
        )
        return report.scorecard

    # ── Observability ─────────────────────────────────────────────────────────

    def get_statistics(self) -> PerformanceAnalyticsStatistics:
        """Return a reference to the live statistics object."""
        return self._manager.statistics

    def get_history(self) -> PerformanceAnalyticsHistory:
        """Return a reference to the live history object."""
        return self._manager.history

    def get_registry(self) -> PerformanceAnalyticsRegistry:
        """Return the active request registry."""
        return self._manager.registry

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def factory(self) -> PerformanceAnalyticsFactory:
        """PerformanceAnalyticsFactory for building requests and contexts."""
        return self._factory

    @property
    def system_id(self) -> str:
        return ENGINE_SYSTEM_ID
