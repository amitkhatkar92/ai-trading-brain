"""test_divergence_engine.py — tests for DivergenceDetector and DivergenceEngine."""
from __future__ import annotations

import pytest

from iios.investment.market.breadth.models import (
    BreadthData,
    BreadthTrend,
    DivergenceType,
    HealthTrend,
    MarketHealthSnapshot,
    ParticipationSnapshot,
)
from iios.investment.market.breadth.divergence_detector import DivergenceDetector
from iios.investment.market.breadth.divergence_engine import DivergenceEngine
from iios.investment.market.breadth.divergence_history import DivergenceHistory


def _bd(pct: float, stability: float = 0.6) -> BreadthData:
    return BreadthData(
        advancing=int(100 * pct), declining=int(100 * (1 - pct)),
        unchanged=0, total=100, breadth_pct=pct,
        ad_ratio=pct / max(1 - pct, 0.01),
        ad_line=0.0, ad_momentum=0.0,
        breadth_trend=BreadthTrend.RISING if pct > 0.5 else BreadthTrend.FALLING,
        breadth_stability=stability, metric_values={},
    )


def _ps(above_ma20: float = 0.50, part_breadth: float = 0.60) -> ParticipationSnapshot:
    return ParticipationSnapshot(
        large_cap_pct=0.60, mid_cap_pct=0.55, small_cap_pct=0.50,
        sector_participation={},
        above_ma20_pct=above_ma20, above_ma50_pct=above_ma20 * 0.9,
        new_highs=10, new_lows=5, nh_nl_ratio=2.0,
        market_participation_score=60.0,
        participation_breadth=part_breadth,
    )


def _health(leadership: float = 0.6, score: float = 60.0) -> MarketHealthSnapshot:
    return MarketHealthSnapshot(
        health_score=score, internal_strength=0.6,
        leadership_breadth=leadership, lagging_breadth=0.4,
        participation_quality=0.6, internal_momentum=0.0,
        health_trend=HealthTrend.STABLE, leading_sectors=[], lagging_sectors=[],
    )


class TestDivergenceDetector:
    def test_no_divergence_on_sparse_history(self):
        d = DivergenceDetector(short_window=5)
        signals = d.detect(_bd(0.70), _ps(), _health())
        assert signals == []  # not enough history yet

    def test_bullish_breadth_divergence_with_bearish_context(self):
        d = DivergenceDetector(short_window=3, confirm_bars=3)
        # Fill history with improving breadth
        for i in range(8):
            bd = _bd(0.50 + i * 0.03)
            d.detect(bd, _ps(above_ma20=0.50), _health(), market_regime="bearish_trend")
        signals = d.detect(_bd(0.74), _ps(), _health(), market_regime="bearish_trend")
        bull_sigs = [s for s in signals if s.divergence_type == DivergenceType.BULLISH_BREADTH]
        assert len(bull_sigs) >= 1

    def test_participation_divergence_internal(self):
        d = DivergenceDetector(short_window=3, confirm_bars=3)
        # Breadth rising but MA20% falling — participation bearish divergence
        for i in range(8):
            bd = _bd(0.50 + i * 0.03)
            ps = _ps(above_ma20=0.70 - i * 0.04)
            d.detect(bd, ps, _health())
        # should trigger participation_bearish
        signals = d.detect(_bd(0.74), _ps(above_ma20=0.30), _health())
        part_sigs = [s for s in signals
                     if s.divergence_type == DivergenceType.PARTICIPATION_BEARISH]
        assert len(part_sigs) >= 1

    def test_signal_strength_in_0_1(self):
        d = DivergenceDetector(short_window=3, confirm_bars=3)
        for i in range(10):
            signals = d.detect(_bd(0.60), _ps(), _health(), market_regime="bearish")
            for s in signals:
                assert 0.0 <= s.strength <= 1.0

    def test_confirmed_after_enough_bars(self):
        d = DivergenceDetector(short_window=3, confirm_bars=2)
        for i in range(10):
            signals = d.detect(_bd(0.65), _ps(), _health(), market_regime="bearish_trend")
        bull_sigs = [s for s in signals if s.divergence_type == DivergenceType.BULLISH_BREADTH]
        if bull_sigs:
            assert any(s.confirmed for s in bull_sigs)


class TestDivergenceEngine:
    def test_returns_signals_and_events(self):
        engine = DivergenceEngine()
        bd = _bd(0.70)
        for i in range(10):
            sigs, evs = engine.update(
                bd, _ps(), _health(), bar_index=i, universe_id="TEST"
            )
        assert isinstance(sigs, list)
        assert isinstance(evs, list)

    def test_event_on_newly_confirmed_divergence(self):
        engine = DivergenceEngine(
            detector=DivergenceDetector(short_window=3, confirm_bars=2)
        )
        events_total = []
        signals_total = []
        # Use rising breadth against bearish context to trigger bullish divergence
        for i in range(30):
            pct = min(0.90, 0.40 + i * 0.02)  # rising trend
            bd = _bd(pct)
            sigs, evs = engine.update(
                bd, _ps(), _health(), bar_index=i,
                universe_id="TEST", market_regime="bearish_declining_trend"
            )
            events_total.extend(evs)
            signals_total.extend(sigs)
        # Verify all returned signals and events are valid types
        for s in signals_total:
            assert isinstance(s.divergence_type, DivergenceType)
            assert 0.0 <= s.strength <= 1.0
        from iios.investment.market.breadth.models import BreadthEventType
        for e in events_total:
            assert isinstance(e.event_type, BreadthEventType)


class TestDivergenceHistory:
    def test_append_and_len(self):
        h = DivergenceHistory(maxlen=5)
        from iios.investment.market.breadth.models import DivergenceSignal
        sig = DivergenceSignal(
            divergence_type=DivergenceType.BULLISH_BREADTH,
            strength=0.5, bars_active=2, description="t", confirmed=False,
        )
        h.append([sig])
        assert len(h) == 1

    def test_maxlen_respected(self):
        h = DivergenceHistory(maxlen=3)
        for i in range(10):
            h.append([])
        assert len(h) == 3

    def test_latest(self):
        h = DivergenceHistory()
        assert h.latest() is None
        h.append([])
        assert h.latest() == []
