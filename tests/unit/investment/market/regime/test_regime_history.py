"""tests/unit/investment/market/regime/test_regime_history.py"""
from __future__ import annotations

import pytest

from iios.investment.market.market_constants import MarketRegime
from iios.investment.market.regime.regime_history import RegimeHistory
from iios.investment.market.regime.regime_transition import RegimeTransition


def make_transition(
    market_id: str = "M1",
    from_r: MarketRegime = MarketRegime.UNKNOWN,
    to_r: MarketRegime = MarketRegime.BULL,
) -> RegimeTransition:
    return RegimeTransition(
        market_id=market_id,
        from_regime=from_r,
        to_regime=to_r,
        confidence=0.8,
        trigger="test",
    )


class TestRecord:
    def test_record_adds_to_store(self):
        h = RegimeHistory()
        t = make_transition()
        h.record(t)
        assert h.count() == 1

    def test_record_is_idempotent(self):
        h = RegimeHistory()
        t = make_transition()
        h.record(t)
        h.record(t)  # same transition_id
        assert h.count() == 1

    def test_record_multiple(self):
        h = RegimeHistory()
        for _ in range(5):
            h.record(make_transition())
        assert h.count() == 5


class TestForMarket:
    def test_for_market_filters_correctly(self):
        h = RegimeHistory()
        h.record(make_transition("M1"))
        h.record(make_transition("M2"))
        h.record(make_transition("M1"))
        result = h.for_market("M1")
        assert len(result) == 2
        assert all(t.market_id == "M1" for t in result)

    def test_for_market_empty_when_no_match(self):
        h = RegimeHistory()
        h.record(make_transition("M1"))
        assert h.for_market("M99") == []


class TestLastForMarket:
    def test_last_for_market_returns_most_recent(self):
        h = RegimeHistory()
        t1 = make_transition("M1", to_r=MarketRegime.BULL)
        t2 = make_transition("M1", to_r=MarketRegime.BEAR)
        h.record(t1)
        h.record(t2)
        last = h.last_for_market("M1")
        assert last is not None
        assert last.to_regime == MarketRegime.BEAR

    def test_last_for_market_none_when_no_market(self):
        h = RegimeHistory()
        assert h.last_for_market("MISSING") is None


class TestRecent:
    def test_recent_respects_n(self):
        h = RegimeHistory()
        for _ in range(10):
            h.record(make_transition())
        result = h.recent(n=3)
        assert len(result) == 3

    def test_recent_returns_all_when_fewer_than_n(self):
        h = RegimeHistory()
        h.record(make_transition())
        h.record(make_transition())
        result = h.recent(n=10)
        assert len(result) == 2


class TestCount:
    def test_count_tracks_correctly(self):
        h = RegimeHistory()
        assert h.count() == 0
        h.record(make_transition())
        assert h.count() == 1
        h.record(make_transition())
        assert h.count() == 2
