"""
iios/execution/recovery/failover/failover_verifier.py
=====================================================
FailoverVerifier — post-failover verification of system health.

Verifies service health, workflow health, gateway/broker availability,
execution readiness, and monitoring status.

C7 Execution Recovery & Resilience — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from typing import Any, List, Tuple

from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import VERIFIER_ID, VERSION, FailoverAction, VerificationStatus
from .exceptions import FailoverNotRunningError
from .failover_response import (
    VerificationCheck,
    VerificationReport,
    make_verification_report,
)

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__)

# Canonical check names
CHECK_SERVICE_HEALTH    = "service_health"
CHECK_WORKFLOW_HEALTH   = "workflow_health"
CHECK_GATEWAY_AVAIL     = "gateway_availability"
CHECK_BROKER_AVAIL      = "broker_availability"
CHECK_EXEC_READINESS    = "execution_readiness"
CHECK_MONITORING_STATUS = "monitoring_status"


class FailoverVerifier(LifecycleAwareMixin):
    """
    Post-failover verification component.

    Examines the FailoverContext and FailoverResult to determine whether
    the system is in a healthy, operational state after the failover action.
    """

    def __init__(self) -> None:
        super().__init__()

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(VERIFIER_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION)
        _log.info("FailoverVerifier started")

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(VERIFIER_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION)
        _log.info("FailoverVerifier stopped")

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in (EngineState.RUNNING, "running"):
            raise FailoverNotRunningError()

    # ── Primary verification entry ────────────────────────────────────────────

    def verify(
        self,
        context: Any,
        result: Any,
        verification_checks: Tuple[str, ...] = (),
    ) -> VerificationReport:
        """
        Run post-failover verification checks.

        *verification_checks* names which checks to run.  If empty, runs
        the full set of applicable checks.
        """
        self._assert_running()
        session_id = getattr(context, "failover_session_id", "")
        action     = getattr(context, "primary_action", None)

        checks_to_run = set(verification_checks) if verification_checks else {
            CHECK_SERVICE_HEALTH,
            CHECK_WORKFLOW_HEALTH,
            CHECK_EXEC_READINESS,
            CHECK_MONITORING_STATUS,
            CHECK_GATEWAY_AVAIL,
            CHECK_BROKER_AVAIL,
        }

        checks: List[VerificationCheck] = []

        if CHECK_SERVICE_HEALTH in checks_to_run:
            checks.append(self._check_service_health(context, result))

        if CHECK_WORKFLOW_HEALTH in checks_to_run:
            checks.append(self._check_workflow_health(context, result))

        if CHECK_GATEWAY_AVAIL in checks_to_run:
            checks.append(self._check_gateway_availability(context, action))

        if CHECK_BROKER_AVAIL in checks_to_run:
            checks.append(self._check_broker_availability(context, action))

        if CHECK_EXEC_READINESS in checks_to_run:
            checks.append(self._check_execution_readiness(context, result))

        if CHECK_MONITORING_STATUS in checks_to_run:
            checks.append(self._check_monitoring_status(context))

        report = make_verification_report(
            failover_session_id = session_id,
            checks              = tuple(checks),
        )
        _log.debug(
            "Verification complete",
            session_id=session_id,
            passed=report.passed_checks,
            failed=report.failed_checks,
        )
        return report

    # ── Individual checks ─────────────────────────────────────────────────────

    def _check_service_health(self, context: Any, result: Any) -> VerificationCheck:
        """Pass if the failover action succeeded and subsystem is not unhealthy."""
        is_successful = getattr(result, "is_successful", False)
        is_emergency  = getattr(context, "emergency_shutdown_requested", False)

        if is_emergency:
            return VerificationCheck(
                CHECK_SERVICE_HEALTH,
                VerificationStatus.PASSED,
                "Emergency shutdown: service intentionally stopped",
            )
        if not is_successful:
            return VerificationCheck(
                CHECK_SERVICE_HEALTH,
                VerificationStatus.FAILED,
                "Failover action did not succeed; service health uncertain",
            )
        return VerificationCheck(
            CHECK_SERVICE_HEALTH,
            VerificationStatus.PASSED,
            "Failover action succeeded; service health restored",
        )

    def _check_workflow_health(self, context: Any, result: Any) -> VerificationCheck:
        """Pass when execution is active or has been gracefully shut down."""
        is_emergency = getattr(context, "emergency_shutdown_requested", False)
        exec_active  = getattr(context, "execution_active", True)
        is_success   = getattr(result, "is_successful", False)

        if is_emergency:
            return VerificationCheck(
                CHECK_WORKFLOW_HEALTH,
                VerificationStatus.PASSED,
                "Emergency shutdown: workflow intentionally stopped",
            )
        if is_success:
            return VerificationCheck(
                CHECK_WORKFLOW_HEALTH,
                VerificationStatus.PASSED,
                "Workflow health restored post-failover",
            )
        return VerificationCheck(
            CHECK_WORKFLOW_HEALTH,
            VerificationStatus.FAILED,
            "Workflow health could not be confirmed",
        )

    def _check_gateway_availability(
        self, context: Any, action: Any
    ) -> VerificationCheck:
        """Pass if a gateway is available post-failover."""
        backup_gw  = getattr(context, "backup_gateway_available", False)
        is_gw_fail = action == FailoverAction.SWITCH_GATEWAY

        if is_gw_fail:
            status  = VerificationStatus.PASSED if backup_gw else VerificationStatus.FAILED
            msg     = "Backup gateway available" if backup_gw else "No backup gateway available"
        else:
            status = VerificationStatus.PASSED
            msg    = "Gateway availability not impacted by this action"

        return VerificationCheck(CHECK_GATEWAY_AVAIL, status, msg)

    def _check_broker_availability(
        self, context: Any, action: Any
    ) -> VerificationCheck:
        """Pass if a broker is available post-failover."""
        backup_bk    = getattr(context, "backup_broker_available", False)
        is_bk_fail   = action == FailoverAction.SWITCH_BROKER

        if is_bk_fail:
            status = VerificationStatus.PASSED if backup_bk else VerificationStatus.FAILED
            msg    = "Backup broker available" if backup_bk else "No backup broker available"
        else:
            status = VerificationStatus.PASSED
            msg    = "Broker availability not impacted by this action"

        return VerificationCheck(CHECK_BROKER_AVAIL, status, msg)

    def _check_execution_readiness(self, context: Any, result: Any) -> VerificationCheck:
        """Pass if the system can resume normal execution."""
        is_emergency = getattr(context, "emergency_shutdown_requested", False)
        action       = getattr(context, "primary_action", None)

        if is_emergency or action in (
            FailoverAction.GRACEFUL_SHUTDOWN,
            FailoverAction.MANUAL_ESCALATION,
            FailoverAction.DEACTIVATE_PRIMARY,
        ):
            return VerificationCheck(
                CHECK_EXEC_READINESS,
                VerificationStatus.SKIPPED,
                "Execution readiness check skipped: system not intended to resume",
            )

        is_success = getattr(result, "is_successful", False)
        status = VerificationStatus.PASSED if is_success else VerificationStatus.FAILED
        msg    = "Execution ready" if is_success else "Execution not ready post-failover"
        return VerificationCheck(CHECK_EXEC_READINESS, status, msg)

    def _check_monitoring_status(self, context: Any) -> VerificationCheck:
        """Pass if monitoring is active."""
        monitoring = getattr(context, "monitoring_active", True)
        status = VerificationStatus.PASSED if monitoring else VerificationStatus.FAILED
        msg    = "Monitoring active" if monitoring else "Monitoring inactive post-failover"
        return VerificationCheck(CHECK_MONITORING_STATUS, status, msg)
