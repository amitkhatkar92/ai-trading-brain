"""
iios/execution/recovery/failover/failover_controller.py
=======================================================
FailoverController — orchestrates the 8-step failover execution workflow.

Steps:
  1. Receive Recovery Decision  (done in engine before controller is called)
  2. Validate Failover Plan     → VALIDATION phase
  3. Verify Resource Availability → RESOURCE_CHECK phase
  4. Prepare Recovery Environment → PREPARATION phase
  5. Execute Failover             → EXECUTION phase
  6. Verify Recovery Success      → VERIFICATION phase
  7. Restore Operational State    → RESTORATION phase
  8. Publish Result               → COMPLETION phase (done in engine after)

C7 Execution Recovery & Resilience — Phase 1, Module 4
"""
from __future__ import annotations

import time
from typing import Any, Optional

from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    CONTROLLER_ID,
    VERSION,
    FailoverAction,
    FailoverPhase,
    FailoverStatus,
)
from .exceptions import (
    FailoverNotRunningError,
    FailoverPlanNotFoundError,
)
from .failover_executor import FailoverExecutor
from .failover_health_monitor import FailoverHealthMonitor
from .failover_plan import FailoverPlan
from .failover_request import FailoverRequest
from .failover_response import FailoverResponse, make_failover_response, make_failover_result
from .failover_strategy_registry import FailoverStrategyRegistry
from .failover_validation import FailoverValidator
from .failover_verifier import FailoverVerifier

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__)


class FailoverController(LifecycleAwareMixin):
    """
    Lifecycle-aware controller that runs the full failover workflow.

    Owns FailoverExecutor, FailoverVerifier, FailoverHealthMonitor,
    FailoverValidator.  Delegates to FailoverStrategyRegistry for plan lookup.
    """

    def __init__(self, strategy_registry: FailoverStrategyRegistry) -> None:
        super().__init__()
        self._registry  = strategy_registry
        self._validator = FailoverValidator()
        self._monitor   = FailoverHealthMonitor()
        self._executor  = FailoverExecutor()
        self._verifier  = FailoverVerifier()

    def _on_start(self) -> None:
        self._monitor.start()
        self._executor.start()
        self._verifier.start()
        _audit.log_lifecycle_event(CONTROLLER_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION)
        _log.info("FailoverController started")

    def _on_stop(self) -> None:
        self._verifier.stop()
        self._executor.stop()
        self._monitor.stop()
        _audit.log_lifecycle_event(CONTROLLER_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION)
        _log.info("FailoverController stopped")

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in (EngineState.RUNNING, "running"):
            raise FailoverNotRunningError()

    # ── Primary workflow entry ────────────────────────────────────────────────

    def execute_failover(self, request: FailoverRequest) -> FailoverResponse:
        """
        Run the full 7-phase execution workflow for *request*.
        Returns a FailoverResponse (phase 8 / publish is handled by the engine).
        """
        self._assert_running()
        start_ns   = time.perf_counter_ns()
        context    = request.context
        phases_run = []

        # ── Phase 2: Validate ─────────────────────────────────────────────────
        phases_run.append(FailoverPhase.VALIDATION)
        vr = self._validator.validate_request(request)
        if not vr.is_valid:
            _log.warning(
                "Failover request validation failed",
                session=request.failover_session_id,
                errors=vr.errors,
            )

        # ── Phase 3: Resource check ───────────────────────────────────────────
        phases_run.append(FailoverPhase.RESOURCE_CHECK)
        avail_report = self._monitor.check_resource_availability(context)
        resource_vr  = self._validator.validate_resource_availability(context)

        if not resource_vr.is_valid:
            _log.warning(
                "Resource unavailable for failover; proceeding to best-effort execution",
                session=request.failover_session_id,
                errors=resource_vr.errors,
            )

        # ── Look up plan ──────────────────────────────────────────────────────
        plan = self._registry.find_plan(request.primary_action)
        if plan is None:
            _log.warning(
                "No plan found; using manual escalation fallback",
                action=request.primary_action.value,
            )
            plan = self._registry.get_plan(FailoverAction.MANUAL_ESCALATION)

        plan_vr = self._validator.validate_plan(plan)
        if not plan_vr.is_valid:
            _log.warning("Plan validation failed", errors=plan_vr.errors)

        # ── Phase 4: Preparation ──────────────────────────────────────────────
        if FailoverPhase.PREPARATION in plan.phases:
            phases_run.append(FailoverPhase.PREPARATION)
            _log.debug("Failover preparation complete", session=request.failover_session_id)

        # ── Phase 5: Execute ──────────────────────────────────────────────────
        phases_run.append(FailoverPhase.EXECUTION)
        result = self._executor.execute(plan, context)

        # ── Phase 6: Verify ───────────────────────────────────────────────────
        verification_report = None
        if plan.requires_verification:
            phases_run.append(FailoverPhase.VERIFICATION)
            verification_report = self._verifier.verify(
                context, result, plan.verification_checks
            )

        # ── Phase 7: Restoration ──────────────────────────────────────────────
        if FailoverPhase.RESTORATION in plan.phases and result.is_successful:
            phases_run.append(FailoverPhase.RESTORATION)
            _log.debug("Operational state restored", session=request.failover_session_id)

        # ── Phase 8 / Completion (build response) ─────────────────────────────
        phases_run.append(FailoverPhase.COMPLETION)
        elapsed_ms = (time.perf_counter_ns() - start_ns) / 1e6

        response = make_failover_response(
            request_id          = request.request_id,
            failover_session_id = request.failover_session_id,
            source_decision_id  = request.source_decision_id,
            result              = result,
            verification_report = verification_report,
            response_time_ms    = elapsed_ms,
        )

        _log.info(
            "Failover workflow complete",
            session=request.failover_session_id,
            action=result.action_executed.value,
            success=result.is_successful,
            operational=response.is_operational,
            elapsed_ms=f"{elapsed_ms:.2f}",
        )
        return response

    # ── Accessors ─────────────────────────────────────────────────────────────

    @property
    def health_monitor(self) -> FailoverHealthMonitor:
        return self._monitor

    @property
    def executor(self) -> FailoverExecutor:
        return self._executor

    @property
    def verifier(self) -> FailoverVerifier:
        return self._verifier
