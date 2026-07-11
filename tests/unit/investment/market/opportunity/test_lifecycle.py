"""tests/unit/investment/market/opportunity/test_lifecycle.py"""
from __future__ import annotations

import pytest

from iios.investment.market.opportunity.lifecycle_history import LifecycleHistory
from iios.investment.market.opportunity.lifecycle_tracker import LifecycleTracker
from iios.investment.market.opportunity.models import (
    Opportunity,
    OpportunityCategory,
    OpportunityEventType,
    OpportunityLifecycleStage,
)
from iios.investment.market.opportunity.opportunity_lifecycle import OpportunityLifecycleEngine


def _opp(symbol: str = "X", score: float = 70.0) -> Opportunity:
    o = Opportunity.new(symbol, "IT", "S", OpportunityCategory.TREND_FOLLOWING, 1)
    o.composite_score = score
    return o


class TestLifecycleTracker:
    def test_stays_discovered_at_low_score(self):
        opp     = _opp(score=40.0)
        tracker = LifecycleTracker(opp)
        events  = tracker.advance(2)
        assert opp.lifecycle_stage is OpportunityLifecycleStage.DISCOVERED
        assert events == []

    def test_advances_to_emerging(self):
        opp     = _opp(score=52.0)  # above DISCOVERED→EMERGING threshold 50
        tracker = LifecycleTracker(opp)
        events  = tracker.advance(2)
        assert opp.lifecycle_stage is OpportunityLifecycleStage.EMERGING
        assert any(e.event_type is OpportunityEventType.UPGRADED for e in events)

    def test_advances_through_stages(self):
        opp     = _opp(score=80.0)  # above CONFIRMED threshold 75
        tracker = LifecycleTracker(opp)
        # Each advance call moves one stage at a time
        stages_reached = {opp.lifecycle_stage}
        for bar in range(2, 8):
            events = tracker.advance(bar)
            stages_reached.add(opp.lifecycle_stage)
            if opp.lifecycle_stage is OpportunityLifecycleStage.CONFIRMED:
                break
        assert OpportunityLifecycleStage.CONFIRMED in stages_reached

    def test_decays_to_weakening(self):
        opp     = _opp(score=80.0)
        tracker = LifecycleTracker(opp)
        # Advance to CONFIRMED
        for bar in range(2, 10):
            tracker.advance(bar)
        assert opp.lifecycle_stage is OpportunityLifecycleStage.CONFIRMED
        # Drop score below weakening threshold for 3 bars
        opp.composite_score = 35.0
        events = tracker.advance(10)
        opp.composite_score = 35.0
        events += tracker.advance(11)
        opp.composite_score = 35.0
        events += tracker.advance(12)
        assert opp.lifecycle_stage is OpportunityLifecycleStage.WEAKENING
        assert any(e.event_type is OpportunityEventType.WEAKENING for e in events)

    def test_expires_at_very_low_score(self):
        """Non-DISCOVERED opportunity with score ≤ 25 expires immediately."""
        opp     = _opp(score=80.0)
        tracker = LifecycleTracker(opp)
        # First advance to EMERGING
        tracker.advance(2)
        assert opp.lifecycle_stage is OpportunityLifecycleStage.EMERGING
        # Now drop to expiry threshold
        opp.composite_score = 20.0
        events  = tracker.advance(3)
        assert opp.lifecycle_stage is OpportunityLifecycleStage.EXPIRED
        assert any(e.event_type is OpportunityEventType.EXPIRED for e in events)

    def test_stage_duration_increments(self):
        opp     = _opp(score=70.0)
        tracker = LifecycleTracker(opp)
        initial = opp.stage_duration_bars
        tracker.advance(2)
        assert opp.stage_duration_bars >= initial


class TestLifecycleHistory:
    def test_empty(self):
        hist = LifecycleHistory()
        assert hist.for_symbol("X") == []
        assert hist.confirmations() == []

    def test_append_and_retrieve(self):
        from iios.investment.market.opportunity.models import OpportunityEvent
        hist  = LifecycleHistory()
        opp   = _opp("AAPL")
        event = OpportunityEvent(
            opportunity_id=opp.opportunity_id,
            event_type=OpportunityEventType.UPGRADED,
            bar_index=2, symbol="AAPL",
            description="AAPL: discovered → emerging",
        )
        hist.append(event)
        assert len(hist.for_symbol("AAPL")) == 1

    def test_confirmations_filter(self):
        from iios.investment.market.opportunity.models import OpportunityEvent
        hist = LifecycleHistory()
        opp  = _opp()
        for et in (OpportunityEventType.UPGRADED, OpportunityEventType.CONFIRMED):
            ev = OpportunityEvent(
                opportunity_id=opp.opportunity_id,
                event_type=et,
                bar_index=5, symbol="X",
                description="test event",
            )
            hist.append(ev)
        confs = hist.confirmations()
        assert len(confs) >= 1

    def test_maxlen_respected(self):
        from iios.investment.market.opportunity.models import OpportunityEvent
        hist = LifecycleHistory(maxlen=3)
        opp  = _opp()
        for i in range(5):
            ev = OpportunityEvent(
                opportunity_id=opp.opportunity_id,
                event_type=OpportunityEventType.UPGRADED,
                bar_index=i, symbol="X",
                description="test",
            )
            hist.append(ev)
        assert len(hist) <= 3


class TestOpportunityLifecycleEngine:
    def test_returns_active_and_events(self):
        engine = OpportunityLifecycleEngine()
        opps   = [_opp("A", 75.0), _opp("B", 30.0)]
        active, events = engine.update(opps, bar_index=2)
        assert isinstance(active, list)
        assert isinstance(events, list)

    def test_expired_removed_from_active(self):
        """Opportunity that reaches EXPIRED stage is excluded from active list."""
        engine = OpportunityLifecycleEngine()
        opp    = _opp("DYING", 80.0)
        # Advance to EMERGING first
        active, _ = engine.update([opp], bar_index=2)
        assert opp.lifecycle_stage is OpportunityLifecycleStage.EMERGING
        # Now score collapses below expiry threshold
        opp.composite_score = 15.0
        active, events = engine.update([opp], bar_index=3)
        active_symbols = [o.symbol for o in active]
        assert "DYING" not in active_symbols

    def test_advances_across_bars(self):
        engine = OpportunityLifecycleEngine()
        opp    = _opp("STAR", 80.0)
        stages = {opp.lifecycle_stage}
        for bar in range(2, 10):
            opps_list = [opp]
            active, _ = engine.update(opps_list, bar_index=bar)
            if active:
                stages.add(active[0].lifecycle_stage)
        assert len(stages) > 1
