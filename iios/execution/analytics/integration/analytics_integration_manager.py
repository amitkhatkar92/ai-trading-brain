"""
analytics_integration_manager.py — iios.execution.analytics.integration
=========================================================================
Orchestrates the full M1-M5 analytics pipeline for one integration request.

:class:`AnalyticsIntegrationManager` is an internal component of the
integration subsystem.  External callers MUST use
:class:`ExecutionAnalyticsIntegration` — the manager is never exposed.

Workflow (9 steps, each gracefully degraded)
--------------------------------------------
1.  Validate request structure.
2.  Register request in the integration registry.
3.  Create M1 analytics session.
4.  Advance M1 lifecycle to ACTIVE.
5.  Invoke M2 analytics engine.
6.  Run M3 performance analytics.
7.  Run M4 predictive intelligence.
8.  Build + publish M5 snapshot.
9.  Complete M1 session.
10. Build :class:`AnalyticsIntegrationResponse`.
11. Record stats, events, history.
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.execution.analytics.lifecycle import (
    AnalyticsTrigger,
)
from iios.execution.analytics.engine import (
    make_analytics_request,
    AnalyticsRequestType,
)
from iios.execution.analytics.predictive import (
    PredictionDomain,
    ForecastHorizon,
)
from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger

from .constants import (
    MANAGER_SYSTEM_ID,
    INTEGRATION_VERSION,
    ACTOR_MANAGER,
)
from .analytics_integration_request import AnalyticsIntegrationRequest
from .analytics_integration_context import AnalyticsIntegrationContext
from .analytics_integration_response import AnalyticsIntegrationResponse
from .analytics_integration_snapshot import IntegrationSnapshotRecord
from .analytics_integration_registry import AnalyticsIntegrationRegistry
from .analytics_integration_statistics import AnalyticsIntegrationStatistics
from .analytics_integration_history import AnalyticsIntegrationHistory
from .analytics_integration_validation import AnalyticsIntegrationValidator
from .analytics_component_registry import AnalyticsComponentRegistry
from .analytics_integration_events import (
    make_analytics_completed,
    make_analytics_snapshot_published,
    make_analytics_validated,
)

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=MANAGER_SYSTEM_ID)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class AnalyticsIntegrationManager(LifecycleAwareMixin):
    """
    Orchestrates the M1-M5 analytics pipeline.

    This is an internal component owned exclusively by
    :class:`ExecutionAnalyticsIntegration`.  It is never exposed to callers.

    Parameters
    ----------
    components :  Running :class:`AnalyticsComponentRegistry`.
    registry :    :class:`AnalyticsIntegrationRegistry` for request tracking.
    statistics :  Shared :class:`AnalyticsIntegrationStatistics`.
    history :     Shared :class:`AnalyticsIntegrationHistory`.
    validator :   :class:`AnalyticsIntegrationValidator` instance.
    """

    def __init__(
        self,
        components:  AnalyticsComponentRegistry,
        registry:    AnalyticsIntegrationRegistry,
        statistics:  AnalyticsIntegrationStatistics,
        history:     AnalyticsIntegrationHistory,
        validator:   AnalyticsIntegrationValidator,
    ) -> None:
        super().__init__()
        self._components  = components
        self._registry    = registry
        self._stats       = statistics
        self._history     = history
        self._validator   = validator
        self._lock        = threading.Lock()

    # ------------------------------------------------------------------
    # LifecycleAwareMixin hooks
    # ------------------------------------------------------------------
    def _on_start(self) -> None:
        _audit.log_lifecycle_event(
            engine_id  = MANAGER_SYSTEM_ID,
            from_state = "stopped",
            to_state   = "running",
            version    = INTEGRATION_VERSION,
            actor      = ACTOR_MANAGER,
        )

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            engine_id  = MANAGER_SYSTEM_ID,
            from_state = "running",
            to_state   = "stopped",
            version    = INTEGRATION_VERSION,
            actor      = ACTOR_MANAGER,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def process(
        self, request: AnalyticsIntegrationRequest
    ) -> AnalyticsIntegrationResponse:
        """
        Execute the full M1-M5 analytics pipeline for *request*.

        Each pipeline step is independently wrapped in try/except.
        A failure in M2/M3/M4 degrades but does not abort the pipeline.
        A failure in M1 session creation causes an immediate FAILED response.

        Returns
        -------
        AnalyticsIntegrationResponse
        """
        if self.lifecycle_state() not in _RUNNING:
            from .exceptions import IntegrationNotRunningError
            raise IntegrationNotRunningError("manager.process")

        t_start = time.perf_counter()
        self._stats.record_request_received()

        # ----------------------------------------------------------
        # Step 1 — Structural validation
        # ----------------------------------------------------------
        req_valid, req_err = self._validator.validate_request_only(
            execution_session_id = request.execution_session_id,
            priority             = request.priority,
        )
        if not req_valid:
            self._stats.record_request_rejected()
            resp = AnalyticsIntegrationResponse.rejected(
                request_id           = request.request_id,
                execution_session_id = request.execution_session_id,
                reason               = req_err,
            )
            self._history.record_response(resp)
            self._registry.mark_rejected(request.request_id, req_err)
            return resp

        # ----------------------------------------------------------
        # Step 2 — Register in integration registry
        # ----------------------------------------------------------
        try:
            self._registry.register(request)
        except ValueError:
            # Already in flight (idempotency guard)
            pass

        # ----------------------------------------------------------
        # Step 3 — M1: Create analytics session
        # ----------------------------------------------------------
        analytics_session_id: str = ""
        session_created = False
        try:
            session = self._components.lifecycle.create(
                request.execution_session_id,
                analytics_scope   = request.analytics_scope,
                analytics_mode    = request.analytics_mode,
                analytics_trigger = AnalyticsTrigger.AUTOMATIC,
                analytics_reason  = request.reason or "integration_request",
                workflow_id       = request.workflow_id,
                portfolio_id      = request.portfolio_id,
                strategy_id       = request.strategy_id,
            )
            analytics_session_id = session.session_id
            session_created = True
            self._stats.record_session_created()
            self._registry.mark_in_progress(
                request.request_id, analytics_session_id
            )
            _log.debug(
                f"AnalyticsIntegrationManager: M1 session created {analytics_session_id}"
            )
        except Exception as exc:
            _log.error(
                f"AnalyticsIntegrationManager: M1 session creation failed for "
                f"request {request.request_id}: {exc}"
            )
            processing_ms = (time.perf_counter() - t_start) * 1000
            self._stats.record_request_failed()
            resp = AnalyticsIntegrationResponse.failed(
                request_id           = request.request_id,
                analytics_session_id = analytics_session_id,
                execution_session_id = request.execution_session_id,
                error_message        = f"M1 session creation failed: {exc}",
                processing_ms        = processing_ms,
            )
            self._history.record_response(resp)
            self._registry.mark_failed(request.request_id, str(exc))
            return resp

        # ----------------------------------------------------------
        # Step 4 — M1: Advance session lifecycle to ACTIVE
        # ----------------------------------------------------------
        if session_created:
            self._advance_m1_lifecycle(analytics_session_id)

        # ----------------------------------------------------------
        # Step 5 — M2: Invoke analytics engine
        # ----------------------------------------------------------
        self._invoke_m2_engine(request.execution_session_id)

        # ----------------------------------------------------------
        # Step 6 — M3: Performance analytics
        # ----------------------------------------------------------
        perf_report = None
        if request.include_performance:
            perf_report = self._run_m3(analytics_session_id)
            if perf_report is not None:
                self._stats.record_performance_report()

        # ----------------------------------------------------------
        # Step 7 — M4: Predictive intelligence
        # ----------------------------------------------------------
        pred_report = None
        if request.include_predictions:
            pred_report = self._run_m4()
            if pred_report is not None:
                self._stats.record_forecast_generated()

        # ----------------------------------------------------------
        # Step 8 — M5: Build and publish snapshot
        # ----------------------------------------------------------
        snapshot = None
        snap_record: Optional[IntegrationSnapshotRecord] = None
        if request.include_snapshot:
            snapshot = self._build_m5_snapshot(
                request,
                analytics_session_id,
                perf_report,
                pred_report,
            )
            if snapshot is not None:
                self._stats.record_snapshot_published()
                snap_record = IntegrationSnapshotRecord.create(
                    request_id           = request.request_id,
                    analytics_session_id = analytics_session_id,
                    execution_session_id = request.execution_session_id,
                    snapshot             = snapshot,
                )
                self._history.record_snapshot(snap_record)
                snap_event = make_analytics_snapshot_published(
                    request_id  = request.request_id,
                    session_id  = analytics_session_id,
                    snapshot_id = snapshot.snapshot_id,
                )
                self._history.record_event(snap_event)

        # ----------------------------------------------------------
        # Step 9 — M1: Complete session
        # ----------------------------------------------------------
        if session_created:
            self._complete_m1_session(analytics_session_id)

        # ----------------------------------------------------------
        # Step 10 — Build response
        # ----------------------------------------------------------
        processing_ms = (time.perf_counter() - t_start) * 1000
        resp = AnalyticsIntegrationResponse.success(
            request_id           = request.request_id,
            analytics_session_id = analytics_session_id,
            execution_session_id = request.execution_session_id,
            snapshot             = snapshot,
            processing_ms        = processing_ms,
        )

        # ----------------------------------------------------------
        # Step 11 — Record stats, events, history
        # ----------------------------------------------------------
        self._stats.record_request_completed(processing_ms)
        completed_evt = make_analytics_completed(
            request_id    = request.request_id,
            session_id    = analytics_session_id,
            processing_ms = processing_ms,
            status        = resp.status.value,
        )
        self._history.record_event(completed_evt)
        self._history.record_response(resp)
        self._registry.mark_completed(request.request_id)

        _log.debug(
            f"AnalyticsIntegrationManager: request {request.request_id} completed in {processing_ms:.1f} ms"
        )
        return resp

    def validate_subsystem(self, *, include_performance: bool = True, include_predictions: bool = True) -> object:
        """
        Run all seven integration validation checks and return the result.

        Returns an :class:`~.analytics_integration_validation.IntegrationValidationResult`.
        """
        crmap = self._safe_component_running_map()
        result = self._validator.validate(
            lifecycle_running   = crmap.get("lifecycle",   False),
            engine_running      = crmap.get("engine",      False),
            performance_running = crmap.get("performance", False),
            predictive_running  = crmap.get("predictive",  False),
            snapshot_running    = crmap.get("snapshot",    False),
            integration_running = self.lifecycle_state() in _RUNNING,
            request_valid       = True,
            include_performance = include_performance,
            include_predictions = include_predictions,
        )
        validated_evt = make_analytics_validated(
            passed        = result.is_valid,
            failed_checks = tuple(c.value for c in result.failed_checks),
        )
        self._history.record_event(validated_evt)
        return result

    # ------------------------------------------------------------------
    # Private pipeline steps
    # ------------------------------------------------------------------
    def _advance_m1_lifecycle(self, session_id: str) -> None:
        """Advance M1 session through INITIALIZING→COLLECTING→ANALYZING→READY→ACTIVE."""
        for transition_fn_name in ("initialize", "collect", "analyze", "ready", "activate"):
            try:
                getattr(self._components.lifecycle, transition_fn_name)(session_id)
            except Exception as exc:
                _log.debug(
                    f"AnalyticsIntegrationManager: M1 {transition_fn_name}({session_id}) skipped: {exc}"
                )
                break  # stop advancing on first error

    def _invoke_m2_engine(self, execution_session_id: str) -> None:
        """Invoke M2 analytics engine; failure is non-fatal."""
        try:
            m2_req = make_analytics_request(
                execution_session_id,
                request_type = AnalyticsRequestType.ON_DEMAND,
                requester    = ACTOR_MANAGER,
                reason       = "integration_pipeline",
            )
            self._components.engine.process(m2_req)
        except Exception as exc:
            _log.debug(
                f"AnalyticsIntegrationManager: M2 engine invocation skipped: {exc}"
            )

    def _run_m3(self, session_id: str) -> object | None:
        """Run M3 performance analytics; returns None on failure."""
        try:
            return self._components.performance.process(session_id)
        except Exception as exc:
            _log.debug(
                f"AnalyticsIntegrationManager: M3 performance analytics skipped: {exc}"
            )
            return None

    def _run_m4(self) -> object | None:
        """Run M4 predictive intelligence; returns None on failure."""
        try:
            return self._components.predictive.submit(
                PredictionDomain.EXECUTION_PERFORMANCE,
                ForecastHorizon.NEXT_HOUR,
            )
        except Exception as exc:
            _log.debug(
                f"AnalyticsIntegrationManager: M4 predictive intelligence skipped: {exc}"
            )
            return None

    def _build_m5_snapshot(
        self,
        request: AnalyticsIntegrationRequest,
        analytics_session_id: str,
        perf_report: object | None,
        pred_report: object | None,
    ) -> object | None:
        """Build and publish M5 snapshot; returns None on failure."""
        try:
            return self._components.snapshot_factory.create(
                analytics_session_id = analytics_session_id,
                execution_session_id = request.execution_session_id,
                workflow_id          = request.workflow_id,
                portfolio_id         = request.portfolio_id,
                strategy_id          = request.strategy_id,
                analytics_scope      = request.analytics_scope,
                analytics_mode       = request.analytics_mode,
                performance_report   = perf_report,
                prediction_report    = pred_report,
                publish              = True,
            )
        except Exception as exc:
            _log.debug(
                f"AnalyticsIntegrationManager: M5 snapshot build skipped: {exc}"
            )
            return None

    def _complete_m1_session(self, session_id: str) -> None:
        """Complete M1 analytics session; failure is non-fatal."""
        try:
            self._components.lifecycle.complete(session_id)
        except Exception as exc:
            _log.debug(
                f"AnalyticsIntegrationManager: M1 complete({session_id}) skipped: {exc}"
            )

    def _safe_component_running_map(self) -> dict:
        """Return component running map safely; all False if registry is not running."""
        try:
            crmap_raw = self._components.component_running_map()
            return {ct.value: running for ct, running in crmap_raw.items()}
        except Exception:
            from .constants import ComponentType
            return {ct.value: False for ct in ComponentType}
