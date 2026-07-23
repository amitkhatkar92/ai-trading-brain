"""
market_analytics_engine.py — iios.market.analytics
====================================================
Primary public interface for the Market Analytics Framework.

C12 Market Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ANALYTICS_SYSTEM_ID,
    ACTOR_ANALYTICS_ENGINE,
    VERSION,
)
from .exceptions import (
    MarketAnalyticsEngineNotRunningError,
    MarketAnalyticsNotApprovedError,
)
from .market_analytics_events import (
    analytics_failed_event,
    analytics_published_event,
    analytics_started_event,
)
from .market_analytics_factory  import MarketAnalyticsFactory
from .market_analytics_history  import MarketAnalyticsHistory
from .market_analytics_manager  import MarketAnalyticsManager
from .market_analytics_registry import MarketAnalyticsRegistry
from .market_analytics_request  import MarketAnalyticsRequest
from .market_analytics_response import MarketAnalyticsReport
from .market_analytics_statistics import MarketAnalyticsStatistics
from .market_analytics_validator  import MarketAnalyticsValidator

_log = get_logger(__name__)


class MarketAnalyticsEngine(LifecycleAwareMixin):
    """
    Market Analytics Engine — primary public interface.

    Responsibilities
    ----------------
    - Lifecycle management (start / stop) via :class:`LifecycleAwareMixin`
    - Policy gate: only processes policy-approved requests
    - Delegates to :class:`~.market_analytics_manager.MarketAnalyticsManager`
      for the full analytics pipeline
    - Maintains per-engine statistics, history, and registry
    - Emits domain events to registered listeners
    """

    def __init__(
        self,
        max_analytics:  int = 10_000,
        max_history:    int = 1_000,
    ) -> None:
        super().__init__()
        self._max_analytics = max_analytics
        self._lock           = threading.RLock()
        self._listeners:     List[Callable[[Any], None]] = []

        self._manager    = MarketAnalyticsManager()
        self._validator  = MarketAnalyticsValidator()
        self._statistics = MarketAnalyticsStatistics()
        self._history    = MarketAnalyticsHistory(max_history)
        self._registry   = MarketAnalyticsRegistry(max_analytics)
        self._factory    = MarketAnalyticsFactory()

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        _log.info(
            "MarketAnalyticsEngine started",
            extra={"engine_id": ANALYTICS_SYSTEM_ID, "version": VERSION},
        )

    def _on_stop(self) -> None:
        _log.info(
            "MarketAnalyticsEngine stopped",
            extra={"engine_id": ANALYTICS_SYSTEM_ID},
        )

    # ------------------------------------------------------------------
    # Primary entry point
    # ------------------------------------------------------------------

    def assess(self, request: MarketAnalyticsRequest) -> MarketAnalyticsReport:
        """
        Run the full analytics pipeline for *request*.

        Parameters
        ----------
        request : MarketAnalyticsRequest
            A fully assembled analytics request (use
            :class:`~.market_analytics_factory.MarketAnalyticsFactory`
            to construct).

        Returns
        -------
        MarketAnalyticsReport
            Immutable report containing all domain results and scores.

        Raises
        ------
        MarketAnalyticsEngineNotRunningError
            If the engine has not been started.
        MarketAnalyticsNotApprovedError
            If ``request.policy_approved`` is not ``True``.
        MarketAnalyticsValidationError
            If the request fails structural validation.
        """
        if self.lifecycle_state().value != "running":
            raise MarketAnalyticsEngineNotRunningError(
                "MarketAnalyticsEngine must be started before calling assess()"
            )

        if not request.policy_approved:
            raise MarketAnalyticsNotApprovedError(
                analytics_id=request.analytics_id,
            )

        # Structural validation
        self._validator.validate_request_or_raise(request)

        self._statistics.record_analytics_started()
        self._history.record_request(request)

        started_evt = analytics_started_event(
            analytics_id       = request.analytics_id,
            market_analysis_id = request.market_analysis_id,
            exchange           = request.exchange,
            actor              = ACTOR_ANALYTICS_ENGINE,
        )
        self._emit(started_evt)
        self._history.record_event(started_evt)

        t0 = time.monotonic()
        try:
            report = self._manager.run(request)
        except Exception as exc:
            elapsed = time.monotonic() - t0
            report  = MarketAnalyticsReport.create_failure(
                analytics_id       = request.analytics_id,
                market_analysis_id = request.market_analysis_id,
                exchange           = request.exchange,
                error_message      = str(exc),
                elapsed_s          = elapsed,
            )
            self._statistics.record_analytics_failed()
            self._statistics.record_elapsed(elapsed)
            failed_evt = analytics_failed_event(
                analytics_id       = request.analytics_id,
                market_analysis_id = request.market_analysis_id,
                exchange           = request.exchange,
                actor              = ACTOR_ANALYTICS_ENGINE,
                error              = str(exc),
            )
            self._emit(failed_evt)
            self._history.record_event(failed_evt)
            self._history.record_report(report)
            _log.error("Analytics pipeline failed: %s", exc, exc_info=True)
            return report

        self._statistics.record_analytics_completed()
        self._statistics.record_elapsed(report.elapsed_s)
        if report.regime is not None:
            self._statistics.record_regime_classified()
        if report.breadth is not None:
            self._statistics.record_breadth_analysis()
        if report.sector_results:
            self._statistics.record_sector_analysis()
        if report.forecasts:
            self._statistics.record_forecast_generated()

        self._registry.register(report)
        self._history.record_report(report)

        published_evt = analytics_published_event(
            analytics_id       = request.analytics_id,
            market_analysis_id = request.market_analysis_id,
            exchange           = request.exchange,
            actor              = ACTOR_ANALYTICS_ENGINE,
        )
        self._emit(published_evt)
        self._history.record_event(published_evt)

        return report

    # ------------------------------------------------------------------
    # Registry queries
    # ------------------------------------------------------------------

    def get_report(self, report_id: str) -> Optional[MarketAnalyticsReport]:
        return self._registry.get(report_id)

    def latest_for_exchange(self, exchange: str) -> Optional[MarketAnalyticsReport]:
        return self._registry.latest_for_exchange(exchange)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def statistics(self) -> Dict[str, Any]:
        return self._statistics.snapshot()

    def history_counts(self) -> Dict[str, int]:
        return self._history.counts()

    # ------------------------------------------------------------------
    # Factory convenience
    # ------------------------------------------------------------------

    @staticmethod
    def create_request(
        analytics_id:       str,
        market_analysis_id: str,
        exchange:           str,
        *,
        policy_approved:    bool = False,
        **kwargs: Any,
    ) -> MarketAnalyticsRequest:
        ctx = MarketAnalyticsFactory.create_context(
            analytics_id, market_analysis_id, exchange
        )
        return MarketAnalyticsFactory.create_request(
            analytics_id,
            market_analysis_id,
            exchange,
            ctx,
            policy_approved = policy_approved,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Event listeners
    # ------------------------------------------------------------------

    def add_listener(self, fn: Callable[[Any], None]) -> None:
        with self._lock:
            if fn not in self._listeners:
                self._listeners.append(fn)

    def remove_listener(self, fn: Callable[[Any], None]) -> None:
        with self._lock:
            self._listeners = [f for f in self._listeners if f != fn]

    def _emit(self, event: Any) -> None:
        with self._lock:
            listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn(event)
            except Exception:
                pass
