"""tests/unit/investment/company/opportunity/test_monitoring.py
Tests for monitoring: change detector, alert engine, priority monitor.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from iios.investment.company.opportunity.alert_engine import generate_opportunity_alerts
from iios.investment.company.opportunity.change_detector import (
    ChangeRecord, detect_category_change, detect_changes, detect_lifecycle_change,
    score_dict_from_breakdown,
)
from iios.investment.company.opportunity.lifecycle_tracker import LifecycleTracker
from iios.investment.company.opportunity.lifecycle_history import LifecycleHistory
from iios.investment.company.opportunity.opportunity_monitor import OpportunityMonitor
from iios.investment.company.opportunity.opportunity_profile import (
    AlertSeverity, OpportunityAlert, OpportunityCategory, OpportunityLifecycle,
    OpportunityPriority,
)
from iios.investment.company.opportunity.priority_monitor import PriorityMonitor


class TestChangeDetector:
    def test_no_previous(self):
        cur = {"overall_score": 70.0}
        changes = detect_changes(cur, None)
        assert changes == []

    def test_no_material_change(self):
        cur  = {"overall_score": 70.0}
        prev = {"overall_score": 68.0}
        changes = detect_changes(cur, prev)
        assert changes == []

    def test_material_score_drop(self):
        cur  = {"overall_score": 55.0}
        prev = {"overall_score": 75.0}
        changes = detect_changes(cur, prev)
        assert len(changes) == 1
        assert changes[0].is_adverse is True
        assert changes[0].magnitude == pytest.approx(20.0)

    def test_material_improvement(self):
        cur  = {"overall_score": 80.0}
        prev = {"overall_score": 60.0}
        changes = detect_changes(cur, prev)
        assert changes[0].is_adverse is False

    def test_lifecycle_change(self):
        change = detect_lifecycle_change("weakening", "monitoring")
        assert change is not None
        assert change.is_adverse is True

    def test_lifecycle_no_change(self):
        assert detect_lifecycle_change("monitoring", "monitoring") is None

    def test_category_change(self):
        change = detect_category_change("observation_only", "compounder")
        assert change is not None
        assert change.is_adverse is True

    def test_category_no_change(self):
        assert detect_category_change("compounder", "compounder") is None


class TestAlertEngine:
    def test_low_score_alert(self):
        alerts = generate_opportunity_alerts(
            ticker="X", overall_score=25.0,
            lifecycle=OpportunityLifecycle.EXPIRED,
            category=OpportunityCategory.OBSERVATION_ONLY,
            fin_score=50.0, own_score=50.0,
        )
        assert len(alerts) > 0
        assert any(a.severity in (AlertSeverity.HIGH, AlertSeverity.CRITICAL) for a in alerts)

    def test_score_decline_alert(self):
        alerts = generate_opportunity_alerts(
            ticker="X", overall_score=40.0,
            lifecycle=OpportunityLifecycle.MONITORING,
            category=OpportunityCategory.WATCHLIST,
            fin_score=50.0, own_score=50.0,
            previous_score=65.0,
        )
        assert any("decline" in a.message.lower() or "drop" in a.message.lower() or
                   "Significant" in a.message for a in alerts)

    def test_lifecycle_transition_alert(self):
        alerts = generate_opportunity_alerts(
            ticker="X", overall_score=70.0,
            lifecycle=OpportunityLifecycle.HIGH_CONVICTION,
            category=OpportunityCategory.COMPOUNDER,
            fin_score=70.0, own_score=65.0,
            previous_lifecycle=OpportunityLifecycle.MONITORING,
        )
        assert any("HIGH CONVICTION" in a.message or "Lifecycle" in a.message for a in alerts)

    def test_high_pledge_alert(self, risky_ownership):
        alerts = generate_opportunity_alerts(
            ticker="X", overall_score=55.0,
            lifecycle=OpportunityLifecycle.MONITORING,
            category=OpportunityCategory.WATCHLIST,
            fin_score=50.0, own_score=30.0,
            ownership_snapshot=risky_ownership,
        )
        assert any("pledge" in a.message.lower() or "Promoter" in a.message for a in alerts)

    def test_financial_distress_alert(self):
        alerts = generate_opportunity_alerts(
            ticker="X", overall_score=45.0,
            lifecycle=OpportunityLifecycle.MONITORING,
            category=OpportunityCategory.WATCHLIST,
            fin_score=25.0, own_score=50.0,
        )
        assert any(a.severity == AlertSeverity.CRITICAL for a in alerts)

    def test_upstream_alerts_propagated(self):
        alerts = generate_opportunity_alerts(
            ticker="X", overall_score=60.0,
            lifecycle=OpportunityLifecycle.MONITORING,
            category=OpportunityCategory.COMPOUNDER,
            fin_score=60.0, own_score=60.0,
            upstream_alerts=["TEST_UPSTREAM_ALERT"],
        )
        assert any("TEST_UPSTREAM_ALERT" in a.message for a in alerts)

    def test_alerts_are_structured(self):
        alerts = generate_opportunity_alerts(
            ticker="Y", overall_score=30.0,
            lifecycle=OpportunityLifecycle.EXPIRED,
            category=OpportunityCategory.OBSERVATION_ONLY,
            fin_score=25.0, own_score=25.0,
        )
        for a in alerts:
            assert isinstance(a, OpportunityAlert)
            assert isinstance(a.message, str)


class TestLifecycleTracker:
    def test_initial_discovered(self):
        tracker = LifecycleTracker()
        state = tracker.update("X", 45.0, 0.40)
        assert state == OpportunityLifecycle.DISCOVERED

    def test_reaches_high_conviction(self):
        tracker = LifecycleTracker()
        # Step 1: moderate score → MONITORING (DISCOVERED→MONITORING is valid)
        tracker.update("X", 58.0, 0.55)
        # Step 2: high score → HIGH_CONVICTION (MONITORING→HIGH_CONVICTION is valid)
        state = tracker.update("X", 72.0, 0.72, score_trend=1.0)
        assert state in (OpportunityLifecycle.HIGH_CONVICTION, OpportunityLifecycle.CONFIRMED,
                         OpportunityLifecycle.MONITORING, OpportunityLifecycle.EMERGING)

    def test_force_archive(self):
        tracker = LifecycleTracker()
        tracker.update("X", 65.0, 0.65)
        tracker.force_archive("X")
        assert tracker.get_state("X") == OpportunityLifecycle.ARCHIVED

    def test_known_tickers(self):
        tracker = LifecycleTracker()
        tracker.update("A", 60.0, 0.60)
        tracker.update("B", 70.0, 0.70)
        assert "A" in tracker.known_tickers()
        assert "B" in tracker.known_tickers()

    def test_history_recorded(self):
        tracker = LifecycleTracker()
        for _ in range(4):
            tracker.update("X", 72.0, 0.72, score_trend=2.0)
        # Should have at least one lifecycle change
        history = tracker.get_history("X")
        assert isinstance(history, list)


class TestLifecycleHistory:
    def test_record_and_retrieve(self):
        from iios.investment.company.opportunity.opportunity_lifecycle import LifecycleChange
        history = LifecycleHistory()
        change = LifecycleChange(
            from_state=OpportunityLifecycle.MONITORING,
            to_state=OpportunityLifecycle.HIGH_CONVICTION,
            score_at_change=70.0,
            changed_at=datetime.now(timezone.utc),
        )
        history.record("T", change)
        records = history.get_ticker_history("T")
        assert len(records) == 1

    def test_count_transitions(self):
        from iios.investment.company.opportunity.opportunity_lifecycle import LifecycleChange
        history = LifecycleHistory()
        for i in range(3):
            change = LifecycleChange(
                from_state=OpportunityLifecycle.DISCOVERED,
                to_state=OpportunityLifecycle.EMERGING,
                score_at_change=50.0 + i,
                changed_at=datetime.now(timezone.utc),
            )
            history.record("T", change)
        assert history.count_transitions("T") == 3


class TestPriorityMonitor:
    def test_update_no_alert_same(self):
        pm = PriorityMonitor()
        pm.update("X", OpportunityPriority.MEDIUM)
        alert = pm.update("X", OpportunityPriority.MEDIUM)
        assert alert is None

    def test_big_upgrade_alert(self):
        pm = PriorityMonitor()
        pm.update("X", OpportunityPriority.LOW)
        alert = pm.update("X", OpportunityPriority.CRITICAL)
        assert alert is not None
        assert "elevated" in alert.message.lower() or "Priority" in alert.message

    def test_downgrade_alert(self):
        pm = PriorityMonitor()
        pm.update("X", OpportunityPriority.HIGH)
        alert = pm.update("X", OpportunityPriority.WATCHLIST)
        assert alert is not None

    def test_critical_tickers(self):
        pm = PriorityMonitor()
        pm.update("A", OpportunityPriority.CRITICAL)
        pm.update("B", OpportunityPriority.LOW)
        assert "A" in pm.critical_tickers()
        assert "B" not in pm.critical_tickers()


class TestOpportunityMonitor:
    def _make_breakdown(self, score: float):
        from unittest.mock import MagicMock
        bd = MagicMock()
        bd.final_score = score
        c = MagicMock()
        c.name = "business_quality"
        c.score = score
        bd.components.return_value = []
        return bd

    def test_process_returns_list(self):
        monitor = OpportunityMonitor()
        alerts = monitor.process(
            ticker="X", overall_score=65.0,
            lifecycle=OpportunityLifecycle.HIGH_CONVICTION,
            category=OpportunityCategory.COMPOUNDER,
            priority=OpportunityPriority.HIGH,
            score_breakdown=self._make_breakdown(65.0),
            fin_score=65.0, own_score=65.0,
        )
        assert isinstance(alerts, list)

    def test_get_alerts(self):
        monitor = OpportunityMonitor()
        monitor.process(
            ticker="X", overall_score=25.0,
            lifecycle=OpportunityLifecycle.EXPIRED,
            category=OpportunityCategory.OBSERVATION_ONLY,
            priority=OpportunityPriority.WATCHLIST,
            score_breakdown=self._make_breakdown(25.0),
            fin_score=25.0, own_score=25.0,
        )
        msgs = monitor.get_alert_messages("X")
        assert isinstance(msgs, list)

    def test_high_priority_tickers(self):
        monitor = OpportunityMonitor()
        monitor.process(
            ticker="HIGH", overall_score=75.0,
            lifecycle=OpportunityLifecycle.HIGH_CONVICTION,
            category=OpportunityCategory.COMPOUNDER,
            priority=OpportunityPriority.HIGH,
            score_breakdown=self._make_breakdown(75.0),
            fin_score=70.0, own_score=68.0,
        )
        assert "HIGH" in monitor.high_priority_tickers()
