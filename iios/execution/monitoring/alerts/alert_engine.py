"""iios/execution/monitoring/alerts/alert_engine.py
==================================================
AlertEngine — primary public API for the Execution Alert Framework.

Owns rules, policy evaluators, registry, factory, statistics, history,
and event dispatch.

IMPORTANT: The Alert Framework ONLY evaluates monitoring conditions and
generates alerts.  It MUST NOT compute metrics, block execution, execute
trades, or communicate with brokers.

C6 Execution Intelligence — Phase 6, Module 4
"""
from __future__ import annotations

import time
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .alert_context import AlertContext, make_alert_context
from .alert_events import (
    AlertEvent,
    make_alert_acknowledged,
    make_alert_escalated,
    make_alert_expired,
    make_alert_generated,
    make_alert_resolved,
    make_alert_suppressed,
)
from .alert_factory import AlertFactory
from .alert_history import AlertHistory
from .alert_policy import PolicyEvaluator, make_immediate_policy
from .alert_registry import AlertRegistry
from .alert_request import AlertRequest, make_alert_request
from .alert_response import AlertResponse, make_alert_response
from .alert_rule import Alert, AlertRule
from .alert_snapshot import AlertSnapshot
from .alert_statistics import AlertStatistics
from .alert_validation import AlertValidator
from .constants import (
    ENGINE_SYSTEM_ID,
    DEFAULT_MAX_ALERTS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_ESCALATIONS,
    AlertSeverity,
    AlertStatus,
    VERSION,
)
from .exceptions import (
    AlertEngineNotRunningError,
    AlertNotFoundError,
    AlertRuleEvaluationError,
    AlertRuleNotFoundError,
    AlertTransitionError,
    DuplicateAlertRuleError,
)

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__)


class AlertEngine(LifecycleAwareMixin):
    """
    Primary public API for the Execution Alert Framework.

    Usage
    -----
    engine = AlertEngine()
    engine.start()

    # Register rules
    engine.register_rule(HighLatencyRule())

    # Evaluate context (built from MetricsSnapshot)
    context  = make_alert_context("sess-1", "port-1", metrics)
    request  = engine.create_request("sess-1", context)
    response = engine.process_request(request)

    # Manage alerts
    engine.acknowledge(alert_id, actor="trader-1")
    engine.resolve(alert_id, actor="trader-1", notes="Fixed upstream")

    # Snapshot current state
    snap = engine.snapshot("sess-1", "port-1")

    engine.stop()
    """

    def __init__(
        self,
        max_alerts:  int = DEFAULT_MAX_ALERTS,
        max_history: int = DEFAULT_MAX_HISTORY,
    ) -> None:
        super().__init__()
        self._registry   = AlertRegistry(max_alerts=max_alerts)
        self._factory    = AlertFactory()
        self._validator  = AlertValidator()
        self._stats      = AlertStatistics()
        self._history    = AlertHistory(
            max_alerts=max_history,
            max_snapshots=max_history,
            max_events=max_history,
        )

        # Rule registry: rule_id → AlertRule
        self._rules: Dict[str, AlertRule]         = {}
        # Policy evaluator per rule_id
        self._evaluators: Dict[str, PolicyEvaluator] = {}
        self._rules_lock = threading.RLock()

        # Event listeners
        self._listeners:      List[Callable[[AlertEvent], None]] = []
        self._listeners_lock  = threading.Lock()

    # ── LifecycleAwareMixin hooks ──────────────────────────────────────────────

    def _on_start(self) -> None:
        self._registry.start()
        self._factory.start()
        _audit.log_lifecycle_event(
            ENGINE_SYSTEM_ID,
            EngineState.STOPPED,
            EngineState.RUNNING,
            VERSION,
        )
        _log.info(
            "AlertEngine started.",
            system_id=ENGINE_SYSTEM_ID,
            version=VERSION,
        )

    def _on_stop(self) -> None:
        self._factory.stop()
        self._registry.stop()
        _audit.log_lifecycle_event(
            ENGINE_SYSTEM_ID,
            EngineState.RUNNING,
            EngineState.STOPPED,
            VERSION,
        )
        _log.info(
            "AlertEngine stopped.",
            system_id=ENGINE_SYSTEM_ID,
            alerts_generated=self._stats.alerts_generated,
        )

    # ── Guard ─────────────────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in (EngineState.RUNNING, "running"):
            raise AlertEngineNotRunningError()

    # ── Rule management ───────────────────────────────────────────────────────

    def register_rule(self, rule: AlertRule) -> None:
        """Register an alert rule.  Raises DuplicateAlertRuleError if already registered."""
        self._assert_running()
        with self._rules_lock:
            if rule.rule_id in self._rules:
                raise DuplicateAlertRuleError(rule.rule_id)
            self._rules[rule.rule_id] = rule
            policy = getattr(rule, "policy", None) or make_immediate_policy()
            self._evaluators[rule.rule_id] = PolicyEvaluator(policy)
        _log.info("AlertRule registered.", rule_id=rule.rule_id, rule_name=rule.rule_name)

    def unregister_rule(self, rule_id: str) -> None:
        """Unregister a rule by ID.  Silent no-op if not found."""
        with self._rules_lock:
            self._rules.pop(rule_id, None)
            self._evaluators.pop(rule_id, None)

    def get_rule(self, rule_id: str) -> AlertRule:
        with self._rules_lock:
            rule = self._rules.get(rule_id)
        if rule is None:
            raise AlertRuleNotFoundError(rule_id)
        return rule

    def list_rules(self) -> List[AlertRule]:
        with self._rules_lock:
            return list(self._rules.values())

    def rule_count(self) -> int:
        with self._rules_lock:
            return len(self._rules)

    # ── Core evaluation API ───────────────────────────────────────────────────

    def create_request(
        self,
        session_id: str,
        context:    AlertContext,
        *,
        rule_ids: Tuple[str, ...] = (),
    ) -> AlertRequest:
        """Create a structured evaluation request."""
        self._assert_running()
        return self._factory.create_request(session_id, context, rule_ids=rule_ids)

    def process_request(self, request: AlertRequest) -> AlertResponse:
        """
        Evaluate the request against all (or specified) enabled rules.

        Returns an AlertResponse containing IDs of generated and suppressed alerts.
        """
        self._assert_running()
        t0     = time.perf_counter()
        errors: List[str] = []

        val_result = self._validator.validate_request(request)
        if not val_result.is_valid:
            err_msg = "; ".join(val_result.errors)
            _log.warning("AlertRequest validation failed.", errors=err_msg)
            self._stats.record_evaluation_failure()
            return make_alert_response(
                request.request_id, request.session_id, (),
                errors=(err_msg,),
                evaluation_duration_ms=0.0,
            )

        generated_ids:  List[str] = []
        suppressed_ids: List[str] = []

        with self._rules_lock:
            rules_to_run = (
                [self._rules[rid] for rid in request.rule_ids if rid in self._rules]
                if request.rule_ids
                else list(self._rules.values())
            )
            evaluators_snapshot = dict(self._evaluators)

        for rule in rules_to_run:
            if not rule.is_enabled():
                continue
            try:
                alert = rule.evaluate(request.context)
            except Exception as exc:
                msg = f"Rule '{rule.rule_id}' raised: {exc}"
                errors.append(msg)
                _log.warning(msg, rule_id=rule.rule_id)
                self._stats.record_evaluation_failure()
                continue

            if alert is None:
                # Condition not met — update policy state
                ev = evaluators_snapshot.get(rule.rule_id)
                if ev:
                    ev.should_fire(False)
                continue

            # Condition met — ask policy whether to fire
            ev = evaluators_snapshot.get(rule.rule_id)
            if ev and not ev.should_fire(True):
                # Suppress duplicate
                alert.suppress(reason="cooldown")
                suppressed_ids.append(alert.alert_id)
                self._stats.record_suppressed()
                ev_obj = make_alert_suppressed(
                    alert.session_id, alert.alert_id, reason="cooldown"
                )
                self._history.append_event(ev_obj)
                self._emit(ev_obj)
                continue

            # Store and emit
            self._registry.store(alert)
            generated_ids.append(alert.alert_id)
            self._stats.record_generated(alert.severity.value)

            ev_obj = make_alert_generated(alert.session_id, alert.alert_id)
            self._history.append_event(ev_obj)
            self._emit(ev_obj)
            _log.info(
                "Alert generated.",
                alert_id=alert.alert_id,
                alert_type=alert.alert_type.value,
                severity=alert.severity.value,
                session_id=alert.session_id,
            )

        duration_ms = (time.perf_counter() - t0) * 1_000
        self._stats.record_evaluation(duration_ms)

        return self._factory.create_response(
            request,
            tuple(generated_ids),
            alerts_suppressed      = tuple(suppressed_ids),
            evaluation_duration_ms = duration_ms,
            errors                 = tuple(errors),
        )

    # ── Alert management ──────────────────────────────────────────────────────

    def acknowledge(self, alert_id: str, actor: str, notes: str = "") -> Alert:
        """Acknowledge an active alert."""
        self._assert_running()
        alert = self._registry.get(alert_id)
        if alert.status != AlertStatus.ACTIVE:
            raise AlertTransitionError(alert_id, alert.status.value, AlertStatus.ACKNOWLEDGED.value)
        alert.acknowledge(actor, notes)
        self._registry.update(alert)
        self._stats.record_acknowledged()
        ev = make_alert_acknowledged(alert.session_id, alert_id, actor)
        self._history.append_event(ev)
        self._emit(ev)
        return alert

    def escalate(self, alert_id: str, actor: str = "engine") -> Alert:
        """Escalate an active or acknowledged alert."""
        self._assert_running()
        alert = self._registry.get(alert_id)
        if alert.status not in (AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED):
            raise AlertTransitionError(alert_id, alert.status.value, AlertStatus.ESCALATED.value)
        alert.escalate(actor)
        self._registry.update(alert)
        self._stats.record_escalated()
        ev = make_alert_escalated(alert.session_id, alert_id, actor)
        self._history.append_event(ev)
        self._emit(ev)
        return alert

    def resolve(self, alert_id: str, actor: str, notes: str = "") -> Alert:
        """Resolve an alert."""
        self._assert_running()
        alert = self._registry.get(alert_id)
        if alert.is_terminal():
            raise AlertTransitionError(alert_id, alert.status.value, AlertStatus.RESOLVED.value)
        alert.resolve(actor, notes)
        self._registry.update(alert)
        self._stats.record_resolved()
        # Move to history and remove from registry
        self._registry.remove(alert_id)
        self._history.append_alert(alert)
        ev = make_alert_resolved(alert.session_id, alert_id, actor, reason=notes or None)
        self._history.append_event(ev)
        self._emit(ev)
        # Reset policy evaluator so rule can fire again
        with self._rules_lock:
            for rule in self._rules.values():
                if rule.rule_id == alert.rule_id:
                    ev_obj = self._evaluators.get(rule.rule_id)
                    if ev_obj:
                        ev_obj.reset()
        return alert

    def suppress_alert(self, alert_id: str, reason: str = "", actor: str = "engine") -> Alert:
        """Suppress a duplicate/noise alert."""
        self._assert_running()
        alert = self._registry.get(alert_id)
        if alert.status != AlertStatus.ACTIVE:
            raise AlertTransitionError(alert_id, alert.status.value, AlertStatus.SUPPRESSED.value)
        alert.suppress(reason)
        self._registry.update(alert)
        self._stats.record_suppressed()
        ev = make_alert_suppressed(alert.session_id, alert_id, actor, reason=reason)
        self._history.append_event(ev)
        self._emit(ev)
        return alert

    def expire_stale_alerts(self, now: Optional[float] = None) -> List[str]:
        """
        Expire all alerts whose ``expires_at`` has passed.

        Returns the list of expired alert IDs.
        """
        self._assert_running()
        t = now or time.time()
        expired_ids: List[str] = []
        for alert in self._registry.all_alerts():
            if not alert.is_terminal() and alert.is_stale(t):
                alert.expire()
                self._registry.update(alert)
                self._registry.remove(alert.alert_id)
                self._history.append_alert(alert)
                self._stats.record_expired()
                ev = make_alert_expired(alert.session_id, alert.alert_id)
                self._history.append_event(ev)
                self._emit(ev)
                expired_ids.append(alert.alert_id)
        return expired_ids

    # ── Snapshot ──────────────────────────────────────────────────────────────

    def snapshot(
        self,
        session_id:   str,
        portfolio_id: str,
        *,
        gateway_id:  Optional[str] = None,
        strategy_id: Optional[str] = None,
    ) -> AlertSnapshot:
        """Build and return an immutable AlertSnapshot of the current state."""
        self._assert_running()
        alerts = self._registry.alerts_for_session(session_id)
        snap   = self._factory.create_snapshot(
            session_id, portfolio_id, alerts,
            gateway_id=gateway_id, strategy_id=strategy_id,
        )
        self._history.append_snapshot(snap)
        return snap

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_alert(self, alert_id: str) -> Alert:
        self._assert_running()
        return self._registry.get(alert_id)

    def find_alert(self, alert_id: str) -> Optional[Alert]:
        return self._registry.find(alert_id)

    def active_alerts(self) -> List[Alert]:
        self._assert_running()
        return self._registry.active_alerts()

    def alerts_for_session(self, session_id: str) -> List[Alert]:
        self._assert_running()
        return self._registry.alerts_for_session(session_id)

    def statistics(self) -> AlertStatistics:
        """Return a copy of the current statistics."""
        return self._stats.copy()

    def history(self) -> AlertHistory:
        return self._history

    # ── Event dispatch ────────────────────────────────────────────────────────

    def add_event_listener(self, listener: Callable[[AlertEvent], None]) -> None:
        with self._listeners_lock:
            self._listeners.append(listener)

    def remove_event_listener(self, listener: Callable[[AlertEvent], None]) -> None:
        with self._listeners_lock:
            self._listeners = [l for l in self._listeners if l != listener]

    def _emit(self, event: AlertEvent) -> None:
        with self._listeners_lock:
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception as exc:
                _log.warning(
                    "Alert event listener raised.",
                    listener=repr(listener),
                    error=str(exc),
                )
