"""
iios/execution/analytics/predictive/predictive_intelligence_engine.py
=====================================================================
PredictiveIntelligenceEngine — PRIMARY PUBLIC INTERFACE for the
Institutional Predictive Intelligence Framework (C8 M4).

This is the ONLY public entry point for external callers.

Responsibilities:
  - Accept and process PredictionRequest objects (or str request_ids
    for M3/dispatcher compatibility)
  - Delegate the full prediction cycle to PredictiveManager
  - Provide focused convenience methods for individual forecast tasks
  - Expose statistics and history for observability

This framework ONLY produces operational forecasts.
It MUST NOT execute trades, generate trading signals, place orders,
modify portfolios, communicate with brokers, or bypass Decision
Intelligence.

C8 Execution Analytics & Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional, Tuple

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ACTOR_ENGINE,
    ACTOR_SYSTEM,
    ENGINE_SYSTEM_ID,
    ForecastHorizon,
    PredictionDomain,
    PredictionType,
    TrendType,
)
from .exceptions import PredictiveEngineNotRunningError
from .predictive_context import PredictiveContext, make_predictive_context
from .predictive_factory import PredictiveIntelligenceFactory
from .predictive_history import PredictiveIntelligenceHistory
from .predictive_manager import PredictiveManager
from .predictive_registry import PredictiveIntelligenceRegistry
from .predictive_request import PredictionRequest, make_prediction_request
from .predictive_response import (
    CapacityForecast,
    Forecast,
    ForecastSummary,
    OperationalForecast,
    PredictionReport,
    ProbabilityReport,
    RiskForecast,
)
from .predictive_statistics import PredictiveIntelligenceStatistics

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=ENGINE_SYSTEM_ID)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class PredictiveIntelligenceEngine(LifecycleAwareMixin):
    """
    Institutional Predictive Intelligence Engine.

    Primary interface for the C8 M4 Predictive Intelligence Framework.
    Converts historical execution analytics into forward-looking operational
    intelligence: trend forecasts, capacity estimates, risk forecasts,
    probability reports, and anomaly predictions.

    Usage
    -----
    ::

        engine = PredictiveIntelligenceEngine()
        engine.start()

        request = engine.factory.create_request(
            domain            = PredictionDomain.EXECUTION_PERFORMANCE,
            horizon           = ForecastHorizon.NEXT_HOUR,
            include_trends    = True,
            include_anomalies = True,
            include_risks     = True,
            include_capacity  = True,
        )
        context = engine.factory.create_context(
            request_id           = request.request_id,
            domain               = request.domain,
            horizon              = request.horizon,
            historical_analytics = {
                PredictionType.EXECUTION_VOLUME_FORECAST.value: [100, 110, 120, 115],
            },
        )
        report = engine.process(request, context)
        engine.stop()
    """

    def __init__(self) -> None:
        super().__init__()
        self._manager = PredictiveManager()
        self._factory = PredictiveIntelligenceFactory()
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
        _log.info("PredictiveIntelligenceEngine started.", system_id=ENGINE_SYSTEM_ID)

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
        _log.info("PredictiveIntelligenceEngine stopped.", system_id=ENGINE_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise PredictiveEngineNotRunningError()

    # ── Primary interface ─────────────────────────────────────────────────────

    def process(
        self,
        request: "PredictionRequest | str",
        context: Optional[PredictiveContext] = None,
    ) -> PredictionReport:
        """
        Process a prediction intelligence request.

        Accepts either a PredictionRequest or a str (for M3 dispatcher
        compatibility — the string is treated as a request_id and a
        minimal default request is synthesised for
        EXECUTION_PERFORMANCE / NEXT_HOUR).

        Parameters
        ----------
        request:  PredictionRequest or str request_id.
        context:  Optional PredictiveContext with historical data.

        Returns
        -------
        PredictionReport
        """
        self._assert_running()
        if isinstance(request, str):
            request = make_prediction_request(
                domain     = PredictionDomain.EXECUTION_PERFORMANCE,
                request_id = request,
                horizon    = ForecastHorizon.NEXT_HOUR,
            )
        return self._manager.process(request, context)

    def submit(
        self,
        domain:             PredictionDomain,
        horizon:            ForecastHorizon              = ForecastHorizon.NEXT_HOUR,
        *,
        prediction_types:   Tuple[PredictionType, ...]    = (),
        include_trends:     bool                         = True,
        include_anomalies:  bool                         = True,
        include_risks:      bool                         = True,
        include_capacity:   bool                         = True,
        context:            Optional[PredictiveContext]  = None,
        requester:          str                          = ACTOR_SYSTEM,
        reason:             str                          = "",
    ) -> PredictionReport:
        """
        Convenience method — create a request and process it immediately.
        """
        self._assert_running()
        request = make_prediction_request(
            domain            = domain,
            horizon           = horizon,
            prediction_types  = prediction_types,
            include_trends    = include_trends,
            include_anomalies = include_anomalies,
            include_risks     = include_risks,
            include_capacity  = include_capacity,
            requester         = requester,
            reason            = reason,
        )
        return self.process(request, context)

    # ── Focused convenience methods ───────────────────────────────────────────

    def generate_forecasts(
        self,
        domain:   PredictionDomain,
        horizon:  ForecastHorizon             = ForecastHorizon.NEXT_HOUR,
        context:  Optional[PredictiveContext] = None,
    ) -> List[Forecast]:
        """Generate operational forecasts without risk/capacity analysis."""
        self._assert_running()
        report = self.submit(
            domain,
            horizon,
            include_trends    = False,
            include_anomalies = False,
            include_risks     = False,
            include_capacity  = False,
            context           = context,
        )
        return list(report.forecasts)

    def forecast_risk(
        self,
        domain:   PredictionDomain,
        horizon:  ForecastHorizon             = ForecastHorizon.NEXT_HOUR,
        context:  Optional[PredictiveContext] = None,
    ) -> Optional[RiskForecast]:
        """Generate a risk forecast only."""
        self._assert_running()
        report = self.submit(
            domain, horizon,
            include_trends    = False,
            include_anomalies = True,
            include_risks     = True,
            include_capacity  = False,
            context           = context,
        )
        return report.risk_forecast

    def estimate_capacity(
        self,
        domain:   PredictionDomain,
        horizon:  ForecastHorizon             = ForecastHorizon.NEXT_HOUR,
        context:  Optional[PredictiveContext] = None,
    ) -> Optional[CapacityForecast]:
        """Estimate capacity utilization for the horizon."""
        self._assert_running()
        report = self.submit(
            domain, horizon,
            include_trends    = False,
            include_anomalies = False,
            include_risks     = False,
            include_capacity  = True,
            context           = context,
        )
        return report.capacity_forecast

    def get_probabilities(
        self,
        domain:   PredictionDomain,
        horizon:  ForecastHorizon             = ForecastHorizon.NEXT_HOUR,
        context:  Optional[PredictiveContext] = None,
    ) -> Optional[ProbabilityReport]:
        """Get probability estimates for all prediction types."""
        self._assert_running()
        report = self.submit(
            domain, horizon,
            include_trends    = False,
            include_anomalies = False,
            include_risks     = False,
            include_capacity  = False,
            context           = context,
        )
        return report.probability_report

    def get_operational_forecast(
        self,
        domain:   PredictionDomain,
        horizon:  ForecastHorizon             = ForecastHorizon.NEXT_HOUR,
        context:  Optional[PredictiveContext] = None,
    ) -> Optional[OperationalForecast]:
        """Get the operational health and availability forecast."""
        self._assert_running()
        report = self.submit(
            domain, horizon,
            include_risks    = True,
            include_capacity = True,
            context          = context,
        )
        return report.operational_forecast

    # ── Observability ─────────────────────────────────────────────────────────

    def get_statistics(self) -> PredictiveIntelligenceStatistics:
        """Return the live statistics object."""
        return self._manager.statistics

    def get_history(self) -> PredictiveIntelligenceHistory:
        """Return the live history object."""
        return self._manager.history

    def get_registry(self) -> PredictiveIntelligenceRegistry:
        """Return the active request registry."""
        return self._manager.registry

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def factory(self) -> PredictiveIntelligenceFactory:
        """PredictiveIntelligenceFactory for building requests and contexts."""
        return self._factory

    @property
    def system_id(self) -> str:
        return ENGINE_SYSTEM_ID
