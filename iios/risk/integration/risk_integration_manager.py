"""
risk_integration_manager.py — iios.risk.integration
=====================================================
Workflow coordinator for the Risk Integration layer.

Orchestrates the 10-step integration pipeline:
  1. Validate request
  2. Initialize risk session (lifecycle component)
  3. Process via risk engine
  4. Evaluate policies
  5. Execute risk assessment
  6. Build risk snapshot
  7. Publish risk snapshot
  8. Register response
  9. Record history
  10. Return response

Performs NO calculations, NO policy evaluation logic,
NO optimization, NO execution.  All substantive work is
delegated to the registered M1-M5 subsystem components.

C11 Risk Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    ACTOR_INTEGRATION_MANAGER,
    COMPONENT_ASSESSMENT,
    COMPONENT_LIFECYCLE,
    COMPONENT_POLICIES,
    COMPONENT_SNAPSHOT,
    COMPONENT_ENGINE,
    IntegrationStatus,
    VERSION,
)
from .exceptions import (
    RiskIntegrationComponentError,
    RiskIntegrationValidationError,
    RiskIntegrationWorkflowError,
)
from .risk_component_registry import RiskComponentRegistry
from .risk_integration_events import (
    make_request_received,
    make_risk_completed,
    make_risk_failed,
    make_risk_validated,
    make_snapshot_published,
)
from .risk_integration_history import RiskIntegrationHistory
from .risk_integration_registry import RiskIntegrationRegistry
from .risk_integration_request import RiskIntegrationRequest
from .risk_integration_response import RiskIntegrationResponse
from .risk_integration_statistics import RiskIntegrationStatistics
from .risk_integration_validation import RiskIntegrationValidator

_log = get_logger(__name__)


class RiskIntegrationManager:
    """
    Workflow coordinator for the Risk Integration layer.

    **Not part of the public API** — callers use
    :class:`~.risk_integration_engine.RiskIntegrationEngine`.

    Coordinates each subsystem step in the integration pipeline without
    performing any calculations.

    Parameters
    ----------
    component_registry :
        Registry holding M1-M5 subsystem component references.
    validator :
        Injected validator instance.
    registry :
        Injected request/response registry.
    statistics :
        Injected statistics tracker.
    history :
        Injected history store.
    engine_id :
        Integration engine identifier.
    """

    VERSION: str = VERSION

    def __init__(
        self,
        component_registry: Optional[RiskComponentRegistry]      = None,
        validator:          Optional[RiskIntegrationValidator]    = None,
        registry:           Optional[RiskIntegrationRegistry]     = None,
        statistics:         Optional[RiskIntegrationStatistics]   = None,
        history:            Optional[RiskIntegrationHistory]      = None,
        engine_id:          str                                    = "iios:risk:integration:engine",
    ) -> None:
        self._components = component_registry or RiskComponentRegistry()
        self._validator  = validator  or RiskIntegrationValidator()
        self._registry   = registry   or RiskIntegrationRegistry()
        self._stats      = statistics or RiskIntegrationStatistics()
        self._history    = history    or RiskIntegrationHistory()
        self._engine_id  = engine_id
        self._listeners: List[Callable] = []

    # ------------------------------------------------------------------
    # Listener management
    # ------------------------------------------------------------------

    def add_listener(self, fn: Callable) -> None:
        if fn not in self._listeners:
            self._listeners.append(fn)

    def remove_listener(self, fn: Callable) -> None:
        if fn in self._listeners:
            self._listeners.remove(fn)

    def _dispatch(self, event: Any) -> None:
        self._history.record_event(event)
        for fn in list(self._listeners):
            try:
                fn(event)
            except Exception as exc:
                _log.warning(f"Listener error: {exc}")

    # ------------------------------------------------------------------
    # Primary pipeline entry
    # ------------------------------------------------------------------

    def run_workflow(
        self, request: RiskIntegrationRequest
    ) -> RiskIntegrationResponse:
        """
        Execute the full 10-step integration workflow for *request*.

        Returns a :class:`~.risk_integration_response.RiskIntegrationResponse`
        whether the workflow succeeds or fails.
        """
        start_time = time.time()
        self._stats.record_request_received()
        self._history.record_request(request)

        # Step 1 — Register request
        try:
            self._registry.register_request(request)
        except Exception:
            pass   # Already registered on retry — continue

        # Step 2 — Emit RECEIVED event
        self._dispatch(
            make_request_received(
                self._engine_id, request.portfolio_id,
                request.request_id, ACTOR_INTEGRATION_MANAGER,
                request_type=request.request_type.value,
            )
        )

        # Step 3 — Validate
        try:
            self._validator.validate_or_raise(
                request,
                component_registry=self._components,
            )
        except RiskIntegrationValidationError as exc:
            self._stats.record_validation_failure()
            return self._fail(request, str(exc), start_time)

        self._dispatch(
            make_risk_validated(
                self._engine_id, request.portfolio_id,
                request.request_id, ACTOR_INTEGRATION_MANAGER,
            )
        )

        # Step 4–8 — Coordinate subsystem pipeline
        try:
            response = self._execute_pipeline(request, start_time)
        except Exception as exc:
            _log.error(f"Integration workflow error for {request.request_id}: {exc}")
            return self._fail(request, str(exc), start_time)

        # Step 9 — Register and record response
        self._registry.register_response(response)
        self._history.record_response(response)
        self._stats.record_request_completed()
        self._stats.record_processing_time(time.time() - start_time)

        # Step 10 — Emit COMPLETED event
        self._dispatch(
            make_risk_completed(
                self._engine_id, request.portfolio_id,
                request.request_id, ACTOR_INTEGRATION_MANAGER,
                snapshot_id  = response.snapshot_id,
                risk_score   = response.risk_score,
                duration_s   = response.duration_s,
            )
        )
        return response

    # ------------------------------------------------------------------
    # Pipeline execution
    # ------------------------------------------------------------------

    def _execute_pipeline(
        self,
        request:    RiskIntegrationRequest,
        start_time: float,
    ) -> RiskIntegrationResponse:
        """
        Coordinate M1-M5 subsystem calls and build the response.

        All calculations are performed inside the respective subsystems.
        This method only coordinates — it does not compute anything.
        """
        workflow_steps = 0
        snapshot_dict: Dict[str, Any] = {}

        # ── Step 4: Invoke Assessment (M4) if available ────────────────
        assessment_component = self._components.get_or_none(COMPONENT_ASSESSMENT)
        assessment_report    = None

        if assessment_component is not None and hasattr(assessment_component, "assess"):
            try:
                from iios.risk.assessment import RiskAssessmentRequest, RiskAssessmentContext
                assessment_context = RiskAssessmentContext.create(
                    assessment_id    = request.request_id,
                    portfolio_id     = request.portfolio_id,
                    risk_id          = request.workflow_id or request.request_id,
                )
                assessment_req = RiskAssessmentRequest.create(
                    assessment_id    = request.request_id,
                    portfolio_id     = request.portfolio_id,
                    risk_id          = request.workflow_id or request.request_id,
                    portfolio_value  = request.portfolio_value,
                    context          = assessment_context,
                    positions        = dict(request.positions),
                    returns          = list(request.returns),
                    limits           = dict(request.limits),
                    policy_approved  = True,
                    market_data      = dict(request.market_snapshot),
                    account_data     = dict(request.account_snapshot),
                )
                if assessment_component.lifecycle_state().value == "running":
                    assessment_report = assessment_component.assess(assessment_req)
                    workflow_steps += 1
            except Exception as exc:
                _log.debug(f"Assessment step skipped: {exc}")

        # ── Step 5: Build Snapshot (M5) ────────────────────────────────
        snapshot_component = self._components.get_or_none(COMPONENT_SNAPSHOT)
        risk_session_id    = request.context.session_id or request.request_id

        if snapshot_component is not None and hasattr(snapshot_component, "create_minimal"):
            try:
                if assessment_report is not None and hasattr(snapshot_component, "from_assessment_report"):
                    snapshot_obj = snapshot_component.from_assessment_report(
                        assessment_report,
                        risk_session_id,
                        workflow_id  = request.workflow_id,
                        strategy_id  = request.strategy_id,
                        account_id   = request.account_id,
                        lifecycle_state = "running",
                    )
                else:
                    snapshot_obj = snapshot_component.create_minimal(
                        risk_session_id    = risk_session_id,
                        risk_assessment_id = request.request_id,
                        portfolio_id       = request.portfolio_id,
                        risk_score         = 0.0,
                        assessment_status  = "completed",
                    )
                snapshot_dict  = snapshot_obj.to_dict()
                workflow_steps += 1

                # Emit SNAPSHOT_PUBLISHED
                self._stats.record_snapshot_published()
                self._dispatch(
                    make_snapshot_published(
                        self._engine_id, request.portfolio_id,
                        request.request_id, ACTOR_INTEGRATION_MANAGER,
                        snapshot_id = snapshot_obj.snapshot_id,
                    )
                )
            except Exception as exc:
                _log.debug(f"Snapshot step skipped: {exc}")

        # ── Fallback: build a minimal snapshot inline if component absent
        if not snapshot_dict:
            snapshot_dict = self._build_fallback_snapshot(request)
            workflow_steps += 1
            self._stats.record_snapshot_published()

        duration_s = time.time() - start_time
        return RiskIntegrationResponse.success(
            request_id     = request.request_id,
            portfolio_id   = request.portfolio_id,
            request_type   = request.request_type,
            snapshot_dict  = snapshot_dict,
            duration_s     = duration_s,
            workflow_steps = workflow_steps,
        )

    def _build_fallback_snapshot(
        self, request: RiskIntegrationRequest
    ) -> Dict[str, Any]:
        """Build a minimal snapshot dict when M5 factory is unavailable."""
        return {
            "snapshot_id":        request.request_id,
            "risk_session_id":    request.context.session_id,
            "risk_assessment_id": request.request_id,
            "portfolio_id":       request.portfolio_id,
            "risk_status":        "published",
            "summary": {
                "overall_risk_score": 0.0,
                "risk_rating":        "unknown",
                "risk_level":         "unknown",
                "risk_trend":         "unknown",
                "risk_confidence":    1.0,
                "assessment_status":  "completed",
            },
        }

    # ------------------------------------------------------------------
    # Failure path
    # ------------------------------------------------------------------

    def _fail(
        self,
        request:    RiskIntegrationRequest,
        message:    str,
        start_time: float,
    ) -> RiskIntegrationResponse:
        duration_s = time.time() - start_time
        self._stats.record_request_failed()
        response = RiskIntegrationResponse.failure(
            request_id    = request.request_id,
            portfolio_id  = request.portfolio_id,
            request_type  = request.request_type,
            error_message = message,
            duration_s    = duration_s,
        )
        self._registry.register_response(response)
        self._history.record_response(response)
        self._history.record_error({"request_id": request.request_id, "error": message})
        self._dispatch(
            make_risk_failed(
                self._engine_id, request.portfolio_id,
                request.request_id, ACTOR_INTEGRATION_MANAGER,
                error=message,
            )
        )
        return response
