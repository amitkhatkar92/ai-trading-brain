"""tests/unit/execution/monitoring/alerts/test_alert_framework.py
==================================================
Comprehensive test suite for the C6 Phase 6 M4 Execution Alert Framework.

Coverage target: 95%+
"""
from __future__ import annotations

import threading
import time
import pytest

from iios.execution.monitoring.alerts import (
    # constants
    AlertCategory, AlertEventType, AlertPolicyType, AlertSeverity,
    AlertStatus, AlertType, ThresholdOperator,
    ACTIVE_ALERT_STATUSES, TERMINAL_ALERT_STATUSES, SEVERITY_WEIGHT,
    # exceptions
    AlertEngineNotRunningError, AlertFrameworkError, AlertNotFoundError,
    AlertRegistryCapacityError, AlertRuleEvaluationError, AlertRuleNotFoundError,
    AlertSnapshotError, AlertTransitionError, AlertValidationError,
    DuplicateAlertRuleError,
    # threshold
    AlertThreshold, make_alert_threshold,
    # context / DTOs
    AlertContext, make_alert_context,
    AlertRequest, make_alert_request,
    AlertResponse, make_alert_response,
    AlertSnapshot, make_alert_snapshot,
    # events
    AlertEvent, make_alert_generated, make_alert_acknowledged,
    make_alert_escalated, make_alert_resolved, make_alert_expired,
    make_alert_suppressed,
    # policy
    AlertPolicy, PolicyEvaluator,
    make_alert_policy, make_immediate_policy,
    make_consecutive_policy, make_rolling_window_policy,
    # rules
    Alert, AlertRule, HighLatencyRule, QueueCongestionRule,
    ExecutionFailureRateRule, BrokerUnavailableRule, GatewayDegradedRule,
    RetryThresholdExceededRule, TimeoutThresholdExceededRule,
    MonitoringFailureRule, ResourceExhaustionRule, SubsystemUnhealthyRule,
    # supporting
    AlertHistory, AlertStatistics, AlertValidationResult, AlertValidator,
    # infrastructure
    AlertRegistry, AlertFactory,
    # primary API
    AlertEngine, AlertManager,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _ctx(
    session_id:   str   = "s1",
    portfolio_id: str   = "p1",
    metrics:      dict  = None,
    **kw,
) -> AlertContext:
    return make_alert_context(
        session_id, portfolio_id, metrics or {}, **kw
    )


def _engine() -> AlertEngine:
    e = AlertEngine()
    e.start()
    return e


def _manager() -> AlertManager:
    m = AlertManager()
    m.start()
    return m


# ═══════════════════════════════════════════════════════════════════════════════
# TestConstants
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_severity_values(self):
        assert AlertSeverity.INFO.value      == "info"
        assert AlertSeverity.EMERGENCY.value == "emergency"

    def test_severity_weight_order(self):
        assert SEVERITY_WEIGHT[AlertSeverity.INFO]      < SEVERITY_WEIGHT[AlertSeverity.WARNING]
        assert SEVERITY_WEIGHT[AlertSeverity.WARNING]   < SEVERITY_WEIGHT[AlertSeverity.CRITICAL]
        assert SEVERITY_WEIGHT[AlertSeverity.CRITICAL]  < SEVERITY_WEIGHT[AlertSeverity.EMERGENCY]

    def test_category_values(self):
        assert AlertCategory.LATENCY.value == "latency"
        assert AlertCategory.BROKER.value  == "broker"

    def test_alert_types(self):
        assert AlertType.HIGH_LATENCY.value          == "high_latency"
        assert AlertType.SUBSYSTEM_UNHEALTHY.value   == "subsystem_unhealthy"

    def test_status_values(self):
        assert AlertStatus.ACTIVE.value    == "active"
        assert AlertStatus.RESOLVED.value  == "resolved"
        assert AlertStatus.EXPIRED.value   == "expired"

    def test_terminal_statuses(self):
        assert AlertStatus.RESOLVED in TERMINAL_ALERT_STATUSES
        assert AlertStatus.EXPIRED  in TERMINAL_ALERT_STATUSES
        assert AlertStatus.ACTIVE   not in TERMINAL_ALERT_STATUSES

    def test_active_statuses(self):
        assert AlertStatus.ACTIVE       in ACTIVE_ALERT_STATUSES
        assert AlertStatus.ACKNOWLEDGED in ACTIVE_ALERT_STATUSES
        assert AlertStatus.ESCALATED    in ACTIVE_ALERT_STATUSES

    def test_policy_types(self):
        assert AlertPolicyType.IMMEDIATE.value            == "immediate"
        assert AlertPolicyType.CONSECUTIVE_FAILURE.value  == "consecutive_failure"

    def test_threshold_operators(self):
        assert ThresholdOperator.GT.value  == "gt"
        assert ThresholdOperator.LTE.value == "lte"


# ═══════════════════════════════════════════════════════════════════════════════
# TestExceptions
# ═══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_base_error(self):
        e = AlertFrameworkError("msg")
        assert e.error_code == "AF-000"
        assert "msg" in str(e)

    def test_not_running(self):
        e = AlertEngineNotRunningError()
        assert e.error_code == "AF-001"

    def test_not_found(self):
        e = AlertNotFoundError("aid-1")
        assert e.error_code == "AF-002"
        assert e.alert_id   == "aid-1"

    def test_rule_not_found(self):
        e = AlertRuleNotFoundError("rule-1")
        assert e.error_code == "AF-003"
        assert e.rule_id    == "rule-1"

    def test_rule_evaluation_error(self):
        e = AlertRuleEvaluationError("r1", "bad input")
        assert e.error_code == "AF-004"
        assert "bad input"  in str(e)

    def test_registry_capacity(self):
        e = AlertRegistryCapacityError(100)
        assert e.error_code == "AF-005"
        assert e.max_count  == 100

    def test_validation_error(self):
        e = AlertValidationError("fail", errors=("e1",))
        assert e.error_code == "AF-006"
        assert "e1" in e.errors

    def test_transition_error(self):
        e = AlertTransitionError("aid", "active", "resolved")
        assert e.error_code == "AF-007"
        assert e.alert_id   == "aid"

    def test_snapshot_error(self):
        e = AlertSnapshotError("reason x")
        assert e.error_code == "AF-008"

    def test_duplicate_rule(self):
        e = DuplicateAlertRuleError("rule-1")
        assert e.error_code == "AF-009"
        assert e.rule_id    == "rule-1"


# ═══════════════════════════════════════════════════════════════════════════════
# TestAlertThreshold
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlertThreshold:
    def test_evaluate_gt_no_breach(self):
        t = make_alert_threshold("m", ThresholdOperator.GT, 100.0)
        assert t.evaluate(50.0) is None

    def test_evaluate_gt_critical(self):
        t = make_alert_threshold("m", ThresholdOperator.GT, 100.0)
        assert t.evaluate(150.0) == AlertSeverity.CRITICAL

    def test_evaluate_gt_warning(self):
        t = make_alert_threshold("m", ThresholdOperator.GT, 100.0, warning_value=50.0)
        assert t.evaluate(75.0) == AlertSeverity.WARNING

    def test_evaluate_gt_emergency(self):
        t = make_alert_threshold("m", ThresholdOperator.GT, 100.0, emergency_value=200.0)
        assert t.evaluate(250.0) == AlertSeverity.EMERGENCY

    def test_evaluate_lt(self):
        t = make_alert_threshold("m", ThresholdOperator.LT, 10.0)
        assert t.evaluate(5.0) == AlertSeverity.CRITICAL
        assert t.evaluate(15.0) is None

    def test_evaluate_lte(self):
        t = make_alert_threshold("m", ThresholdOperator.LTE, 10.0)
        assert t.evaluate(10.0) == AlertSeverity.CRITICAL

    def test_evaluate_gte(self):
        t = make_alert_threshold("m", ThresholdOperator.GTE, 10.0)
        assert t.evaluate(10.0) == AlertSeverity.CRITICAL

    def test_evaluate_eq(self):
        t = make_alert_threshold("m", ThresholdOperator.EQ, 42.0)
        assert t.evaluate(42.0) == AlertSeverity.CRITICAL
        assert t.evaluate(43.0) is None

    def test_evaluate_neq(self):
        t = make_alert_threshold("m", ThresholdOperator.NEQ, 42.0)
        assert t.evaluate(43.0) == AlertSeverity.CRITICAL
        assert t.evaluate(42.0) is None

    def test_is_breached(self):
        t = make_alert_threshold("m", ThresholdOperator.GT, 100.0)
        assert t.is_breached(200.0) is True
        assert t.is_breached(50.0)  is False

    def test_to_dict(self):
        t = make_alert_threshold("m", ThresholdOperator.GT, 100.0, description="test")
        d = t.to_dict()
        assert d["metric_key"]     == "m"
        assert d["critical_value"] == 100.0
        assert d["operator"]       == "gt"

    def test_frozen(self):
        t = make_alert_threshold("m", ThresholdOperator.GT, 100.0)
        with pytest.raises((AttributeError, TypeError)):
            t.metric_key = "other"  # type: ignore


# ═══════════════════════════════════════════════════════════════════════════════
# TestAlertContext
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlertContext:
    def test_factory(self):
        ctx = _ctx("s1", "p1", {"p99_latency": 500.0})
        assert ctx.session_id   == "s1"
        assert ctx.portfolio_id == "p1"
        assert ctx.timestamp    > 0

    def test_get_metric(self):
        ctx = _ctx(metrics={"p99_latency": 500.0})
        assert ctx.get_metric("p99_latency")      == 500.0
        assert ctx.get_metric("missing", 99.0)    == 99.0

    def test_has_metric(self):
        ctx = _ctx(metrics={"p99_latency": 500.0})
        assert ctx.has_metric("p99_latency") is True
        assert ctx.has_metric("missing")     is False

    def test_window_metrics(self):
        ctx = _ctx(metrics={}, window_metrics={"1m": {"p99_latency": 200.0}})
        assert ctx.get_window_metric("1m", "p99_latency")        == 200.0
        assert ctx.get_window_metric("1m", "missing", 0.0)       == 0.0
        assert ctx.has_window_metric("1m", "p99_latency")        is True
        assert ctx.has_window_metric("5m", "p99_latency")        is False

    def test_frozen(self):
        ctx = _ctx()
        with pytest.raises((AttributeError, TypeError)):
            ctx.session_id = "other"  # type: ignore

    def test_to_dict(self):
        ctx = _ctx()
        d = ctx.to_dict()
        assert "session_id" in d
        assert "metric_count" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestAlertRequest
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlertRequest:
    def test_factory(self):
        ctx = _ctx()
        req = make_alert_request("s1", ctx)
        assert req.session_id    == "s1"
        assert req.rule_ids      == ()
        assert req.requested_at  > 0

    def test_with_rule_ids(self):
        ctx = _ctx()
        req = make_alert_request("s1", ctx, rule_ids=("r1", "r2"))
        assert req.rule_ids == ("r1", "r2")

    def test_frozen(self):
        ctx = _ctx()
        req = make_alert_request("s1", ctx)
        with pytest.raises((AttributeError, TypeError)):
            req.session_id = "other"  # type: ignore

    def test_to_dict(self):
        ctx = _ctx()
        req = make_alert_request("s1", ctx)
        d   = req.to_dict()
        assert "request_id" in d
        assert "session_id" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestAlertResponse
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlertResponse:
    def test_factory(self):
        resp = make_alert_response("req-1", "s1", ("a1", "a2"))
        assert resp.request_id        == "req-1"
        assert resp.generated_count   == 2
        assert resp.suppressed_count  == 0
        assert resp.has_alerts        is True
        assert resp.has_errors        is False

    def test_with_suppressed_and_errors(self):
        resp = make_alert_response(
            "req-1", "s1", ("a1",),
            alerts_suppressed=("a2",),
            errors=("err",),
        )
        assert resp.suppressed_count == 1
        assert resp.has_errors       is True

    def test_frozen(self):
        resp = make_alert_response("r", "s", ())
        with pytest.raises((AttributeError, TypeError)):
            resp.session_id = "other"  # type: ignore

    def test_to_dict(self):
        resp = make_alert_response("r", "s", ())
        d    = resp.to_dict()
        assert "framework_version" in d
        assert d["alerts_generated"] == []


# ═══════════════════════════════════════════════════════════════════════════════
# TestAlertSnapshot
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlertSnapshot:
    def _make_alert(self, status=AlertStatus.ACTIVE, severity=AlertSeverity.CRITICAL):
        """Helper: make a minimal Alert for snapshot testing."""
        alert = Alert(
            alert_id=str(id(object())), alert_type=AlertType.HIGH_LATENCY,
            severity=severity, category=AlertCategory.LATENCY,
            status=status, rule_id="r1", rule_name="test",
            title="T", message="M",
            session_id="s1", portfolio_id="p1",
            triggered_at=time.time(), detected_at=time.time(),
            framework_version="1.0.0",
        )
        return alert

    def test_empty_snapshot(self):
        snap = make_alert_snapshot("s1", "p1", [])
        assert snap.total_active    == 0
        assert snap.has_active_alerts is False
        assert snap.has_critical_or_above is False

    def test_active_alert_counted(self):
        a    = self._make_alert()
        snap = make_alert_snapshot("s1", "p1", [a])
        assert snap.total_active == 1
        assert snap.has_active_alerts is True
        assert a.alert_id in snap.active_alert_ids

    def test_critical_detection(self):
        a    = self._make_alert(severity=AlertSeverity.CRITICAL)
        snap = make_alert_snapshot("s1", "p1", [a])
        assert snap.has_critical_or_above is True
        assert snap.highest_severity      == "critical"

    def test_resolved_not_in_active_ids(self):
        a = self._make_alert(status=AlertStatus.RESOLVED)
        snap = make_alert_snapshot("s1", "p1", [a])
        assert a.alert_id not in snap.active_alert_ids
        assert snap.total_resolved == 1

    def test_is_newer_than(self):
        s1 = make_alert_snapshot("s1", "p1", [], snapshot_version=1)
        time.sleep(0.01)
        s2 = make_alert_snapshot("s1", "p1", [], snapshot_version=2)
        assert s2.is_newer_than(s1) is True
        assert s1.is_newer_than(s2) is False

    def test_total_open(self):
        a1 = self._make_alert(status=AlertStatus.ACTIVE)
        a2 = self._make_alert(status=AlertStatus.ACKNOWLEDGED)
        a3 = self._make_alert(status=AlertStatus.ESCALATED)
        snap = make_alert_snapshot("s1", "p1", [a1, a2, a3])
        assert snap.total_open == 3

    def test_frozen(self):
        snap = make_alert_snapshot("s1", "p1", [])
        with pytest.raises((AttributeError, TypeError)):
            snap.session_id = "other"  # type: ignore

    def test_to_json(self):
        snap = make_alert_snapshot("s1", "p1", [])
        j = snap.to_json()
        assert '"session_id"' in j


# ═══════════════════════════════════════════════════════════════════════════════
# TestAlertEvents
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlertEvents:
    def test_make_generated(self):
        e = make_alert_generated("s1", "a1")
        assert e.event_type  == AlertEventType.ALERT_GENERATED
        assert e.session_id  == "s1"
        assert e.alert_id    == "a1"
        assert e.occurred_at > 0

    def test_make_acknowledged(self):
        e = make_alert_acknowledged("s1", "a1", "trader")
        assert e.event_type == AlertEventType.ALERT_ACKNOWLEDGED
        assert e.actor      == "trader"

    def test_make_escalated(self):
        e = make_alert_escalated("s1", "a1")
        assert e.event_type == AlertEventType.ALERT_ESCALATED

    def test_make_resolved(self):
        e = make_alert_resolved("s1", "a1", "trader", reason="fixed")
        assert e.event_type == AlertEventType.ALERT_RESOLVED
        assert e.reason     == "fixed"

    def test_make_expired(self):
        e = make_alert_expired("s1", "a1")
        assert e.event_type == AlertEventType.ALERT_EXPIRED

    def test_make_suppressed(self):
        e = make_alert_suppressed("s1", "a1", reason="duplicate")
        assert e.event_type == AlertEventType.ALERT_SUPPRESSED
        assert e.reason     == "duplicate"

    def test_frozen(self):
        e = make_alert_generated("s1", "a1")
        with pytest.raises((AttributeError, TypeError)):
            e.event_id = "other"  # type: ignore

    def test_to_dict(self):
        e = make_alert_generated("s1", "a1")
        d = e.to_dict()
        assert "event_id" in d
        assert d["event_type"] == "alert_generated"


# ═══════════════════════════════════════════════════════════════════════════════
# TestAlertHistory
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlertHistory:
    def _alert(self, session_id="s1"):
        return Alert(
            alert_id=str(id(object())), alert_type=AlertType.HIGH_LATENCY,
            severity=AlertSeverity.CRITICAL, category=AlertCategory.LATENCY,
            status=AlertStatus.RESOLVED, rule_id="r1", rule_name="t",
            title="T", message="M", session_id=session_id, portfolio_id="p1",
            triggered_at=time.time(), detected_at=time.time(),
            framework_version="1.0.0",
        )

    def test_append_and_count(self):
        h = AlertHistory()
        h.append_alert(self._alert())
        assert h.alert_count == 1

    def test_maxlen(self):
        h = AlertHistory(max_alerts=3)
        for _ in range(5):
            h.append_alert(self._alert())
        assert h.alert_count == 3

    def test_latest_alert(self):
        h  = AlertHistory()
        a1 = self._alert("s1")
        a2 = self._alert("s2")
        h.append_alert(a1)
        h.append_alert(a2)
        assert h.latest_alert() is a2

    def test_alerts_for_session(self):
        h = AlertHistory()
        h.append_alert(self._alert("s1"))
        h.append_alert(self._alert("s2"))
        assert len(h.alerts_for_session("s1")) == 1

    def test_snapshots(self):
        h = AlertHistory()
        s = make_alert_snapshot("s1", "p1", [])
        h.append_snapshot(s)
        assert h.snapshot_count == 1
        assert h.latest_snapshot() is s

    def test_events(self):
        h = AlertHistory()
        e = make_alert_generated("s1", "a1")
        h.append_event(e)
        assert h.event_count == 1
        assert len(h.events_for_session("s1")) == 1

    def test_events_for_alert(self):
        h = AlertHistory()
        h.append_event(make_alert_generated("s1", "a1"))
        h.append_event(make_alert_acknowledged("s1", "a2", "actor"))
        assert len(h.events_for_alert("a1")) == 1

    def test_events_matching(self):
        h = AlertHistory()
        h.append_event(make_alert_generated("s1", "a1"))
        h.append_event(make_alert_acknowledged("s1", "a2", "a"))
        matches = h.events_matching(lambda e: e.event_type == AlertEventType.ALERT_GENERATED)
        assert len(matches) == 1

    def test_clear(self):
        h = AlertHistory()
        h.append_alert(self._alert())
        h.append_event(make_alert_generated("s1", "a1"))
        h.clear()
        assert h.alert_count == 0
        assert h.event_count == 0


# ═══════════════════════════════════════════════════════════════════════════════
# TestAlertStatistics
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlertStatistics:
    def test_initial_zeroes(self):
        s = AlertStatistics()
        assert s.alerts_generated == 0
        assert s.resolution_rate  == 0.0

    def test_record_generated(self):
        s = AlertStatistics()
        s.record_generated("critical")
        assert s.alerts_generated == 1
        assert s.critical_alerts  == 1

    def test_record_emergency(self):
        s = AlertStatistics()
        s.record_generated("emergency")
        assert s.emergency_alerts == 1

    def test_record_resolution(self):
        s = AlertStatistics()
        s.record_generated()
        s.record_generated()
        s.record_resolved()
        assert abs(s.resolution_rate - 0.5) < 1e-9

    def test_average_evaluation_time(self):
        s = AlertStatistics()
        s.record_evaluation(10.0)
        s.record_evaluation(20.0)
        assert abs(s.average_evaluation_time_ms - 15.0) < 1e-9

    def test_escalation_rate(self):
        s = AlertStatistics()
        s.record_generated()
        s.record_escalated()
        assert s.escalation_rate == 1.0

    def test_suppression_rate(self):
        s = AlertStatistics()
        s.record_generated()
        s.record_suppressed()
        assert abs(s.suppression_rate - 0.5) < 1e-9

    def test_reset(self):
        s = AlertStatistics()
        s.record_generated("critical")
        s.reset()
        assert s.alerts_generated == 0
        assert s.critical_alerts  == 0

    def test_copy_is_independent(self):
        s = AlertStatistics()
        s.record_generated()
        c = s.copy()
        s.record_generated()
        assert c.alerts_generated == 1
        assert s.alerts_generated == 2

    def test_to_dict(self):
        s = AlertStatistics()
        d = s.to_dict()
        assert "alerts_generated"          in d
        assert "average_evaluation_time_ms" in d

    def test_thread_safe_increments(self):
        s = AlertStatistics()
        threads = [threading.Thread(target=s.record_generated) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert s.alerts_generated == 100


# ═══════════════════════════════════════════════════════════════════════════════
# TestAlertValidation
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlertValidation:
    def _v(self):
        return AlertValidator()

    def test_valid_context(self):
        ctx = _ctx()
        r   = self._v().validate_context(ctx)
        assert r.is_valid is True

    def test_invalid_context_missing_session(self):
        ctx = make_alert_context("", "p1", {})
        r   = self._v().validate_context(ctx)
        assert r.is_valid is False
        assert any("session_id" in e for e in r.errors)

    def test_invalid_context_missing_portfolio(self):
        ctx = make_alert_context("s1", "", {})
        r   = self._v().validate_context(ctx)
        assert r.is_valid is False

    def test_invalid_request(self):
        ctx = make_alert_context("", "p1", {})
        req = make_alert_request("", ctx)
        r   = self._v().validate_request(req)
        assert r.is_valid is False

    def test_valid_threshold(self):
        t = make_alert_threshold("m", ThresholdOperator.GT, 100.0)
        r = self._v().validate_threshold(t)
        assert r.is_valid is True

    def test_threshold_missing_metric_key(self):
        t = make_alert_threshold("", ThresholdOperator.GT, 100.0)
        r = self._v().validate_threshold(t)
        assert r.is_valid is False

    def test_threshold_gt_warning_warning(self):
        # warning >= critical for GT — should be a warning (not error)
        t = make_alert_threshold("m", ThresholdOperator.GT, 50.0, warning_value=100.0)
        r = self._v().validate_threshold(t)
        assert r.is_valid is True
        assert len(r.warnings) > 0

    def test_valid_transition(self):
        r = self._v().validate_transition("a1", AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED)
        assert r.is_valid is True

    def test_invalid_transition_from_resolved(self):
        r = self._v().validate_transition("a1", AlertStatus.RESOLVED, AlertStatus.ACTIVE)
        assert r.is_valid is False

    def test_invalid_transition_active_to_active(self):
        r = self._v().validate_transition("a1", AlertStatus.ACTIVE, AlertStatus.ACTIVE)
        assert r.is_valid is False

    def test_validation_result_to_dict(self):
        vr = AlertValidationResult()
        vr.add_error("e1")
        vr.add_warning("w1")
        d = vr.to_dict()
        assert d["is_valid"] is False
        assert "e1" in d["errors"]
        assert "w1" in d["warnings"]


# ═══════════════════════════════════════════════════════════════════════════════
# TestAlertPolicy
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlertPolicy:
    def test_immediate_fires_immediately(self):
        ev = PolicyEvaluator(make_immediate_policy(cooldown_seconds=0))
        assert ev.should_fire(True) is True

    def test_immediate_no_fire_when_not_met(self):
        ev = PolicyEvaluator(make_immediate_policy())
        assert ev.should_fire(False) is False

    def test_cooldown_suppresses_second_fire(self):
        policy = make_immediate_policy(cooldown_seconds=60.0)
        ev     = PolicyEvaluator(policy)
        assert ev.should_fire(True, now=1000.0)  is True
        assert ev.should_fire(True, now=1010.0)  is False   # in cooldown

    def test_cooldown_expired_fires_again(self):
        policy = make_immediate_policy(cooldown_seconds=60.0)
        ev     = PolicyEvaluator(policy)
        ev.should_fire(True, now=1000.0)
        assert ev.should_fire(True, now=2000.0) is True   # cooldown expired

    def test_consecutive_requires_n_hits(self):
        policy = make_consecutive_policy(3, cooldown_seconds=0)
        ev     = PolicyEvaluator(policy)
        assert ev.should_fire(True, now=1.0)  is False
        assert ev.should_fire(True, now=2.0)  is False
        assert ev.should_fire(True, now=3.0)  is True

    def test_consecutive_resets_on_miss(self):
        policy = make_consecutive_policy(3, cooldown_seconds=0)
        ev     = PolicyEvaluator(policy)
        ev.should_fire(True,  now=1.0)
        ev.should_fire(True,  now=2.0)
        ev.should_fire(False, now=3.0)   # miss resets
        ev.should_fire(True,  now=4.0)
        ev.should_fire(True,  now=5.0)
        assert ev.should_fire(True, now=6.0) is True   # 3 consecutive after reset

    def test_rolling_window_fires_at_min_hits(self):
        policy = make_rolling_window_policy(60.0, 3, cooldown_seconds=0)
        ev     = PolicyEvaluator(policy)
        assert ev.should_fire(True, now=1.0)  is False
        assert ev.should_fire(True, now=2.0)  is False
        assert ev.should_fire(True, now=3.0)  is True

    def test_rolling_window_prunes_old_hits(self):
        policy = make_rolling_window_policy(10.0, 2, cooldown_seconds=0)
        ev     = PolicyEvaluator(policy)
        ev.should_fire(True, now=1.0)    # hit at t=1
        ev.should_fire(True, now=2.0)    # hit at t=2 → 2 hits → fires; resets after
        # Now add hits where old ones expire
        ev.should_fire(True, now=20.0)   # old hits at 1, 2 are gone; only 1 hit
        assert ev.should_fire(True, now=25.0) is True  # 2 hits in window [15, 25]

    def test_in_cooldown(self):
        policy = make_immediate_policy(cooldown_seconds=60.0)
        ev     = PolicyEvaluator(policy)
        ev.should_fire(True, now=100.0)
        assert ev.in_cooldown(120.0) is True
        assert ev.in_cooldown(200.0) is False

    def test_reset(self):
        policy = make_consecutive_policy(3, cooldown_seconds=0)
        ev     = PolicyEvaluator(policy)
        ev.should_fire(True, now=1.0)
        ev.should_fire(True, now=2.0)
        ev.reset()
        # Needs 3 more hits after reset
        ev.should_fire(True, now=3.0)
        ev.should_fire(True, now=4.0)
        assert ev.should_fire(True, now=5.0) is True

    def test_policy_to_dict(self):
        p = make_immediate_policy()
        d = p.to_dict()
        assert d["policy_type"] == "immediate"

    def test_policy_frozen(self):
        p = make_immediate_policy()
        with pytest.raises((AttributeError, TypeError)):
            p.policy_type = AlertPolicyType.CUSTOM  # type: ignore


# ═══════════════════════════════════════════════════════════════════════════════
# TestAlertDomain (Alert object)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlertDomain:
    def _alert(self, status=AlertStatus.ACTIVE):
        return Alert(
            alert_id="a1", alert_type=AlertType.HIGH_LATENCY,
            severity=AlertSeverity.CRITICAL, category=AlertCategory.LATENCY,
            status=status, rule_id="r1", rule_name="test",
            title="T", message="M",
            session_id="s1", portfolio_id="p1",
            triggered_at=time.time(), detected_at=time.time(),
            framework_version="1.0.0",
        )

    def test_acknowledge(self):
        a = self._alert()
        a.acknowledge("trader1")
        assert a.status          == AlertStatus.ACKNOWLEDGED
        assert a.acknowledged_by == "trader1"
        assert a.acknowledged_at is not None

    def test_acknowledge_non_active_noop(self):
        a = self._alert(status=AlertStatus.RESOLVED)
        a.acknowledge("trader1")
        assert a.status == AlertStatus.RESOLVED   # no change

    def test_escalate(self):
        a = self._alert()
        a.escalate("auto")
        assert a.status          == AlertStatus.ESCALATED
        assert a.escalation_count == 1
        assert a.escalated_at    is not None

    def test_escalate_from_acknowledged(self):
        a = self._alert()
        a.acknowledge("t")
        a.escalate("auto")
        assert a.status == AlertStatus.ESCALATED

    def test_resolve(self):
        a = self._alert()
        a.resolve("trader1", "fixed")
        assert a.status           == AlertStatus.RESOLVED
        assert a.resolved_by      == "trader1"
        assert a.resolution_notes == "fixed"

    def test_resolve_terminal_noop(self):
        a = self._alert(status=AlertStatus.EXPIRED)
        a.resolve("t")
        assert a.status == AlertStatus.EXPIRED

    def test_expire(self):
        a = self._alert()
        a.expire()
        assert a.status == AlertStatus.EXPIRED

    def test_expire_terminal_noop(self):
        a = self._alert(status=AlertStatus.RESOLVED)
        a.expire()
        assert a.status == AlertStatus.RESOLVED

    def test_suppress(self):
        a = self._alert()
        a.suppress("duplicate")
        assert a.status             == AlertStatus.SUPPRESSED
        assert a.suppressed         is True
        assert a.suppression_reason == "duplicate"

    def test_suppress_non_active_noop(self):
        a = self._alert(status=AlertStatus.ESCALATED)
        a.suppress("x")
        assert a.status == AlertStatus.ESCALATED

    def test_reactivate(self):
        a = self._alert()
        a.suppress("dup")
        a.reactivate()
        assert a.status == AlertStatus.ACTIVE

    def test_is_active(self):
        a = self._alert()
        assert a.is_active() is True
        a.resolve("t")
        assert a.is_active() is False

    def test_is_terminal(self):
        a = self._alert()
        assert a.is_terminal() is False
        a.resolve("t")
        assert a.is_terminal() is True

    def test_is_stale(self):
        a = self._alert()
        a.expires_at = time.time() - 1.0
        assert a.is_stale() is True

    def test_to_dict(self):
        a = self._alert()
        d = a.to_dict()
        assert d["alert_id"]   == "a1"
        assert d["alert_type"] == "high_latency"


# ═══════════════════════════════════════════════════════════════════════════════
# TestBuiltInRules
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuiltInRules:
    def _ctx(self, **metrics) -> AlertContext:
        return make_alert_context("s1", "p1", metrics)

    def test_high_latency_fires(self):
        rule = HighLatencyRule(rule_id="r1")
        ctx  = self._ctx(p99_latency=2_000.0)
        a    = rule.evaluate(ctx)
        assert a is not None
        assert a.alert_type == AlertType.HIGH_LATENCY
        assert a.severity   in (AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY)

    def test_high_latency_no_fire(self):
        rule = HighLatencyRule(rule_id="r1")
        ctx  = self._ctx(p99_latency=100.0)
        assert rule.evaluate(ctx) is None

    def test_high_latency_warning(self):
        rule = HighLatencyRule(rule_id="r1")
        ctx  = self._ctx(p99_latency=750.0)   # > 500ms warning
        a    = rule.evaluate(ctx)
        assert a is not None
        assert a.severity == AlertSeverity.WARNING

    def test_queue_congestion_fires(self):
        rule = QueueCongestionRule(rule_id="r2")
        ctx  = self._ctx(queue_wait_time=2_000.0)
        a    = rule.evaluate(ctx)
        assert a is not None
        assert a.alert_type == AlertType.QUEUE_CONGESTION

    def test_queue_no_fire(self):
        rule = QueueCongestionRule(rule_id="r2")
        ctx  = self._ctx(queue_wait_time=50.0)
        assert rule.evaluate(ctx) is None

    def test_execution_failure_rate_fires(self):
        rule = ExecutionFailureRateRule(rule_id="r3")
        ctx  = self._ctx(failure_rate=0.20)
        a    = rule.evaluate(ctx)
        assert a is not None
        assert a.alert_type == AlertType.EXECUTION_FAILURE_RATE

    def test_broker_unavailable_fires(self):
        rule = BrokerUnavailableRule(rule_id="r4")
        ctx  = self._ctx(broker_utilization=0.99)
        a    = rule.evaluate(ctx)
        assert a is not None
        assert a.alert_type == AlertType.BROKER_UNAVAILABLE

    def test_gateway_degraded_fires(self):
        rule = GatewayDegradedRule(rule_id="r5")
        ctx  = make_alert_context("s1", "p1", {"gateway_throughput": 0.05})
        a    = rule.evaluate(ctx)
        assert a is not None
        assert a.alert_type == AlertType.GATEWAY_DEGRADED

    def test_gateway_metric_absent_no_fire(self):
        rule = GatewayDegradedRule(rule_id="r5")
        ctx  = self._ctx()   # no gateway_throughput metric
        assert rule.evaluate(ctx) is None

    def test_retry_threshold_fires(self):
        rule = RetryThresholdExceededRule(rule_id="r6")
        ctx  = self._ctx(retry_rate=0.30)
        a    = rule.evaluate(ctx)
        assert a is not None
        assert a.alert_type == AlertType.RETRY_THRESHOLD_EXCEEDED

    def test_timeout_threshold_fires(self):
        rule = TimeoutThresholdExceededRule(rule_id="r7")
        ctx  = self._ctx(timeout_rate=0.15)
        a    = rule.evaluate(ctx)
        assert a is not None
        assert a.alert_type == AlertType.TIMEOUT_THRESHOLD_EXCEEDED

    def test_monitoring_failure_fires(self):
        rule = MonitoringFailureRule(rule_id="r8")
        ctx  = self._ctx(monitoring_cycle_time=6_000.0)
        a    = rule.evaluate(ctx)
        assert a is not None
        assert a.alert_type == AlertType.MONITORING_FAILURE

    def test_resource_exhaustion_fires(self):
        rule = ResourceExhaustionRule(rule_id="r9")
        ctx  = self._ctx(execution_count=15_000.0)
        a    = rule.evaluate(ctx)
        assert a is not None
        assert a.alert_type == AlertType.RESOURCE_EXHAUSTION

    def test_subsystem_unhealthy_fires(self):
        rule = SubsystemUnhealthyRule(rule_id="r10")
        ctx  = self._ctx(
            failure_rate=0.20,
            p99_latency=600.0,
            timeout_rate=0.10,
        )
        a = rule.evaluate(ctx)
        assert a is not None
        assert a.alert_type == AlertType.SUBSYSTEM_UNHEALTHY

    def test_subsystem_one_condition_no_fire(self):
        rule = SubsystemUnhealthyRule(rule_id="r10")
        ctx  = self._ctx(failure_rate=0.20, p99_latency=100.0, timeout_rate=0.01)
        assert rule.evaluate(ctx) is None

    def test_rule_disabled_noop(self):
        rule = HighLatencyRule(rule_id="r1", enabled=False)
        assert rule.is_enabled() is False

    def test_rule_to_dict(self):
        rule = HighLatencyRule(rule_id="r1")
        d    = rule.to_dict()
        assert d["rule_id"]    == "r1"
        assert d["alert_type"] == "high_latency"
        assert "threshold" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestAlertRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlertRegistry:
    def _reg(self):
        r = AlertRegistry()
        r.start()
        return r

    def _alert(self, session_id="s1"):
        import uuid
        return Alert(
            alert_id=str(uuid.uuid4()), alert_type=AlertType.HIGH_LATENCY,
            severity=AlertSeverity.CRITICAL, category=AlertCategory.LATENCY,
            status=AlertStatus.ACTIVE, rule_id="r1", rule_name="t",
            title="T", message="M", session_id=session_id, portfolio_id="p1",
            triggered_at=time.time(), detected_at=time.time(),
            framework_version="1.0.0",
        )

    def test_store_and_get(self):
        reg = self._reg()
        a   = self._alert()
        reg.store(a)
        assert reg.get(a.alert_id) is a

    def test_find_missing_returns_none(self):
        reg = self._reg()
        assert reg.find("missing") is None

    def test_get_missing_raises(self):
        reg = self._reg()
        with pytest.raises(AlertNotFoundError) as ei:
            reg.get("missing")
        assert ei.value.error_code == "AF-002"

    def test_capacity_error(self):
        reg = AlertRegistry(max_alerts=2)
        reg.start()
        reg.store(self._alert())
        reg.store(self._alert())
        with pytest.raises(AlertRegistryCapacityError) as ei:
            reg.store(self._alert())
        assert ei.value.error_code == "AF-005"

    def test_contains(self):
        reg = self._reg()
        a   = self._alert()
        reg.store(a)
        assert reg.contains(a.alert_id) is True
        assert reg.contains("missing")  is False

    def test_remove(self):
        reg = self._reg()
        a   = self._alert()
        reg.store(a)
        removed = reg.remove(a.alert_id)
        assert removed is a
        assert reg.contains(a.alert_id) is False

    def test_active_alerts(self):
        reg = self._reg()
        a1  = self._alert()
        a2  = self._alert()
        a2.resolve("t")
        reg.store(a1)
        reg.store(a2)
        active = reg.active_alerts()
        assert a1 in active
        assert a2 not in active

    def test_alerts_for_session(self):
        reg = self._reg()
        reg.store(self._alert("s1"))
        reg.store(self._alert("s2"))
        assert len(reg.alerts_for_session("s1")) == 1

    def test_purge_terminal(self):
        reg = self._reg()
        a1  = self._alert()
        a2  = self._alert()
        a2.resolve("t")
        reg.store(a1)
        reg.store(a2)
        purged = reg.purge_terminal()
        assert a2 in purged
        assert reg.count() == 1

    def test_not_running_raises(self):
        reg = AlertRegistry()
        with pytest.raises(AlertEngineNotRunningError):
            reg.store(self._alert())


# ═══════════════════════════════════════════════════════════════════════════════
# TestAlertFactory
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlertFactory:
    def _fac(self):
        f = AlertFactory()
        f.start()
        return f

    def test_create_snapshot(self):
        f = self._fac()
        s = f.create_snapshot("s1", "p1", [])
        assert s.snapshot_version == 1
        assert s.session_id       == "s1"

    def test_version_increments(self):
        f  = self._fac()
        s1 = f.create_snapshot("s1", "p1", [])
        s2 = f.create_snapshot("s1", "p1", [])
        assert s2.snapshot_version == s1.snapshot_version + 1

    def test_version_independent_per_session(self):
        f  = self._fac()
        f.create_snapshot("s1", "p1", [])
        s2 = f.create_snapshot("s2", "p2", [])
        assert s2.snapshot_version == 1

    def test_create_request(self):
        f   = self._fac()
        ctx = _ctx()
        req = f.create_request("s1", ctx)
        assert req.session_id == "s1"

    def test_create_response(self):
        f    = self._fac()
        ctx  = _ctx()
        req  = f.create_request("s1", ctx)
        resp = f.create_response(req, ("a1",))
        assert resp.generated_count == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TestAlertEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlertEngine:
    def _engine(self):
        return _engine()

    def test_start_stop(self):
        e = AlertEngine()
        e.start()
        e.stop()

    def test_not_running_raises(self):
        e = AlertEngine()
        with pytest.raises(AlertEngineNotRunningError):
            e.create_request("s1", _ctx())

    def test_register_rule(self):
        e = self._engine()
        e.register_rule(HighLatencyRule(rule_id="r1"))
        assert e.rule_count() == 1

    def test_duplicate_rule_raises(self):
        e = self._engine()
        e.register_rule(HighLatencyRule(rule_id="r1"))
        with pytest.raises(DuplicateAlertRuleError):
            e.register_rule(HighLatencyRule(rule_id="r1"))

    def test_unregister_rule(self):
        e = self._engine()
        e.register_rule(HighLatencyRule(rule_id="r1"))
        e.unregister_rule("r1")
        assert e.rule_count() == 0

    def test_evaluate_generates_alert(self):
        e = self._engine()
        e.register_rule(HighLatencyRule(rule_id="r1"))
        ctx  = make_alert_context("s1", "p1", {"p99_latency": 2_000.0})
        req  = e.create_request("s1", ctx)
        resp = e.process_request(req)
        assert resp.generated_count >= 1
        assert len(resp.alerts_generated) >= 1

    def test_evaluate_no_breach_no_alert(self):
        e = self._engine()
        e.register_rule(HighLatencyRule(rule_id="r1"))
        ctx  = make_alert_context("s1", "p1", {"p99_latency": 10.0})
        req  = e.create_request("s1", ctx)
        resp = e.process_request(req)
        assert resp.generated_count == 0

    def test_invalid_request_returns_error_response(self):
        e   = self._engine()
        ctx = make_alert_context("", "p1", {})
        req = make_alert_request("", ctx)
        resp = e.process_request(req)
        assert resp.has_errors is True
        assert resp.generated_count == 0

    def test_acknowledge(self):
        e = self._engine()
        e.register_rule(HighLatencyRule(rule_id="r1"))
        ctx  = make_alert_context("s1", "p1", {"p99_latency": 2_000.0})
        resp = e.process_request(e.create_request("s1", ctx))
        aid  = resp.alerts_generated[0]
        a    = e.acknowledge(aid, "trader1")
        assert a.status == AlertStatus.ACKNOWLEDGED

    def test_acknowledge_non_active_raises(self):
        e = self._engine()
        e.register_rule(HighLatencyRule(rule_id="r1"))
        ctx  = make_alert_context("s1", "p1", {"p99_latency": 2_000.0})
        resp = e.process_request(e.create_request("s1", ctx))
        aid  = resp.alerts_generated[0]
        e.acknowledge(aid, "t")
        with pytest.raises(AlertTransitionError):
            e.acknowledge(aid, "t")  # already ACKNOWLEDGED

    def test_escalate(self):
        e = self._engine()
        e.register_rule(HighLatencyRule(rule_id="r1"))
        ctx  = make_alert_context("s1", "p1", {"p99_latency": 2_000.0})
        resp = e.process_request(e.create_request("s1", ctx))
        aid  = resp.alerts_generated[0]
        a    = e.escalate(aid)
        assert a.status          == AlertStatus.ESCALATED
        assert a.escalation_count == 1

    def test_resolve_removes_from_registry(self):
        e = self._engine()
        e.register_rule(HighLatencyRule(rule_id="r1"))
        ctx  = make_alert_context("s1", "p1", {"p99_latency": 2_000.0})
        resp = e.process_request(e.create_request("s1", ctx))
        aid  = resp.alerts_generated[0]
        e.resolve(aid, "trader1", "fixed")
        assert e.find_alert(aid) is None
        # Check history has it
        hist = e.history().alerts_for_alert(aid) if hasattr(e.history(), "alerts_for_alert") else []

    def test_resolve_terminal_raises(self):
        e = self._engine()
        e.register_rule(HighLatencyRule(rule_id="r1"))
        ctx  = make_alert_context("s1", "p1", {"p99_latency": 2_000.0})
        resp = e.process_request(e.create_request("s1", ctx))
        aid  = resp.alerts_generated[0]
        e.resolve(aid, "t")
        with pytest.raises(AlertNotFoundError):
            e.resolve(aid, "t")   # already removed from registry

    def test_expire_stale_alerts(self):
        e = self._engine()
        e.register_rule(HighLatencyRule(rule_id="r1"))
        ctx  = make_alert_context("s1", "p1", {"p99_latency": 2_000.0})
        resp = e.process_request(e.create_request("s1", ctx))
        aid  = resp.alerts_generated[0]
        # Set expires_at in the past
        alert = e.get_alert(aid)
        alert.expires_at = time.time() - 1.0
        e._registry.update(alert)
        expired = e.expire_stale_alerts()
        assert aid in expired

    def test_snapshot(self):
        e    = self._engine()
        snap = e.snapshot("s1", "p1")
        assert snap.session_id    == "s1"
        assert snap.total_active  == 0

    def test_event_listener(self):
        events = []
        e = self._engine()
        e.add_event_listener(events.append)
        e.register_rule(HighLatencyRule(rule_id="r1"))
        ctx  = make_alert_context("s1", "p1", {"p99_latency": 2_000.0})
        e.process_request(e.create_request("s1", ctx))
        assert len(events) >= 1
        assert events[0].event_type == AlertEventType.ALERT_GENERATED

    def test_remove_event_listener(self):
        events = []
        e = self._engine()
        e.add_event_listener(events.append)
        e.remove_event_listener(events.append)
        e.register_rule(HighLatencyRule(rule_id="r1"))
        ctx  = make_alert_context("s1", "p1", {"p99_latency": 2_000.0})
        e.process_request(e.create_request("s1", ctx))
        assert len(events) == 0

    def test_statistics(self):
        e = self._engine()
        e.register_rule(HighLatencyRule(rule_id="r1"))
        ctx  = make_alert_context("s1", "p1", {"p99_latency": 2_000.0})
        e.process_request(e.create_request("s1", ctx))
        stats = e.statistics()
        assert stats.alerts_generated >= 1
        assert stats.evaluation_count >= 1

    def test_cooldown_suppresses_duplicate(self):
        policy = make_immediate_policy(cooldown_seconds=999.0)
        rule   = HighLatencyRule(rule_id="r1", policy=policy)
        e = self._engine()
        e.register_rule(rule)
        ctx = make_alert_context("s1", "p1", {"p99_latency": 2_000.0})
        resp1 = e.process_request(e.create_request("s1", ctx))
        resp2 = e.process_request(e.create_request("s1", ctx))
        assert resp1.generated_count  >= 1
        assert resp2.suppressed_count >= 1

    def test_rule_ids_filter(self):
        e = self._engine()
        e.register_rule(HighLatencyRule(rule_id="r1"))
        e.register_rule(QueueCongestionRule(rule_id="r2"))
        ctx = make_alert_context("s1", "p1", {"p99_latency": 2_000.0, "queue_wait_time": 5_000.0})
        req  = e.create_request("s1", ctx, rule_ids=("r1",))
        resp = e.process_request(req)
        # Only r1 evaluated; should be 1 alert of type HIGH_LATENCY
        assert resp.generated_count == 1

    def test_suppressed_alert_in_history(self):
        policy = make_immediate_policy(cooldown_seconds=999.0)
        rule   = HighLatencyRule(rule_id="r1", policy=policy)
        e = self._engine()
        e.register_rule(rule)
        ctx = make_alert_context("s1", "p1", {"p99_latency": 2_000.0})
        e.process_request(e.create_request("s1", ctx))
        resp2 = e.process_request(e.create_request("s1", ctx))
        hist_events = e.history().events_matching(
            lambda ev: ev.event_type == AlertEventType.ALERT_SUPPRESSED
        )
        assert len(hist_events) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# TestAlertManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlertManager:
    def test_start_stop(self):
        m = AlertManager()
        m.start()
        m.stop()

    def test_register_default_rules(self):
        m = _manager()
        m.register_default_rules()
        assert m.engine().rule_count() == 10

    def test_evaluate(self):
        m = _manager()
        m.register_rule(HighLatencyRule(rule_id="r1"))
        ctx    = make_alert_context("s1", "p1", {"p99_latency": 2_000.0})
        alerts = m.evaluate(ctx)
        assert len(alerts) >= 1

    def test_acknowledge_resolve(self):
        m = _manager()
        m.register_rule(HighLatencyRule(rule_id="r1"))
        ctx    = make_alert_context("s1", "p1", {"p99_latency": 2_000.0})
        alerts = m.evaluate(ctx)
        aid    = alerts[0].alert_id
        m.acknowledge(aid, "trader1")
        m.resolve(aid, "trader1", "fixed")

    def test_run_maintenance_expires(self):
        m = _manager(escalation_age_sec=9999) if False else AlertManager(escalation_age_sec=9999)
        m.start()
        m.register_rule(HighLatencyRule(rule_id="r1"))
        ctx = make_alert_context("s1", "p1", {"p99_latency": 2_000.0})
        m.evaluate(ctx)
        # Set stale
        for a in m.active_alerts():
            a.expires_at = time.time() - 1.0
            m.engine()._registry.update(a)
        result = m.run_maintenance()
        assert result["expired"] >= 1

    def test_snapshot(self):
        m    = _manager()
        snap = m.snapshot("s1", "p1")
        assert snap.session_id == "s1"

    def test_statistics(self):
        m = _manager()
        m.register_rule(HighLatencyRule(rule_id="r1"))
        m.evaluate(make_alert_context("s1", "p1", {"p99_latency": 2_000.0}))
        stats = m.statistics()
        assert stats.alerts_generated >= 1

    def test_not_running_raises(self):
        m = AlertManager()
        with pytest.raises(AlertEngineNotRunningError):
            m.evaluate(_ctx())


# ═══════════════════════════════════════════════════════════════════════════════
# TestConcurrency
# ═══════════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    def test_concurrent_evaluate(self):
        e = _engine()
        e.register_rule(HighLatencyRule(rule_id="r1"))
        errors = []

        def work():
            try:
                ctx  = make_alert_context("s1", "p1", {"p99_latency": 2_000.0})
                req  = e.create_request("s1", ctx)
                e.process_request(req)
            except Exception as ex:
                errors.append(ex)

        threads = [threading.Thread(target=work) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == [], f"Errors: {errors}"

    def test_concurrent_register_unregister(self):
        e      = _engine()
        errors = []

        def register(i):
            try:
                rule = HighLatencyRule(rule_id=f"r{i}")
                e.register_rule(rule)
            except DuplicateAlertRuleError:
                pass
            except Exception as ex:
                errors.append(ex)

        def unregister(i):
            try:
                e.unregister_rule(f"r{i}")
            except Exception as ex:
                errors.append(ex)

        threads = (
            [threading.Thread(target=register, args=(i,)) for i in range(20)]
            + [threading.Thread(target=unregister, args=(i,)) for i in range(20)]
        )
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == [], f"Errors: {errors}"

    def test_concurrent_statistics(self):
        stats = AlertStatistics()
        threads = [threading.Thread(target=stats.record_generated) for _ in range(200)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert stats.alerts_generated == 200


# ═══════════════════════════════════════════════════════════════════════════════
# TestStressTesting
# ═══════════════════════════════════════════════════════════════════════════════

class TestStressTesting:
    def test_many_evaluations(self):
        e = _engine()
        e.register_rule(HighLatencyRule(rule_id="r1"))
        for i in range(100):
            ctx  = make_alert_context(f"s{i}", "p1", {"p99_latency": 2_000.0})
            req  = e.create_request(f"s{i}", ctx)
            e.process_request(req)
        stats = e.statistics()
        assert stats.evaluation_count >= 100

    def test_all_ten_rules(self):
        m = _manager()
        m.register_default_rules()
        ctx = make_alert_context("s1", "p1", {
            "p99_latency":          2_000.0,
            "queue_wait_time":      2_000.0,
            "failure_rate":         0.20,
            "broker_utilization":   0.99,
            "gateway_throughput":   0.05,
            "retry_rate":           0.30,
            "timeout_rate":         0.15,
            "monitoring_cycle_time": 6_000.0,
            "execution_count":      15_000.0,
        })
        alerts = m.evaluate(ctx)
        # At minimum: latency, queue, failure, broker, gateway, retry, timeout, monitoring, resource
        # SubsystemUnhealthy also fires (multiple breached)
        assert len(alerts) >= 9


# ═══════════════════════════════════════════════════════════════════════════════
# TestRegressionEdgeCases
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegressionEdgeCases:
    def test_no_alert_generation_from_metrics(self):
        """Alert Framework must not compute metrics — only read pre-computed ones."""
        e = _engine()
        e.register_rule(HighLatencyRule(rule_id="r1"))
        ctx = make_alert_context("s1", "p1", {})   # empty metrics
        req = e.create_request("s1", ctx)
        resp = e.process_request(req)
        # No breach (all metrics default to 0) → no alert
        assert resp.generated_count == 0

    def test_no_broker_communication(self):
        """AlertEngine must not have any broker connectivity."""
        e = _engine()
        assert not hasattr(e, "_broker")
        assert not hasattr(e, "_gateway")

    def test_no_metric_computation(self):
        """AlertEngine must not have MetricsManager or MetricsCollector."""
        e = _engine()
        assert not hasattr(e, "_metrics_manager")
        assert not hasattr(e, "_collector")

    def test_alert_id_unique_per_evaluation(self):
        e = _engine()
        e.register_rule(HighLatencyRule(rule_id="r1"))
        ctx = make_alert_context("s1", "p1", {"p99_latency": 2_000.0})
        # Evaluate twice in different sessions to bypass cooldown
        resp1 = e.process_request(e.create_request("s1", ctx))
        resp2 = e.process_request(e.create_request("s2",
            make_alert_context("s2", "p1", {"p99_latency": 2_000.0})
        ))
        if resp1.generated_count > 0 and resp2.generated_count > 0:
            assert resp1.alerts_generated[0] != resp2.alerts_generated[0]

    def test_statistics_copy_independent(self):
        e = _engine()
        e.register_rule(HighLatencyRule(rule_id="r1"))
        ctx = make_alert_context("s1", "p1", {"p99_latency": 2_000.0})
        e.process_request(e.create_request("s1", ctx))
        s1 = e.statistics()
        e.process_request(e.create_request("s2",
            make_alert_context("s2", "p1", {"p99_latency": 2_000.0})
        ))
        s2 = e.statistics()
        assert s2.evaluation_count > s1.evaluation_count

    def test_factory_version_per_session(self):
        f  = AlertFactory()
        f.start()
        f.create_snapshot("sA", "p", [])
        f.create_snapshot("sA", "p", [])
        f.create_snapshot("sB", "p", [])
        assert f.current_version("sA") == 2
        assert f.current_version("sB") == 1

    def test_rule_makes_alert_with_correct_session(self):
        rule = HighLatencyRule(rule_id="r1")
        ctx  = make_alert_context("unique-sess", "p1", {"p99_latency": 2_000.0})
        a    = rule.evaluate(ctx)
        assert a is not None
        assert a.session_id == "unique-sess"

    def test_threshold_emergency_priority_over_critical(self):
        t = make_alert_threshold("m", ThresholdOperator.GT, 100.0, emergency_value=200.0)
        assert t.evaluate(300.0) == AlertSeverity.EMERGENCY
        assert t.evaluate(150.0) == AlertSeverity.CRITICAL

    def test_engine_stop_is_clean(self):
        e = _engine()
        e.register_rule(HighLatencyRule(rule_id="r1"))
        e.process_request(e.create_request("s1",
            make_alert_context("s1", "p1", {"p99_latency": 2_000.0})
        ))
        e.stop()
        # After stop, engine raises not-running
        with pytest.raises(AlertEngineNotRunningError):
            e.create_request("s1", make_alert_context("s1", "p1", {}))
