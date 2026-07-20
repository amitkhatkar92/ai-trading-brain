"""
iios/execution/analytics/predictive/predictive_factory.py
=========================================================
PredictiveIntelligenceFactory — builds PredictionRequest and
PredictiveContext objects for the Predictive Intelligence Framework.

C8 Execution Analytics & Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import ACTOR_SYSTEM, FACTORY_SYSTEM_ID, ForecastHorizon, PredictionDomain, PredictionType
from .exceptions import PredictiveEngineNotRunningError
from .predictive_context import PredictiveContext, make_predictive_context
from .predictive_request import PredictionRequest, make_prediction_request

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class PredictiveIntelligenceFactory(LifecycleAwareMixin):
    """
    Factory for PredictionRequest and PredictiveContext objects.

    Thread-safe.  Must be started before use.
    """

    def _on_start(self) -> None:
        _log.info("PredictiveIntelligenceFactory started.", system_id=FACTORY_SYSTEM_ID)

    def _on_stop(self) -> None:
        _log.info("PredictiveIntelligenceFactory stopped.", system_id=FACTORY_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise PredictiveEngineNotRunningError()

    def create_request(
        self,
        domain:             PredictionDomain,
        *,
        horizon:            ForecastHorizon               = ForecastHorizon.NEXT_HOUR,
        prediction_types:   Tuple[PredictionType, ...]     = (),
        include_trends:     bool                          = True,
        include_anomalies:  bool                          = True,
        include_risks:      bool                          = True,
        include_capacity:   bool                          = True,
        requester:          str                           = ACTOR_SYSTEM,
        priority:           int                           = 5,
        reason:             str                           = "",
        tags:               Tuple[str, ...]                = (),
        metadata:           Optional[Dict[str, Any]]      = None,
        request_id:         Optional[str]                 = None,
    ) -> PredictionRequest:
        """Create a new PredictionRequest."""
        self._assert_running()
        return make_prediction_request(
            domain            = domain,
            request_id        = request_id,
            horizon           = horizon,
            prediction_types  = prediction_types,
            include_trends    = include_trends,
            include_anomalies = include_anomalies,
            include_risks     = include_risks,
            include_capacity  = include_capacity,
            requester         = requester,
            priority          = priority,
            reason            = reason,
            tags              = tags,
            metadata          = metadata,
        )

    def create_context(
        self,
        request_id:             str,
        domain:                 PredictionDomain,
        horizon:                ForecastHorizon,
        *,
        context_id:             Optional[str]                    = None,
        performance_report:     Optional[Any]                    = None,
        performance_snapshot:   Optional[Any]                    = None,
        monitoring_snapshot:    Optional[Any]                    = None,
        recovery_snapshot:      Optional[Any]                    = None,
        gateway_snapshot:       Optional[Any]                    = None,
        historical_analytics:   Optional[Dict[str, List[float]]] = None,
        raw_metrics:            Optional[Dict[str, List[float]]] = None,
        execution_statistics:   Optional[Any]                    = None,
        custom_horizon_seconds: float                            = 0.0,
        requester:              str                              = ACTOR_SYSTEM,
        metadata:               Optional[Dict[str, Any]]         = None,
    ) -> PredictiveContext:
        """Create a new PredictiveContext."""
        self._assert_running()
        return make_predictive_context(
            request_id             = request_id,
            domain                 = domain,
            horizon                = horizon,
            context_id             = context_id,
            performance_report     = performance_report,
            performance_snapshot   = performance_snapshot,
            monitoring_snapshot    = monitoring_snapshot,
            recovery_snapshot      = recovery_snapshot,
            gateway_snapshot       = gateway_snapshot,
            historical_analytics   = historical_analytics,
            raw_metrics            = raw_metrics,
            execution_statistics   = execution_statistics,
            custom_horizon_seconds = custom_horizon_seconds,
            requester              = requester,
            metadata               = metadata,
        )

    def create_context_for_request(
        self,
        request:                PredictionRequest,
        *,
        performance_report:     Optional[Any]                    = None,
        performance_snapshot:   Optional[Any]                    = None,
        historical_analytics:   Optional[Dict[str, List[float]]] = None,
        raw_metrics:            Optional[Dict[str, List[float]]] = None,
        custom_horizon_seconds: float                            = 0.0,
        metadata:               Optional[Dict[str, Any]]         = None,
    ) -> PredictiveContext:
        """Create a PredictiveContext aligned to an existing request."""
        self._assert_running()
        return make_predictive_context(
            request_id             = request.request_id,
            domain                 = request.domain,
            horizon                = request.horizon,
            performance_report     = performance_report,
            performance_snapshot   = performance_snapshot,
            historical_analytics   = historical_analytics,
            raw_metrics            = raw_metrics,
            custom_horizon_seconds = custom_horizon_seconds,
            requester              = request.requester,
            metadata               = metadata,
        )
