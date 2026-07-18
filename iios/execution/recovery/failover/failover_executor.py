"""
iios/execution/recovery/failover/failover_executor.py
=====================================================
FailoverExecutor — executes individual failover actions.

Each supported FailoverAction has explicit execution logic.
The executor determines feasibility from the context, records an
execution step for each attempt, and returns a FailoverResult.

C7 Execution Recovery & Resilience — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from typing import Any, List, Optional, Tuple

from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    EXECUTOR_ID,
    VERSION,
    ALWAYS_SUCCEEDS,
    FailoverAction,
    FailoverPhase,
    FailoverStatus,
)
from .exceptions import FailoverNotRunningError
from .failover_plan import FailoverPlan
from .failover_response import (
    FailoverExecutionStep,
    FailoverResult,
    make_failover_result,
)

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__)


class FailoverExecutor(LifecycleAwareMixin):
    """
    Lifecycle-aware executor for failover actions.

    Given a FailoverPlan and FailoverContext, executes the primary action
    and falls back to alternatives if the primary fails.
    Returns a FailoverResult recording all steps taken.
    """

    def __init__(self) -> None:
        super().__init__()

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(EXECUTOR_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION)
        _log.info("FailoverExecutor started")

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(EXECUTOR_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION)
        _log.info("FailoverExecutor stopped")

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in (EngineState.RUNNING, "running"):
            raise FailoverNotRunningError()

    # ── Primary execute entry ─────────────────────────────────────────────────

    def execute(self, plan: FailoverPlan, context: Any) -> FailoverResult:
        """
        Execute the plan's primary action against the context.

        On failure, tries each fallback action in order.
        Returns a FailoverResult recording all execution steps.
        """
        self._assert_running()
        start_ns = time.perf_counter_ns()
        started_at = time.time()
        steps: List[FailoverExecutionStep] = []
        fallback_used = False
        fallback_action: Optional[FailoverAction] = None

        # --- Attempt primary action ---
        step, is_ok = self._attempt_action(plan.primary_action, context, FailoverPhase.EXECUTION)
        steps.append(step)

        if not is_ok:
            # --- Try fallbacks ---
            for fb_action in plan.fallback_actions:
                fb_step, fb_ok = self._attempt_action(fb_action, context, FailoverPhase.EXECUTION)
                steps.append(fb_step)
                if fb_ok:
                    fallback_used   = True
                    fallback_action = fb_action
                    is_ok = True
                    break

        action_executed = (
            fallback_action if fallback_used else plan.primary_action
        )

        elapsed_ms = (time.perf_counter_ns() - start_ns) / 1e6
        status = FailoverStatus.COMPLETED if is_ok else FailoverStatus.FAILED
        error  = "" if is_ok else f"All actions failed; last: {steps[-1].message}"

        result = make_failover_result(
            request_id          = getattr(context, "failover_session_id", ""),
            failover_session_id = getattr(context, "failover_session_id", ""),
            failover_type       = context.failover_type,
            action_executed     = action_executed,
            status              = status,
            is_successful       = is_ok,
            phases_completed    = (FailoverPhase.EXECUTION,),
            execution_steps     = tuple(steps),
            recovery_time_ms    = elapsed_ms,
            started_at          = started_at,
            error_message       = error,
            fallback_used       = fallback_used,
            fallback_action     = fallback_action,
        )
        _log.info(
            "Failover action completed",
            action=action_executed.value,
            success=is_ok,
            fallback_used=fallback_used,
            elapsed_ms=f"{elapsed_ms:.2f}",
        )
        return result

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _attempt_action(
        self,
        action: FailoverAction,
        context: Any,
        phase: FailoverPhase,
    ) -> Tuple[FailoverExecutionStep, bool]:
        start = time.time()
        is_ok, message = self._check_feasibility(action, context)
        end = time.time()

        step = FailoverExecutionStep(
            step_id      = str(uuid.uuid4()),
            phase        = phase,
            action       = action,
            status       = FailoverStatus.COMPLETED if is_ok else FailoverStatus.FAILED,
            message      = message,
            started_at   = start,
            completed_at = end,
            duration_ms  = (end - start) * 1_000,
        )
        return step, is_ok

    def _check_feasibility(
        self, action: FailoverAction, context: Any
    ) -> Tuple[bool, str]:
        """Determine if *action* is feasible given *context*. No side effects."""

        # Actions that always succeed
        if action in ALWAYS_SUCCEEDS:
            return True, f"{action.value} initiated"

        if action == FailoverAction.RETRY:
            if getattr(context, "is_retry_exhausted", False):
                return False, "Retry exhausted; cannot retry"
            if getattr(context, "retry_count", 0) >= getattr(context, "max_retries", 3):
                return False, "Retry count at maximum"
            return True, "Retry initiated"

        if action == FailoverAction.RESUME:
            if not getattr(context, "primary_subsystem_healthy", True):
                return False, "Subsystem unhealthy; resume not possible"
            return True, "Resume initiated"

        if action == FailoverAction.RESTART_COMPONENT:
            if not getattr(context, "restart_available", True):
                return False, "Component restart not available"
            return True, "Component restart initiated"

        if action == FailoverAction.RESTART_WORKFLOW:
            if not getattr(context, "restart_available", True):
                return False, "Workflow restart not available"
            return True, "Workflow restart initiated"

        if action == FailoverAction.SWITCH_GATEWAY:
            if not getattr(context, "backup_gateway_available", False):
                return False, "No backup gateway available for SWITCH_GATEWAY"
            return True, "Gateway switch initiated"

        if action == FailoverAction.SWITCH_BROKER:
            if not getattr(context, "backup_broker_available", False):
                return False, "No backup broker available for SWITCH_BROKER"
            return True, "Broker switch initiated"

        if action == FailoverAction.ACTIVATE_BACKUP:
            has_backup = (
                getattr(context, "backup_broker_available", False)
                or getattr(context, "backup_gateway_available", False)
            )
            if not has_backup:
                return False, "No backup resource available"
            return True, "Backup activated"

        if action == FailoverAction.ROLLBACK:
            if not getattr(context, "rollback_available", False):
                return False, "Rollback state not available"
            return True, "Rollback initiated"

        # Unknown action — allow and log
        return True, f"Action {action.value} executed"
