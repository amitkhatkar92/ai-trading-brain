"""
iios/execution/recovery/failover/failover_health_monitor.py
===========================================================
FailoverHealthMonitor — assesses resource and subsystem health before
and after failover execution.

C7 Execution Recovery & Resilience — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ENGINE_ID,
    VERIFIER_ID,
    VERSION,
    FailoverAction,
    HealthStatus,
)
from .exceptions import FailoverNotRunningError

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__)


@dataclass(frozen=True)
class ResourceAvailabilityReport:
    """Report of available resources for failover."""

    report_id:              str
    failover_session_id:    str
    backup_broker_available: bool
    backup_gateway_available: bool
    rollback_available:      bool
    restart_available:       bool
    monitoring_active:       bool
    primary_healthy:         bool
    overall_health:          HealthStatus
    checked_at:              float
    notes:                   Tuple[str, ...]  = ()
    version:                 str              = VERSION

    @property
    def has_any_backup(self) -> bool:
        return self.backup_broker_available or self.backup_gateway_available

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":               self.report_id,
            "failover_session_id":     self.failover_session_id,
            "backup_broker_available": self.backup_broker_available,
            "backup_gateway_available": self.backup_gateway_available,
            "rollback_available":      self.rollback_available,
            "restart_available":       self.restart_available,
            "monitoring_active":       self.monitoring_active,
            "primary_healthy":         self.primary_healthy,
            "overall_health":          self.overall_health.value,
            "has_any_backup":          self.has_any_backup,
        }


class FailoverHealthMonitor(LifecycleAwareMixin):
    """
    Lifecycle-aware health monitor for the Failover Framework.

    Assesses resource availability from the FailoverContext and returns
    structured health reports used by the controller for gate decisions.
    """

    def __init__(self) -> None:
        super().__init__()

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(VERIFIER_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION)
        _log.info("FailoverHealthMonitor started")

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(VERIFIER_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION)
        _log.info("FailoverHealthMonitor stopped")

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in (EngineState.RUNNING, "running"):
            raise FailoverNotRunningError()

    # ── Resource availability ─────────────────────────────────────────────────

    def check_resource_availability(
        self, context: Any
    ) -> ResourceAvailabilityReport:
        """
        Build a ResourceAvailabilityReport from the FailoverContext.

        Reads context fields; does not communicate with external systems.
        """
        self._assert_running()
        notes = []

        backup_broker   = bool(getattr(context, "backup_broker_available", False))
        backup_gateway  = bool(getattr(context, "backup_gateway_available", False))
        rollback        = bool(getattr(context, "rollback_available", False))
        restart         = bool(getattr(context, "restart_available", True))
        monitoring      = bool(getattr(context, "monitoring_active", True))
        primary_healthy = bool(getattr(context, "primary_subsystem_healthy", True))
        action          = getattr(context, "primary_action", None)

        # Assess overall health for this action
        if action == FailoverAction.SWITCH_BROKER and not backup_broker:
            notes.append("No backup broker; SWITCH_BROKER may fail")
        if action == FailoverAction.SWITCH_GATEWAY and not backup_gateway:
            notes.append("No backup gateway; SWITCH_GATEWAY may fail")
        if action == FailoverAction.ROLLBACK and not rollback:
            notes.append("No rollback state; ROLLBACK may fail")

        if getattr(context, "emergency_shutdown_requested", False):
            overall = HealthStatus.UNHEALTHY
            notes.append("Emergency shutdown requested")
        elif not primary_healthy and not backup_broker and not backup_gateway:
            overall = HealthStatus.UNHEALTHY
        elif not primary_healthy:
            overall = HealthStatus.DEGRADED
        elif not monitoring:
            overall = HealthStatus.DEGRADED
            notes.append("Monitoring inactive")
        else:
            overall = HealthStatus.HEALTHY

        return ResourceAvailabilityReport(
            report_id               = str(uuid.uuid4()),
            failover_session_id     = getattr(context, "failover_session_id", ""),
            backup_broker_available  = backup_broker,
            backup_gateway_available = backup_gateway,
            rollback_available       = rollback,
            restart_available        = restart,
            monitoring_active        = monitoring,
            primary_healthy          = primary_healthy,
            overall_health           = overall,
            checked_at               = time.time(),
            notes                    = tuple(notes),
        )

    # ── Subsystem health ──────────────────────────────────────────────────────

    def assess_context_health(self, context: Any) -> HealthStatus:
        """Quick overall health assessment from context fields."""
        if getattr(context, "emergency_shutdown_requested", False):
            return HealthStatus.UNHEALTHY
        if not getattr(context, "is_within_risk_limits", True):
            return HealthStatus.UNHEALTHY
        if not getattr(context, "primary_subsystem_healthy", True):
            return HealthStatus.DEGRADED
        if not getattr(context, "monitoring_active", True):
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY
