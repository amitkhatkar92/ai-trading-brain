"""iios/execution/monitoring/alerts/alert_manager.py
==================================================
AlertManager — LifecycleAwareMixin orchestration layer above AlertEngine.

Provides session-scoped alert management, bulk operations, and
auto-escalation support.

C6 Execution Intelligence — Phase 6, Module 4
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional, Tuple

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .alert_context import AlertContext
from .alert_engine import AlertEngine
from .alert_events import AlertEvent
from .alert_rule import Alert, AlertRule
from .alert_snapshot import AlertSnapshot
from .alert_statistics import AlertStatistics
from .constants import (
    MANAGER_SYSTEM_ID,
    DEFAULT_MAX_ALERTS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_ESCALATIONS,
    AlertSeverity,
    AlertStatus,
    VERSION,
    SEVERITY_WEIGHT,
)
from .exceptions import AlertEngineNotRunningError

_log = get_logger(__name__)


class AlertManager(LifecycleAwareMixin):
    """
    Session-scoped alert orchestration layer.

    Delegates evaluation and lifecycle operations to AlertEngine and adds:
    - Auto-escalation of unacknowledged alerts older than a threshold
    - Bulk rule registration from default rule set
    - Per-session summary queries
    - Periodic maintenance (expire stale, auto-escalate)
    """

    def __init__(
        self,
        max_alerts:         int   = DEFAULT_MAX_ALERTS,
        max_history:        int   = DEFAULT_MAX_HISTORY,
        escalation_age_sec: float = 300.0,
        max_escalations:    int   = DEFAULT_MAX_ESCALATIONS,
    ) -> None:
        super().__init__()
        self._engine             = AlertEngine(max_alerts=max_alerts, max_history=max_history)
        self._escalation_age_sec = escalation_age_sec
        self._max_escalations    = max_escalations

    # ── LifecycleAwareMixin hooks ──────────────────────────────────────────────

    def _on_start(self) -> None:
        self._engine.start()
        _log.info("AlertManager started.", system_id=MANAGER_SYSTEM_ID, version=VERSION)

    def _on_stop(self) -> None:
        self._engine.stop()
        _log.info("AlertManager stopped.", system_id=MANAGER_SYSTEM_ID)

    # ── Guard ─────────────────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in (EngineState.RUNNING, "running"):
            raise AlertEngineNotRunningError()

    # ── Rule management ───────────────────────────────────────────────────────

    def register_rule(self, rule: AlertRule) -> None:
        """Register a single alert rule."""
        self._assert_running()
        self._engine.register_rule(rule)

    def register_rules(self, rules: List[AlertRule]) -> None:
        """Register multiple rules at once."""
        self._assert_running()
        for rule in rules:
            self._engine.register_rule(rule)

    def register_default_rules(self) -> None:
        """Register all 10 built-in rules with default thresholds."""
        from .alert_rule import (
            BrokerUnavailableRule,
            ExecutionFailureRateRule,
            GatewayDegradedRule,
            HighLatencyRule,
            MonitoringFailureRule,
            QueueCongestionRule,
            ResourceExhaustionRule,
            RetryThresholdExceededRule,
            SubsystemUnhealthyRule,
            TimeoutThresholdExceededRule,
        )
        defaults = [
            HighLatencyRule(),
            QueueCongestionRule(),
            ExecutionFailureRateRule(),
            BrokerUnavailableRule(),
            GatewayDegradedRule(),
            RetryThresholdExceededRule(),
            TimeoutThresholdExceededRule(),
            MonitoringFailureRule(),
            ResourceExhaustionRule(),
            SubsystemUnhealthyRule(),
        ]
        self.register_rules(defaults)

    def unregister_rule(self, rule_id: str) -> None:
        self._engine.unregister_rule(rule_id)

    def list_rules(self) -> List[AlertRule]:
        return self._engine.list_rules()

    # ── Evaluation ────────────────────────────────────────────────────────────

    def evaluate(self, context: AlertContext) -> List[Alert]:
        """
        Evaluate all enabled rules against ``context``.

        Returns a list of newly generated Alert objects.
        """
        self._assert_running()
        request  = self._engine.create_request(context.session_id, context)
        response = self._engine.process_request(request)
        alerts   = []
        for aid in response.alerts_generated:
            alert = self._engine.find_alert(aid)
            if alert:
                alerts.append(alert)
        return alerts

    # ── Alert lifecycle ───────────────────────────────────────────────────────

    def acknowledge(self, alert_id: str, actor: str, notes: str = "") -> Alert:
        self._assert_running()
        return self._engine.acknowledge(alert_id, actor, notes)

    def escalate(self, alert_id: str, actor: str = "manager") -> Alert:
        self._assert_running()
        return self._engine.escalate(alert_id, actor)

    def resolve(self, alert_id: str, actor: str, notes: str = "") -> Alert:
        self._assert_running()
        return self._engine.resolve(alert_id, actor, notes)

    def suppress_alert(self, alert_id: str, reason: str = "") -> Alert:
        self._assert_running()
        return self._engine.suppress_alert(alert_id, reason)

    # ── Maintenance ───────────────────────────────────────────────────────────

    def run_maintenance(self, now: Optional[float] = None) -> Dict[str, int]:
        """
        Run periodic maintenance:
        1. Expire stale alerts
        2. Auto-escalate unacknowledged alerts older than escalation_age_sec

        Returns a dict with counts of expired and escalated alerts.
        """
        self._assert_running()
        t = now or time.time()

        expired    = self._engine.expire_stale_alerts(t)
        escalated: List[str] = []

        for alert in self._engine.active_alerts():
            if alert.status == AlertStatus.ACTIVE:
                age = t - alert.detected_at
                if (
                    age >= self._escalation_age_sec
                    and alert.escalation_count < self._max_escalations
                    and alert.severity in (AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY)
                ):
                    try:
                        self._engine.escalate(alert.alert_id, actor="auto-escalation")
                        escalated.append(alert.alert_id)
                    except Exception:
                        pass

        return {"expired": len(expired), "escalated": len(escalated)}

    # ── Snapshot ──────────────────────────────────────────────────────────────

    def snapshot(
        self,
        session_id:   str,
        portfolio_id: str,
        *,
        gateway_id:  Optional[str] = None,
        strategy_id: Optional[str] = None,
    ) -> AlertSnapshot:
        self._assert_running()
        return self._engine.snapshot(
            session_id, portfolio_id,
            gateway_id=gateway_id, strategy_id=strategy_id,
        )

    # ── Queries ───────────────────────────────────────────────────────────────

    def active_alerts(self) -> List[Alert]:
        self._assert_running()
        return self._engine.active_alerts()

    def alerts_for_session(self, session_id: str) -> List[Alert]:
        self._assert_running()
        return self._engine.alerts_for_session(session_id)

    def statistics(self) -> AlertStatistics:
        return self._engine.statistics()

    def engine(self) -> AlertEngine:
        """Expose underlying engine for direct access."""
        return self._engine
