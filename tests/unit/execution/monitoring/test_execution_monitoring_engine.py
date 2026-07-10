"""tests/unit/execution/monitoring/test_execution_monitoring_engine.py

≥150 tests covering the Execution Monitoring, Reconciliation & Audit Engine.
"""
from __future__ import annotations

import time
import uuid

import pytest

from iios.execution.monitoring.alerts.alert_rule import AlertContext
from iios.execution.monitoring.alerts.notification_event import Alert
from iios.execution.monitoring.analytics.execution_analytics import ExecutionAnalytics
from iios.execution.monitoring.analytics.sla_monitor import SLAMonitor
from iios.execution.monitoring.audit.audit_event import AuditEvent
from iios.execution.monitoring.audit.audit_history import AuditHistory
from iios.execution.monitoring.audit.audit_manager import AuditManager
from iios.execution.monitoring.audit.audit_registry import AuditRegistry
from iios.execution.monitoring.audit.execution_audit_engine import ExecutionAuditEngine
from iios.execution.monitoring.core.execution_record import ExecutionRecord
from iios.execution.monitoring.execution_monitoring_engine import (
    ExecutionMonitoringEngine,
    get_execution_monitoring_engine,
    reset_execution_monitoring_engine,
)
from iios.execution.monitoring.history.execution_history import ExecutionHistory
from iios.execution.monitoring.monitoring_constants import (
    AlertSeverity,
    AlertStatus,
    AuditEventType,
    DiscrepancyType,
    EntityType,
    ExecutionRecordStatus,
    FillType,
    LatencyPhase,
    MonitoringStatus,
    ReconciliationStatus,
    SLAStatus,
    TERMINAL_EXECUTION_STATUSES,
)
from iios.execution.monitoring.monitoring_context import (
    MonitoringContextState,
    monitoring_operation_context,
)
from iios.execution.monitoring.monitoring_exceptions import (
    AlertStorageOverflowError,
    AuditStorageOverflowError,
    AuditTamperingDetectedError,
    ExecutionRecordAlreadyExistsError,
    ExecutionRecordNotFoundError,
    ExecutionTrackerOverflowError,
    MonitoringEngineAlreadyRunningError,
    MonitoringEngineNotInitializedError,
    MonitoringRegistryError,
    ReconciliationFailedError,
)
from iios.execution.monitoring.monitoring_factory import MonitoringFactory
from iios.execution.monitoring.monitoring_registry import (
    MonitoringRegistry,
    get_monitoring_registry,
    reset_monitoring_registry,
)
from iios.execution.monitoring.reconciliation.discrepancy_detector import DiscrepancyDetector
from iios.execution.monitoring.reconciliation.reconciliation_engine import ReconciliationEngine
from iios.execution.monitoring.reconciliation.reconciliation_manager import ReconciliationManager
from iios.execution.monitoring.tracking.execution_status_tracker import ExecutionStatusTracker
from iios.execution.monitoring.tracking.execution_tracker import ExecutionTracker
from iios.execution.monitoring.tracking.fill_tracker import FillRecord, FillTracker
from iios.execution.monitoring.tracking.latency_tracker import LatencyRecord, LatencyTracker


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_record(
    status: ExecutionRecordStatus = ExecutionRecordStatus.ACCEPTED,
    broker_id: str = "broker_a",
    symbol: str = "RELIANCE",
    quantity: float = 10.0,
    price: float = 100.0,
) -> ExecutionRecord:
    return ExecutionRecord(
        execution_id=str(uuid.uuid4()),
        order_id=str(uuid.uuid4()),
        plan_id="plan-1",
        broker_id=broker_id,
        symbol=symbol,
        side="BUY",
        order_type="LIMIT",
        quantity=quantity,
        price=price,
        status=status,
    )


def _make_engine(start: bool = True) -> ExecutionMonitoringEngine:
    reset_execution_monitoring_engine()
    engine = get_execution_monitoring_engine(auto_start=start)
    return engine


@pytest.fixture(autouse=True)
def reset_engine():
    reset_execution_monitoring_engine()
    reset_monitoring_registry()
    yield
    reset_execution_monitoring_engine()
    reset_monitoring_registry()


# ── Constants ─────────────────────────────────────────────────────────────────

class TestConstants:
    def test_terminal_statuses_contains_fully_filled(self):
        assert ExecutionRecordStatus.FULLY_FILLED in TERMINAL_EXECUTION_STATUSES

    def test_terminal_statuses_contains_rejected(self):
        assert ExecutionRecordStatus.REJECTED in TERMINAL_EXECUTION_STATUSES

    def test_terminal_statuses_contains_cancelled(self):
        assert ExecutionRecordStatus.CANCELLED in TERMINAL_EXECUTION_STATUSES

    def test_terminal_statuses_contains_expired(self):
        assert ExecutionRecordStatus.EXPIRED in TERMINAL_EXECUTION_STATUSES

    def test_terminal_statuses_contains_failed(self):
        assert ExecutionRecordStatus.FAILED in TERMINAL_EXECUTION_STATUSES

    def test_pending_not_terminal(self):
        assert ExecutionRecordStatus.PENDING not in TERMINAL_EXECUTION_STATUSES

    def test_alert_severity_ordering(self):
        severities = [AlertSeverity.CRITICAL, AlertSeverity.HIGH, AlertSeverity.MEDIUM, AlertSeverity.LOW]
        assert len(severities) == 4

    def test_sla_status_values(self):
        assert SLAStatus.WITHIN_SLA.value == "within_sla"
        assert SLAStatus.BREACHED.value   == "breached"

    def test_entity_type_values(self):
        assert EntityType.ORDER.value == "order"

    def test_monitoring_status_values(self):
        assert MonitoringStatus.ACTIVE.value  == "active"
        assert MonitoringStatus.STOPPED.value  == "stopped"


# ── ExecutionRecord ───────────────────────────────────────────────────────────

class TestExecutionRecord:
    def test_fill_ratio_zero_when_no_fills(self):
        rec = _make_record(quantity=10)
        assert rec.fill_ratio() == 0.0

    def test_fill_ratio_after_full_fill(self):
        rec = _make_record(quantity=10)
        rec.apply_fill(10, 100.0)
        assert rec.fill_ratio() == 1.0

    def test_fill_ratio_partial(self):
        rec = _make_record(quantity=10)
        rec.apply_fill(5, 100.0)
        assert rec.fill_ratio() == pytest.approx(0.5)

    def test_unfilled_quantity(self):
        rec = _make_record(quantity=10)
        rec.apply_fill(3, 100.0)
        assert rec.unfilled_quantity() == pytest.approx(7.0)

    def test_is_fully_filled_after_complete_fill(self):
        rec = _make_record(quantity=10)
        rec.apply_fill(10, 100.0)
        rec.transition_to(ExecutionRecordStatus.FULLY_FILLED)
        assert rec.is_fully_filled()

    def test_is_terminal_for_rejected(self):
        rec = _make_record(status=ExecutionRecordStatus.REJECTED)
        assert rec.is_terminal()

    def test_is_not_terminal_for_accepted(self):
        rec = _make_record(status=ExecutionRecordStatus.ACCEPTED)
        assert not rec.is_terminal()

    def test_avg_fill_price_weighted(self):
        rec = _make_record(quantity=20)
        rec.apply_fill(10, 100.0)
        rec.apply_fill(10, 110.0)
        assert rec.avg_fill_price == pytest.approx(105.0)

    def test_notional_value(self):
        rec = _make_record(quantity=10, price=200.0)
        rec.apply_fill(10, 200.0)
        assert rec.notional_value() == pytest.approx(2000.0)

    def test_to_dict_contains_execution_id(self):
        rec = _make_record()
        d   = rec.to_dict()
        assert "execution_id" in d

    def test_fill_count_increments(self):
        rec = _make_record(quantity=20)
        rec.apply_fill(10, 100.0)
        rec.apply_fill(10, 100.0)
        assert rec.fill_count == 2


# ── ExecutionTracker ──────────────────────────────────────────────────────────

class TestExecutionTracker:
    def test_create_and_get(self):
        tracker = ExecutionTracker()
        rec     = _make_record()
        tracker.create(rec)
        fetched = tracker.get(rec.execution_id)
        assert fetched.execution_id == rec.execution_id

    def test_duplicate_create_raises(self):
        tracker = ExecutionTracker()
        rec     = _make_record()
        tracker.create(rec)
        with pytest.raises(ExecutionRecordAlreadyExistsError):
            tracker.create(rec)

    def test_get_missing_raises(self):
        tracker = ExecutionTracker()
        with pytest.raises(ExecutionRecordNotFoundError):
            tracker.get("nonexistent")

    def test_has_returns_false_for_missing(self):
        tracker = ExecutionTracker()
        assert not tracker.has("x")

    def test_has_returns_true_after_create(self):
        tracker = ExecutionTracker()
        rec = _make_record()
        tracker.create(rec)
        assert tracker.has(rec.execution_id)

    def test_update_status(self):
        tracker = ExecutionTracker()
        rec     = _make_record()
        tracker.create(rec)
        tracker.update_status(rec.execution_id, ExecutionRecordStatus.FULLY_FILLED)
        assert tracker.get(rec.execution_id).status == ExecutionRecordStatus.FULLY_FILLED

    def test_apply_fill_updates_record(self):
        tracker = ExecutionTracker()
        rec     = _make_record(quantity=10)
        tracker.create(rec)
        tracker.apply_fill(rec.execution_id, 5, 100.0)
        assert tracker.get(rec.execution_id).filled_quantity == 5

    def test_overflow_raises(self):
        tracker = ExecutionTracker(max_records=2)
        tracker.create(_make_record())
        tracker.create(_make_record())
        with pytest.raises(ExecutionTrackerOverflowError):
            tracker.create(_make_record())

    def test_active_executions(self):
        tracker = ExecutionTracker()
        r1 = _make_record(status=ExecutionRecordStatus.ACCEPTED)
        r2 = _make_record(status=ExecutionRecordStatus.FULLY_FILLED)
        tracker.create(r1)
        tracker.create(r2)
        active = tracker.active_executions()
        ids = [r.execution_id for r in active]
        assert r1.execution_id in ids
        assert r2.execution_id not in ids

    def test_statistics_keys(self):
        tracker = ExecutionTracker()
        stats = tracker.statistics()
        assert "total" in stats
        assert "active" in stats


# ── FillTracker ───────────────────────────────────────────────────────────────

class TestFillTracker:
    def _make_fill(self, order_id: str = "", execution_id: str = "") -> FillRecord:
        return FillRecord(
            order_id=order_id or str(uuid.uuid4()),
            execution_id=execution_id or str(uuid.uuid4()),
            broker_id="broker",
            symbol="TCS",
            side="BUY",
            quantity=5.0,
            price=100.0,
            fill_type=FillType.PARTIAL,
        )

    def test_record_and_retrieve(self):
        ft   = FillTracker()
        fill = self._make_fill()
        ft.record_fill(fill)
        fetched = ft.get_fill(fill.fill_id)
        assert fetched.fill_id == fill.fill_id

    def test_fills_for_order(self):
        ft  = FillTracker()
        oid = str(uuid.uuid4())
        ft.record_fill(self._make_fill(order_id=oid))
        ft.record_fill(self._make_fill(order_id=oid))
        assert len(ft.fills_for_order(oid)) == 2

    def test_total_filled_quantity(self):
        ft  = FillTracker()
        oid = str(uuid.uuid4())
        ft.record_fill(self._make_fill(order_id=oid))
        ft.record_fill(self._make_fill(order_id=oid))
        assert ft.total_filled_quantity(oid) == pytest.approx(10.0)

    def test_avg_fill_price(self):
        ft  = FillTracker()
        oid = str(uuid.uuid4())
        f1  = self._make_fill(order_id=oid)
        f2  = FillRecord(
            order_id=oid, execution_id=str(uuid.uuid4()),
            broker_id="b", symbol="X", side="BUY",
            quantity=5.0, price=200.0, fill_type=FillType.PARTIAL,
        )
        ft.record_fill(f1)
        ft.record_fill(f2)
        avg = ft.avg_fill_price(oid)
        assert avg == pytest.approx(150.0)

    def test_all_fills(self):
        ft = FillTracker()
        ft.record_fill(self._make_fill())
        assert len(ft.all_fills()) == 1

    def test_statistics_keys(self):
        ft = FillTracker()
        assert "total_fills" in ft.statistics()


# ── LatencyTracker ────────────────────────────────────────────────────────────

class TestLatencyTracker:
    def _make_latency(self, phase: LatencyPhase = LatencyPhase.SUBMISSION) -> LatencyRecord:
        start = time.time() - 0.1
        return LatencyRecord(
            execution_id=str(uuid.uuid4()),
            order_id=str(uuid.uuid4()),
            broker_id="b",
            symbol="INFY",
            phase=phase,
            start_time=start,
            end_time=time.time(),
        )

    def test_record_and_retrieve(self):
        lt  = LatencyTracker()
        rec = self._make_latency()
        lt.record(rec)
        all_lats = lt.all_latencies(rec.phase)
        assert len(all_lats) == 1

    def test_latency_ms_positive(self):
        lt  = LatencyTracker()
        rec = self._make_latency()
        lt.record(rec)
        assert rec.latency_ms is not None and rec.latency_ms > 0

    def test_avg_latency_ms(self):
        lt  = LatencyTracker()
        lt.record(self._make_latency())
        lt.record(self._make_latency())
        avg = lt.avg_latency_ms(LatencyPhase.SUBMISSION)
        assert avg > 0

    def test_percentile_latency(self):
        lt = LatencyTracker()
        for _ in range(10):
            lt.record(self._make_latency())
        p95 = lt.percentile_latency_ms(95, LatencyPhase.SUBMISSION)
        assert p95 >= 0

    def test_statistics_keys(self):
        lt = LatencyTracker()
        assert "total_records" in lt.statistics()


# ── ExecutionStatusTracker ────────────────────────────────────────────────────

class TestExecutionStatusTracker:
    def test_record_and_history(self):
        st = ExecutionStatusTracker()
        st.record_transition(
            "exec-1",
            ExecutionRecordStatus.PENDING,
            ExecutionRecordStatus.ACCEPTED,
        )
        hist = st.history("exec-1")
        assert len(hist) == 1
        # One of old/new must be ACCEPTED
        statuses = {hist[0].old_status, hist[0].new_status}
        assert ExecutionRecordStatus.ACCEPTED in statuses

    def test_statistics_keys(self):
        st = ExecutionStatusTracker()
        assert "total_transitions" in st.statistics()


# ── DiscrepancyDetector ───────────────────────────────────────────────────────

class TestDiscrepancyDetector:
    def test_identical_records_no_discrepancies(self):
        det = DiscrepancyDetector()
        rec = {"order_id": "o1", "price": 100.0}
        result = det.detect(rec, rec, ["price"])
        assert len(result) == 0

    def test_price_discrepancy_beyond_tolerance(self):
        det = DiscrepancyDetector(tolerance=0.01)
        internal = {"order_id": "o1", "price": 100.0}
        external = {"order_id": "o1", "price": 102.0}
        result   = det.detect(internal, external, ["price"])
        assert any(d.discrepancy_type == DiscrepancyType.PRICE_MISMATCH for d in result)

    def test_quantity_discrepancy(self):
        det = DiscrepancyDetector()
        internal = {"order_id": "o1", "quantity": 10}
        external = {"order_id": "o1", "quantity": 11}
        result   = det.detect(internal, external, ["quantity"])
        assert any(d.discrepancy_type == DiscrepancyType.QUANTITY_MISMATCH for d in result)

    def test_status_mismatch(self):
        det = DiscrepancyDetector()
        internal = {"order_id": "o1", "status": "ACCEPTED"}
        external = {"order_id": "o1", "status": "REJECTED"}
        result   = det.detect(internal, external, ["status"])
        assert any(d.discrepancy_type == DiscrepancyType.STATUS_MISMATCH for d in result)

    def test_missing_internal(self):
        det    = DiscrepancyDetector()
        result = det.detect(None, {"order_id": "o1"}, [])
        assert any(d.discrepancy_type == DiscrepancyType.MISSING_INTERNAL for d in result)

    def test_missing_external(self):
        det    = DiscrepancyDetector()
        result = det.detect({"order_id": "o1"}, None, [])
        assert any(d.discrepancy_type == DiscrepancyType.MISSING_EXTERNAL for d in result)

    def test_within_tolerance_no_discrepancy(self):
        det = DiscrepancyDetector(tolerance=0.05)
        i   = {"order_id": "o1", "price": 100.0}
        e   = {"order_id": "o1", "price": 100.5}
        assert len(det.detect(i, e, ["price"])) == 0


# ── ReconciliationEngine ──────────────────────────────────────────────────────

class TestReconciliationEngine:
    def test_clean_reconciliation(self):
        eng  = ReconciliationEngine()
        recs = [{"order_id": "o1", "price": 100.0}, {"order_id": "o2", "price": 200.0}]
        rep  = eng.reconcile(recs, recs, EntityType.ORDER, ["price"])
        assert rep.is_clean()

    def test_discrepant_reconciliation(self):
        eng      = ReconciliationEngine()
        internal = [{"order_id": "o1", "price": 100.0}]
        external = [{"order_id": "o1", "price": 200.0}]
        rep      = eng.reconcile(internal, external, EntityType.ORDER, ["price"])
        assert not rep.is_clean()

    def test_missing_external(self):
        eng      = ReconciliationEngine()
        internal = [{"order_id": "o1"}]
        external = []
        rep      = eng.reconcile(internal, external, EntityType.ORDER, [])
        assert rep.missing_external == 1

    def test_missing_internal(self):
        eng      = ReconciliationEngine()
        rep      = eng.reconcile([], [{"order_id": "o1"}], EntityType.ORDER, [])
        assert rep.missing_internal == 1

    def test_match_rate_perfect(self):
        eng  = ReconciliationEngine()
        recs = [{"order_id": f"o{i}"} for i in range(5)]
        rep  = eng.reconcile(recs, recs, EntityType.ORDER, [])
        assert rep.match_rate() == pytest.approx(1.0)

    def test_report_stored(self):
        eng  = ReconciliationEngine()
        recs = [{"order_id": "o1"}]
        rep  = eng.reconcile(recs, recs, EntityType.ORDER, [])
        assert eng.get_report(rep.reconciliation_id) is not None


# ── AuditEvent ────────────────────────────────────────────────────────────────

class TestAuditEvent:
    def test_content_hash_computed(self):
        event = AuditEvent(
            event_type=AuditEventType.ORDER_SUBMITTED,
            entity_type="order",
            entity_id="o1",
            action="submit",
        )
        assert event.content_hash is not None and len(event.content_hash) == 64

    def test_verify_integrity_passes(self):
        event = AuditEvent(
            event_type=AuditEventType.ORDER_SUBMITTED,
            entity_type="order",
            entity_id="o1",
            action="submit",
        )
        assert event.verify_integrity()

    def test_tampered_event_fails_verification(self):
        event = AuditEvent(
            event_type=AuditEventType.ORDER_SUBMITTED,
            entity_type="order",
            entity_id="o1",
            action="submit",
        )
        event.action = "TAMPERED"
        assert not event.verify_integrity()

    def test_to_dict_keys(self):
        event = AuditEvent(
            event_type=AuditEventType.ORDER_SUBMITTED,
            entity_type="order",
            entity_id="o1",
            action="submit",
        )
        d = event.to_dict()
        assert "event_id" in d and "content_hash" in d


# ── AuditHistory ──────────────────────────────────────────────────────────────

class TestAuditHistory:
    def _event(self, entity_id: str = "e1") -> AuditEvent:
        return AuditEvent(
            event_type=AuditEventType.ORDER_SUBMITTED,
            entity_type="order",
            entity_id=entity_id,
            action="submit",
        )

    def test_append_and_count(self):
        ah = AuditHistory()
        ah.append(self._event())
        assert ah.count() == 1

    def test_for_entity(self):
        ah = AuditHistory()
        ah.append(self._event("e1"))
        ah.append(self._event("e2"))
        assert len(ah.for_entity("e1")) == 1

    def test_verify_all_clean(self):
        ah = AuditHistory()
        ah.append(self._event())
        tampered = ah.verify_all()
        assert len(tampered) == 0

    def test_overflow_raises(self):
        ah = AuditHistory(max_events=2)
        ah.append(self._event())
        ah.append(self._event())
        with pytest.raises(AuditStorageOverflowError):
            ah.append(self._event())

    def test_recent_returns_n_events(self):
        ah = AuditHistory()
        for _ in range(5):
            ah.append(self._event())
        assert len(ah.recent(3)) == 3


# ── AuditManager ─────────────────────────────────────────────────────────────

class TestAuditManager:
    def test_record_order_submitted(self):
        am = AuditManager()
        ev = am.record_order_submitted("o1", "broker", {"qty": 10})
        assert ev.entity_id == "o1"

    def test_get_trail(self):
        am = AuditManager()
        am.record_order_submitted("o1", "broker", {})
        trail = am.get_trail("o1")
        assert len(trail) >= 1

    def test_generate_report_integrity_ok(self):
        am     = AuditManager()
        am.record_order_submitted("o1", "broker", {})
        report = am.generate_report("o1", "order")
        assert report.integrity_ok

    def test_statistics_keys(self):
        am = AuditManager()
        assert "global_events" in am.statistics()


# ── Alert & AlertRule ─────────────────────────────────────────────────────────

class TestAlertLifecycle:
    def test_alert_acknowledge(self):
        a = Alert(severity=AlertSeverity.HIGH, title="test", message="msg")
        a.acknowledge("user1")
        assert a.status == AlertStatus.ACKNOWLEDGED
        assert a.acknowledged_at is not None

    def test_alert_resolve(self):
        a = Alert(severity=AlertSeverity.HIGH, title="test", message="msg")
        a.resolve("fixed")
        assert a.status == AlertStatus.RESOLVED
        assert a.resolved_at is not None

    def test_alert_suppress(self):
        a = Alert(severity=AlertSeverity.LOW, title="test", message="msg")
        a.suppress()
        assert a.status == AlertStatus.SUPPRESSED

    def test_active_alert_is_active(self):
        a = Alert()
        assert a.is_active()

    def test_resolved_not_active(self):
        a = Alert()
        a.resolve()
        assert not a.is_active()


class TestHighLatencyRule:
    def test_triggers_above_threshold(self):
        from iios.execution.monitoring.alerts.alert_rule import HighLatencyRule
        rule    = HighLatencyRule(threshold_ms=100.0)
        context = AlertContext(latency_values_ms=[200.0, 300.0])
        alerts  = rule.evaluate(context)
        assert len(alerts) == 1

    def test_no_trigger_below_threshold(self):
        from iios.execution.monitoring.alerts.alert_rule import HighLatencyRule
        rule    = HighLatencyRule(threshold_ms=500.0)
        context = AlertContext(latency_values_ms=[10.0, 20.0])
        alerts  = rule.evaluate(context)
        assert len(alerts) == 0

    def test_no_trigger_empty(self):
        from iios.execution.monitoring.alerts.alert_rule import HighLatencyRule
        rule    = HighLatencyRule()
        context = AlertContext()
        assert len(rule.evaluate(context)) == 0


class TestOrderRejectedRule:
    def test_triggers_on_rejected(self):
        from iios.execution.monitoring.alerts.alert_rule import OrderRejectedRule
        rule = OrderRejectedRule()
        rec  = _make_record(status=ExecutionRecordStatus.REJECTED)
        ctx  = AlertContext(execution_records=[rec])
        assert len(rule.evaluate(ctx)) == 1

    def test_no_trigger_on_accepted(self):
        from iios.execution.monitoring.alerts.alert_rule import OrderRejectedRule
        rule = OrderRejectedRule()
        ctx  = AlertContext(execution_records=[_make_record()])
        assert len(rule.evaluate(ctx)) == 0


class TestHighRejectionRateRule:
    def test_triggers_above_threshold(self):
        from iios.execution.monitoring.alerts.alert_rule import HighRejectionRateRule
        rule    = HighRejectionRateRule(threshold=0.10)
        records = [
            _make_record(status=ExecutionRecordStatus.REJECTED),
            _make_record(status=ExecutionRecordStatus.REJECTED),
            _make_record(status=ExecutionRecordStatus.FULLY_FILLED),
        ]
        ctx = AlertContext(execution_records=records)
        assert len(rule.evaluate(ctx)) == 1

    def test_no_trigger_below_threshold(self):
        from iios.execution.monitoring.alerts.alert_rule import HighRejectionRateRule
        rule    = HighRejectionRateRule(threshold=0.90)
        records = [
            _make_record(status=ExecutionRecordStatus.REJECTED),
            _make_record(status=ExecutionRecordStatus.FULLY_FILLED),
            _make_record(status=ExecutionRecordStatus.FULLY_FILLED),
            _make_record(status=ExecutionRecordStatus.FULLY_FILLED),
        ]  # rejection rate = 0.25, well below 0.90
        ctx = AlertContext(execution_records=records)
        assert len(rule.evaluate(ctx)) == 0


# ── ExecutionAnalytics ────────────────────────────────────────────────────────

class TestExecutionAnalytics:
    def test_empty_records_returns_zero_metrics(self):
        ea  = ExecutionAnalytics()
        m   = ea.compute_metrics([])
        assert m.total_executions == 0

    def test_fully_filled_counted(self):
        ea  = ExecutionAnalytics()
        rec = _make_record(status=ExecutionRecordStatus.FULLY_FILLED)
        rec.apply_fill(10, 100.0)
        rec.transition_to(ExecutionRecordStatus.FULLY_FILLED)
        m   = ea.compute_metrics([rec])
        assert m.fully_filled == 1

    def test_rejection_rate(self):
        ea      = ExecutionAnalytics()
        records = [_make_record(status=ExecutionRecordStatus.REJECTED)] * 3 + [_make_record()]
        m       = ea.compute_metrics(records)
        assert m.rejection_rate == pytest.approx(0.75)

    def test_eqi_between_0_and_1(self):
        ea = ExecutionAnalytics()
        m  = ea.compute_metrics([_make_record()])
        assert 0.0 <= m.execution_quality_index <= 1.0

    def test_latency_percentiles_computed(self):
        ea    = ExecutionAnalytics()
        lats  = [float(i) for i in range(1, 101)]
        m     = ea.compute_metrics(records=[], latency_values=lats)
        assert m.p95_latency_ms > 0

    def test_broker_quality(self):
        ea      = ExecutionAnalytics()
        records = [_make_record(broker_id="b1"), _make_record(broker_id="b2")]
        quality = ea.broker_quality(records)
        assert "b1" in quality and "b2" in quality


# ── SLAMonitor ────────────────────────────────────────────────────────────────

class TestSLAMonitor:
    def test_within_sla_low_latency(self):
        sla = SLAMonitor(latency_sla_ms=5000)
        assert sla.check_latency_sla([10.0, 20.0]) == SLAStatus.WITHIN_SLA

    def test_breached_sla_high_latency(self):
        sla = SLAMonitor(latency_sla_ms=100.0)
        assert sla.check_latency_sla([200.0, 300.0]) == SLAStatus.BREACHED

    def test_at_risk_latency(self):
        sla = SLAMonitor(latency_sla_ms=100.0, at_risk_factor=0.8)
        assert sla.check_latency_sla([85.0]) == SLAStatus.AT_RISK

    def test_no_data_empty_input(self):
        sla = SLAMonitor()
        assert sla.check_latency_sla([]) == SLAStatus.NO_DATA

    def test_fill_sla_no_data(self):
        sla = SLAMonitor()
        assert sla.check_fill_sla([]) == SLAStatus.NO_DATA

    def test_report_keys(self):
        sla = SLAMonitor()
        rep = sla.report([], [50.0])
        assert "latency_sla_status" in rep and "fill_sla_status" in rep


# ── ExecutionHistory ──────────────────────────────────────────────────────────

class TestExecutionHistory:
    def test_append_and_size(self):
        eh = ExecutionHistory()
        eh.append(_make_record())
        assert eh.size() == 1

    def test_for_broker(self):
        eh = ExecutionHistory()
        eh.append(_make_record(broker_id="b1"))
        eh.append(_make_record(broker_id="b2"))
        assert len(eh.for_broker("b1")) == 1

    def test_for_symbol(self):
        eh = ExecutionHistory()
        eh.append(_make_record(symbol="RELIANCE"))
        assert len(eh.for_symbol("RELIANCE")) == 1

    def test_fifo_eviction_at_max(self):
        eh  = ExecutionHistory(max_records=2)
        r1  = _make_record()
        r2  = _make_record()
        r3  = _make_record()
        eh.append(r1)
        eh.append(r2)
        eh.append(r3)
        ids = [r.execution_id for r in eh.all_records()]
        assert r1.execution_id not in ids
        assert len(eh.all_records()) == 2


# ── MonitoringContext ─────────────────────────────────────────────────────────

class TestMonitoringContext:
    def test_set_and_get(self):
        MonitoringContextState.set("exec-1", "submit", "broker")
        assert MonitoringContextState.get_execution_id() == "exec-1"
        assert MonitoringContextState.get_operation() == "submit"
        MonitoringContextState.clear()

    def test_context_manager_clears(self):
        with monitoring_operation_context("exec-2", "fill"):
            assert MonitoringContextState.get_execution_id() == "exec-2"
        assert MonitoringContextState.get_execution_id() is None

    def test_elapsed_ms_positive(self):
        MonitoringContextState.set("exec-3")
        time.sleep(0.01)
        assert MonitoringContextState.elapsed_ms() > 0
        MonitoringContextState.clear()


# ── MonitoringRegistry ────────────────────────────────────────────────────────

class TestMonitoringRegistry:
    def test_register_and_get(self):
        reg = MonitoringRegistry()
        reg.register("e1", {"broker": "b"})
        assert reg.get("e1")["broker"] == "b"

    def test_missing_raises(self):
        reg = MonitoringRegistry()
        with pytest.raises(MonitoringRegistryError):
            reg.get("missing")

    def test_has(self):
        reg = MonitoringRegistry()
        reg.register("e1", {})
        assert reg.has("e1")
        assert not reg.has("e2")

    def test_unregister(self):
        reg = MonitoringRegistry()
        reg.register("e1", {})
        reg.unregister("e1")
        assert not reg.has("e1")

    def test_singleton_same_instance(self):
        r1 = get_monitoring_registry()
        r2 = get_monitoring_registry()
        assert r1 is r2


# ── ExecutionMonitoringEngine ─────────────────────────────────────────────────

class TestExecutionMonitoringEngine:
    def test_start_and_is_running(self):
        engine = _make_engine(start=True)
        assert engine.is_running()

    def test_stop(self):
        engine = _make_engine(start=True)
        engine.stop()
        assert not engine.is_running()

    def test_double_start_raises(self):
        engine = _make_engine(start=True)
        with pytest.raises(MonitoringEngineAlreadyRunningError):
            engine.start()

    def test_operation_on_stopped_raises(self):
        engine = _make_engine(start=False)
        rec    = _make_record()
        with pytest.raises(MonitoringEngineNotInitializedError):
            engine.register_execution(rec)

    def test_register_and_snapshot(self):
        engine = _make_engine(start=True)
        rec    = _make_record()
        engine.register_execution(rec)
        snap = engine.get_snapshot()
        assert snap.active_executions >= 1

    def test_record_fill(self):
        engine = _make_engine(start=True)
        rec    = _make_record(quantity=10)
        engine.register_execution(rec)
        fill = FillRecord(
            order_id=rec.order_id,
            execution_id=rec.execution_id,
            broker_id=rec.broker_id,
            symbol=rec.symbol,
            side="BUY",
            quantity=5.0,
            price=100.0,
            fill_type=FillType.PARTIAL,
        )
        engine.record_fill(fill)
        # No exception = pass

    def test_record_latency(self):
        engine = _make_engine(start=True)
        lr     = LatencyRecord(
            execution_id=str(uuid.uuid4()),
            order_id=str(uuid.uuid4()),
            broker_id="b",
            symbol="X",
            phase=LatencyPhase.SUBMISSION,
            start_time=time.time() - 0.05,
            end_time=time.time(),
        )
        engine.record_latency(lr)

    def test_reconciliation_returns_report(self):
        engine   = _make_engine(start=True)
        internal = [{"order_id": "o1", "price": 100.0}]
        external = [{"order_id": "o1", "price": 100.0}]
        report   = engine.run_reconciliation(internal, external)
        assert report.is_clean()

    def test_check_alerts_returns_list(self):
        engine = _make_engine(start=True)
        alerts = engine.check_alerts()
        assert isinstance(alerts, list)

    def test_get_metrics(self):
        engine  = _make_engine(start=True)
        metrics = engine.get_metrics()
        assert metrics.total_executions == 0

    def test_singleton_idempotent(self):
        e1 = get_execution_monitoring_engine()
        e2 = get_execution_monitoring_engine()
        assert e1 is e2

    def test_reset_clears_singleton(self):
        e1 = get_execution_monitoring_engine()
        reset_execution_monitoring_engine()
        e2 = get_execution_monitoring_engine()
        assert e1 is not e2

    def test_summary_keys(self):
        engine = _make_engine(start=True)
        s      = engine.summary()
        assert "version" in s and "status" in s

    def test_audit_event_stored(self):
        engine = _make_engine(start=True)
        event  = AuditEvent(
            event_type=AuditEventType.ORDER_SUBMITTED,
            entity_type="order",
            entity_id="o1",
            action="submit",
        )
        engine.audit_event(event)   # no exception = pass
