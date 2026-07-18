"""
iios/execution/analytics/performance/performance_factory.py
===========================================================
PerformanceAnalyticsFactory — builds PerformanceRequest and
PerformanceContext objects for the Performance Analytics Framework.

C8 Execution Analytics & Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import ACTOR_SYSTEM, FACTORY_SYSTEM_ID, AggregationWindow, KPIType, PerformanceDomain
from .exceptions import PerformanceEngineNotRunningError
from .performance_context import PerformanceContext, make_performance_context
from .performance_request import PerformanceRequest, make_performance_request

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class PerformanceAnalyticsFactory(LifecycleAwareMixin):
    """
    Factory for creating PerformanceRequest and PerformanceContext objects.

    Thread-safe.  Must be started before use.
    """

    def _on_start(self) -> None:
        _log.info("PerformanceAnalyticsFactory started.", system_id=FACTORY_SYSTEM_ID)

    def _on_stop(self) -> None:
        _log.info("PerformanceAnalyticsFactory stopped.", system_id=FACTORY_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise PerformanceEngineNotRunningError()

    def create_request(
        self,
        domain:             PerformanceDomain,
        *,
        window:             AggregationWindow              = AggregationWindow.REAL_TIME,
        kpi_types:          Tuple[KPIType, ...]             = (),
        include_trends:     bool                           = False,
        include_benchmarks: bool                           = True,
        include_scorecard:  bool                           = True,
        requester:          str                            = ACTOR_SYSTEM,
        priority:           int                            = 5,
        reason:             str                            = "",
        tags:               Tuple[str, ...]                 = (),
        metadata:           Optional[Dict[str, Any]]       = None,
        request_id:         Optional[str]                  = None,
    ) -> PerformanceRequest:
        """Create a new PerformanceRequest."""
        self._assert_running()
        return make_performance_request(
            domain             = domain,
            request_id         = request_id,
            window             = window,
            kpi_types          = kpi_types,
            include_trends     = include_trends,
            include_benchmarks = include_benchmarks,
            include_scorecard  = include_scorecard,
            requester          = requester,
            priority           = priority,
            reason             = reason,
            tags               = tags,
            metadata           = metadata,
        )

    def create_context(
        self,
        request_id:            str,
        domain:                PerformanceDomain,
        window:                AggregationWindow,
        *,
        context_id:            Optional[str]                    = None,
        monitoring_snapshot:   Optional[Any]                    = None,
        recovery_snapshot:     Optional[Any]                    = None,
        gateway_snapshot:      Optional[Any]                    = None,
        risk_snapshot:         Optional[Any]                    = None,
        historical_kpi_data:   Optional[Dict[str, List[float]]] = None,
        raw_sample_data:       Optional[Dict[str, List[float]]] = None,
        custom_window_seconds: float                            = 0.0,
        requester:             str                              = ACTOR_SYSTEM,
        metadata:              Optional[Dict[str, Any]]         = None,
    ) -> PerformanceContext:
        """Create a new PerformanceContext."""
        self._assert_running()
        return make_performance_context(
            request_id             = request_id,
            domain                 = domain,
            window                 = window,
            context_id             = context_id,
            monitoring_snapshot    = monitoring_snapshot,
            recovery_snapshot      = recovery_snapshot,
            gateway_snapshot       = gateway_snapshot,
            risk_snapshot          = risk_snapshot,
            historical_kpi_data    = historical_kpi_data,
            raw_sample_data        = raw_sample_data,
            custom_window_seconds  = custom_window_seconds,
            requester              = requester,
            metadata               = metadata,
        )

    def create_context_for_request(
        self,
        request:               PerformanceRequest,
        *,
        monitoring_snapshot:   Optional[Any]                    = None,
        recovery_snapshot:     Optional[Any]                    = None,
        gateway_snapshot:      Optional[Any]                    = None,
        risk_snapshot:         Optional[Any]                    = None,
        historical_kpi_data:   Optional[Dict[str, List[float]]] = None,
        raw_sample_data:       Optional[Dict[str, List[float]]] = None,
        custom_window_seconds: float                            = 0.0,
        metadata:              Optional[Dict[str, Any]]         = None,
    ) -> PerformanceContext:
        """Create a PerformanceContext aligned to an existing request."""
        self._assert_running()
        return make_performance_context(
            request_id             = request.request_id,
            domain                 = request.domain,
            window                 = request.window,
            monitoring_snapshot    = monitoring_snapshot,
            recovery_snapshot      = recovery_snapshot,
            gateway_snapshot       = gateway_snapshot,
            risk_snapshot          = risk_snapshot,
            historical_kpi_data    = historical_kpi_data,
            raw_sample_data        = raw_sample_data,
            custom_window_seconds  = custom_window_seconds,
            requester              = request.requester,
            metadata               = metadata,
        )
