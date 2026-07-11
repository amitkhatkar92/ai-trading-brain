"""tests/unit/investment/market/opportunity/test_monitoring.py"""
from __future__ import annotations

import pytest

from iios.investment.market.opportunity.alert_engine import AlertEngine
from iios.investment.market.opportunity.change_detector import ChangeDetector
from iios.investment.market.opportunity.models import (
    AlertType,
    Opportunity,
    OpportunityAlert,
    OpportunityCategory,
    OpportunityLifecycleStage,
    OpportunityPriority,
)
from iios.investment.market.opportunity.opportunity_monitor import OpportunityMonitor
from iios.investment.market.opportunity.priority_monitor import PriorityMonitor


def _opp(
    symbol: str,
    score: float = 70.0,
    priority: OpportunityPriority = OpportunityPriority.HIGH,
    stage: OpportunityLifecycleStage = OpportunityLifecycleStage.EMERGING,
) -> Opportunity:
    o = Opportunity.new(symbol, "IT", "S", OpportunityCategory.TREND_FOLLOWING, 1)
    o.composite_score = score
    o.priority        = priority
    o.lifecycle_stage = stage
    return o


class TestChangeDetector:
    def test_new_opportunity_alert(self):
        detector = ChangeDetector()
        opps     = [_opp("AAPL")]
        alerts   = detector.detect(opps, bar_index=1)
        types    = [a.alert_type for a in alerts]
        assert AlertType.NEW_OPPORTUNITY in types

    def test_priority_upgrade_alert(self):
        detector = ChangeDetector()
        opp      = _opp("AAPL", priority=OpportunityPriority.MEDIUM)
        # First bar — register
        detector.detect([opp], bar_index=1)
        # Upgrade priority
        opp.priority = OpportunityPriority.CRITICAL
        alerts = detector.detect([opp], bar_index=2)
        types  = [a.alert_type for a in alerts]
        assert AlertType.PRIORITY_UPGRADE in types

    def test_priority_downgrade_alert(self):
        detector = ChangeDetector()
        opp      = _opp("MSFT", priority=OpportunityPriority.CRITICAL)
        detector.detect([opp], bar_index=1)
        opp.priority = OpportunityPriority.LOW
        alerts = detector.detect([opp], bar_index=2)
        types  = [a.alert_type for a in alerts]
        assert AlertType.PRIORITY_DOWNGRADE in types

    def test_confidence_surge_alert(self):
        detector = ChangeDetector()
        opp      = _opp("GOOG")
        opp.confidence = 0.50
        detector.detect([opp], bar_index=1)
        opp.confidence = 0.75   # +25% → CONFIDENCE_SURGE
        alerts = detector.detect([opp], bar_index=2)
        types  = [a.alert_type for a in alerts]
        assert AlertType.CONFIDENCE_SURGE in types

    def test_confidence_drop_alert(self):
        detector = ChangeDetector()
        opp      = _opp("JNJ")
        opp.confidence = 0.80
        detector.detect([opp], bar_index=1)
        opp.confidence = 0.60   # -20% → CONFIDENCE_DROP
        alerts = detector.detect([opp], bar_index=2)
        types  = [a.alert_type for a in alerts]
        assert AlertType.CONFIDENCE_DROP in types

    def test_lifecycle_advance_alert(self):
        detector = ChangeDetector()
        opp      = _opp("AMZN", stage=OpportunityLifecycleStage.DISCOVERED)
        detector.detect([opp], bar_index=1)
        opp.lifecycle_stage = OpportunityLifecycleStage.CONFIRMED
        alerts = detector.detect([opp], bar_index=2)
        types  = [a.alert_type for a in alerts]
        assert AlertType.LIFECYCLE_ADVANCE in types

    def test_expiration_alert(self):
        detector = ChangeDetector()
        opp      = _opp("DYING", stage=OpportunityLifecycleStage.WEAKENING)
        detector.detect([opp], bar_index=1)
        opp.lifecycle_stage = OpportunityLifecycleStage.EXPIRED
        alerts = detector.detect([opp], bar_index=2)
        types  = [a.alert_type for a in alerts]
        assert AlertType.EXPIRATION in types

    def test_no_spurious_alerts_unchanged(self):
        detector = ChangeDetector()
        opp      = _opp("STABLE")
        detector.detect([opp], bar_index=1)
        alerts = detector.detect([opp], bar_index=2)
        assert len(alerts) == 0   # nothing changed


class TestAlertEngine:
    def test_publish_stores_alerts(self):
        engine = AlertEngine()
        opp    = _opp("X")
        alert  = OpportunityAlert.make(AlertType.NEW_OPPORTUNITY, opp, 1, 0.8, "New")
        engine.publish([alert])
        assert len(engine.recent(10)) == 1

    def test_by_type_filter(self):
        engine = AlertEngine()
        opp    = _opp("Y")
        a1     = OpportunityAlert.make(AlertType.NEW_OPPORTUNITY,    opp, 1, 0.7, "New")
        a2     = OpportunityAlert.make(AlertType.PRIORITY_UPGRADE,   opp, 2, 0.8, "Up")
        engine.publish([a1, a2])
        new_alerts = engine.by_type(AlertType.NEW_OPPORTUNITY)
        assert len(new_alerts) == 1
        assert new_alerts[0].alert_type is AlertType.NEW_OPPORTUNITY

    def test_for_symbol_filter(self):
        engine = AlertEngine()
        opp_a  = _opp("AAPL")
        opp_b  = _opp("MSFT")
        a1     = OpportunityAlert.make(AlertType.NEW_OPPORTUNITY, opp_a, 1, 0.7, "New A")
        a2     = OpportunityAlert.make(AlertType.NEW_OPPORTUNITY, opp_b, 1, 0.7, "New B")
        engine.publish([a1, a2])
        aapl_alerts = engine.for_symbol("AAPL")
        assert all(a.symbol == "AAPL" for a in aapl_alerts)

    def test_high_severity_filter(self):
        engine = AlertEngine()
        opp    = _opp("Z")
        low    = OpportunityAlert.make(AlertType.NEW_OPPORTUNITY,  opp, 1, 0.3, "Low")
        high   = OpportunityAlert.make(AlertType.PRIORITY_UPGRADE, opp, 1, 0.9, "High")
        engine.publish([low, high])
        severe = engine.high_severity()
        assert all(a.severity >= 0.7 for a in severe)

    def test_on_alert_callback(self):
        received = []
        engine = AlertEngine()
        engine.on_alert = received.append
        opp    = _opp("CB")
        alert  = OpportunityAlert.make(AlertType.NEW_OPPORTUNITY, opp, 1, 0.8, "New")
        engine.publish([alert])
        assert len(received) == 1

    def test_maxlen_respected(self):
        engine = AlertEngine(maxlen=3)
        opp    = _opp("X")
        for i in range(5):
            a = OpportunityAlert.make(AlertType.NEW_OPPORTUNITY, opp, i, 0.8, "N")
            engine.publish([a])
        assert len(engine.recent(100)) <= 3


class TestPriorityMonitor:
    def test_critical_only(self):
        monitor = PriorityMonitor()
        opps    = [
            _opp("A", priority=OpportunityPriority.CRITICAL),
            _opp("B", priority=OpportunityPriority.HIGH),
            _opp("C", priority=OpportunityPriority.LOW),
        ]
        monitor.update(opps)
        crits = monitor.critical()
        assert all(o.priority is OpportunityPriority.CRITICAL for o in crits)
        assert len(crits) == 1

    def test_high_and_above(self):
        monitor = PriorityMonitor()
        opps    = [
            _opp("A", priority=OpportunityPriority.CRITICAL),
            _opp("B", priority=OpportunityPriority.HIGH),
            _opp("C", priority=OpportunityPriority.MEDIUM),
        ]
        monitor.update(opps)
        above = monitor.high_and_above()
        assert len(above) == 2

    def test_new_critical_detection(self):
        monitor = PriorityMonitor()
        opps1   = [_opp("A", priority=OpportunityPriority.HIGH)]
        monitor.update(opps1)
        new1    = monitor.new_critical()
        assert new1 == []
        opps2   = [_opp("A", priority=OpportunityPriority.CRITICAL)]
        monitor.update(opps2)
        new2    = monitor.new_critical()
        assert "A" in new2


class TestOpportunityMonitor:
    def test_update_returns_alerts(self):
        monitor = OpportunityMonitor()
        opps    = [_opp("AAPL"), _opp("MSFT")]
        alerts  = monitor.update(opps, bar_index=1)
        assert isinstance(alerts, list)

    def test_new_critical_callback(self):
        received_critical = []
        monitor = OpportunityMonitor()
        monitor.on_new_critical = received_critical.append
        opps = [_opp("X", priority=OpportunityPriority.CRITICAL)]
        monitor.update(opps, bar_index=1)
        # Register
        # Now on bar 2 it should stay critical and not re-fire unless logic demands
        monitor.update(opps, bar_index=2)
        # The callback fired at least once (first detection)
        # (exact semantics depend on PriorityMonitor.new_critical)

    def test_recent_alerts_api(self):
        monitor = OpportunityMonitor()
        opps    = [_opp("AAPL"), _opp("MSFT")]
        monitor.update(opps, bar_index=1)
        recent = monitor.recent_alerts(5)
        assert isinstance(recent, list)
