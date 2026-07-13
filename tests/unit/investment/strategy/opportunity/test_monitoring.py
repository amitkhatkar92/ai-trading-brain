"""tests/unit/investment/strategy/opportunity/test_monitoring.py"""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone

from iios.investment.strategy.opportunity.change_detector import ChangeDetector
from iios.investment.strategy.opportunity.strategy_alerts import (
    AlertRegistry, AlertSeverity, AlertType, StrategyAlert
)
from iios.investment.strategy.opportunity.priority_monitor import PriorityMonitor
from iios.investment.strategy.opportunity.opportunity_monitor import OpportunityMonitor
from iios.investment.strategy.opportunity.strategy_opportunity import (
    StrategyOpportunity, OpportunityState
)
from iios.investment.strategy.opportunity.market_opportunity import (
    MarketRegime, VolatilityRegime
)
from tests.unit.investment.strategy.opportunity.conftest import (
    make_market_opp, make_company_opp
)


def _active_opp(opp_id="o1", state=OpportunityState.RECOMMENDED):
    opp = StrategyOpportunity(
        opportunity_id=opp_id,
        strategy_id="s1",
        strategy_name="Test",
        market_opportunity_id="mkt-1",
        company_opportunity_id=None,
        state=state,
        matching_score=70.0,
        suitability_score=65.0,
        ranking_score=68.0,
    )
    return opp


class TestChangeDetector:
    def test_same_snapshot_no_changes(self):
        opp   = make_market_opp()
        changes = ChangeDetector().detect_market_changes(opp, opp)
        assert changes == []

    def test_regime_shift_detected(self):
        prev = make_market_opp(regime=MarketRegime.BULL)
        curr = make_market_opp(regime=MarketRegime.BEAR)
        changes = ChangeDetector().detect_market_changes(prev, curr)
        types = [c.change_type for c in changes]
        assert "regime_shift" in types

    def test_bull_to_bear_is_critical(self):
        prev = make_market_opp(regime=MarketRegime.BULL)
        curr = make_market_opp(regime=MarketRegime.BEAR)
        changes = ChangeDetector().detect_market_changes(prev, curr)
        regime_change = next(c for c in changes if c.change_type == "regime_shift")
        assert regime_change.severity == "critical"
        assert regime_change.requires_reeval

    def test_volatility_spike_detected(self):
        prev = make_market_opp(vol_regime=VolatilityRegime.LOW)
        curr = make_market_opp(vol_regime=VolatilityRegime.HIGH)
        changes = ChangeDetector().detect_market_changes(prev, curr)
        types = [c.change_type for c in changes]
        assert "volatility_shift" in types

    def test_direction_flip_detected(self):
        prev = make_market_opp(direction="long")
        curr = make_market_opp(direction="short")
        changes = ChangeDetector().detect_market_changes(prev, curr)
        types = [c.change_type for c in changes]
        assert "direction_flip" in types
        flip = next(c for c in changes if c.change_type == "direction_flip")
        assert flip.severity == "critical"

    def test_confidence_drop_detected(self):
        prev = make_market_opp(confidence=0.90)
        curr = make_market_opp(confidence=0.55)
        changes = ChangeDetector().detect_market_changes(prev, curr)
        types = [c.change_type for c in changes]
        assert "confidence_drop" in types

    def test_company_sentiment_shift_detected(self):
        prev = make_company_opp(sentiment=0.80)
        curr = make_company_opp(sentiment=-0.10)
        changes = ChangeDetector().detect_company_changes(prev, curr)
        types = [c.change_type for c in changes]
        assert "sentiment_shift" in types

    def test_change_event_has_to_dict(self):
        prev = make_market_opp(regime=MarketRegime.BULL)
        curr = make_market_opp(regime=MarketRegime.BEAR)
        changes = ChangeDetector().detect_market_changes(prev, curr)
        assert len(changes) > 0
        d = changes[0].to_dict()
        assert "change_type" in d


class TestAlertRegistry:
    def test_add_and_count(self):
        reg   = AlertRegistry()
        alert = StrategyAlert.create(
            AlertType.REGIME_SHIFT, AlertSeverity.MAJOR,
            "s1", "o1", "Test", "Test alert",
        )
        reg.add(alert)
        assert reg.count() == 1

    def test_for_opportunity(self):
        reg = AlertRegistry()
        a1  = StrategyAlert.create(AlertType.REGIME_SHIFT, AlertSeverity.MAJOR, "s1", "o1", "T", "D")
        a2  = StrategyAlert.create(AlertType.REGIME_SHIFT, AlertSeverity.MAJOR, "s1", "o2", "T", "D")
        reg.add(a1)
        reg.add(a2)
        assert len(reg.for_opportunity("o1")) == 1

    def test_critical_filters(self):
        reg = AlertRegistry()
        reg.add(StrategyAlert.create(AlertType.REGIME_SHIFT, AlertSeverity.CRITICAL, "s1", "o1", "T", "D"))
        reg.add(StrategyAlert.create(AlertType.REGIME_SHIFT, AlertSeverity.WARNING,  "s1", "o2", "T", "D"))
        assert len(reg.critical()) == 1

    def test_action_required_filters(self):
        reg = AlertRegistry()
        reg.add(StrategyAlert.create(AlertType.REGIME_SHIFT, AlertSeverity.MAJOR, "s1", "o1", "T", "D", action_required=True))
        reg.add(StrategyAlert.create(AlertType.REGIME_SHIFT, AlertSeverity.MAJOR, "s1", "o2", "T", "D", action_required=False))
        assert len(reg.action_required()) == 1


class TestPriorityMonitor:
    def test_register_and_record(self):
        reg = AlertRegistry()
        pm  = PriorityMonitor(reg)
        opp = _active_opp()
        pm.register(opp)
        assert "o1" in pm.monitored_ids()

    def test_no_alert_for_stable_score(self):
        reg = AlertRegistry()
        pm  = PriorityMonitor(reg)
        opp = _active_opp()
        pm.register(opp)
        # Same scores → no degradation
        alerts = pm.check(opp)
        assert alerts == []

    def test_major_degradation_triggers_alert(self):
        reg = AlertRegistry()
        pm  = PriorityMonitor(reg)
        opp = _active_opp()
        pm.register(opp)
        # Simulate major score drop
        opp.matching_score    = 20.0
        opp.suitability_score = 20.0
        opp.ranking_score     = 20.0
        alerts = pm.check(opp)
        assert len(alerts) > 0
        assert any(a.severity in (AlertSeverity.MAJOR, AlertSeverity.CRITICAL) for a in alerts)


class TestOpportunityMonitor:
    def test_update_market_no_initial_change(self):
        monitor = OpportunityMonitor()
        opp     = make_market_opp()
        # First update has no previous snapshot → no changes
        changes = monitor.update_market(opp)
        assert changes == []

    def test_update_market_detects_changes(self):
        monitor = OpportunityMonitor()
        prev    = make_market_opp(regime=MarketRegime.BULL)
        curr    = make_market_opp(regime=MarketRegime.BEAR)
        monitor.update_market(prev)
        changes = monitor.update_market(curr)
        assert len(changes) > 0

    def test_check_expiring_raises_alert(self):
        monitor = OpportunityMonitor()
        opp     = _active_opp()
        opp.expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        alerts  = monitor.check_expiring([opp], warn_minutes=30)
        assert len(alerts) == 1

    def test_check_expiring_future_ok(self):
        monitor = OpportunityMonitor()
        opp     = _active_opp()
        opp.expires_at = datetime.now(timezone.utc) + timedelta(hours=5)
        alerts  = monitor.check_expiring([opp], warn_minutes=30)
        assert len(alerts) == 0

    def test_alert_callback_invoked(self):
        monitor = OpportunityMonitor()
        received = []
        monitor.subscribe_alerts(received.append)
        prev = make_market_opp(regime=MarketRegime.BULL)
        curr = make_market_opp(regime=MarketRegime.BEAR)
        monitor.update_market(prev)
        monitor.update_market(curr)
        assert len(received) > 0
