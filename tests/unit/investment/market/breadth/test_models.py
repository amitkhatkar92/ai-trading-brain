"""test_models.py — unit tests for all breadth models."""
from __future__ import annotations

import time

import pytest

from iios.investment.market.breadth.models import (
    BreadthConfidenceScore,
    BreadthData,
    BreadthEvent,
    BreadthEventType,
    BreadthIntelligenceSnapshot,
    BreadthMetricValue,
    BreadthRegimeSnapshot,
    BreadthRegimeType,
    BreadthTrend,
    DivergenceSignal,
    DivergenceType,
    HealthTrend,
    MarketCapTier,
    MarketHealthSnapshot,
    ParticipationSnapshot,
    SecurityObservation,
    UniverseSnapshot,
)


# ── SecurityObservation ───────────────────────────────────────────────────

class TestSecurityObservation:
    def test_is_advancing_positive(self):
        obs = SecurityObservation("AAPL", price_change_pct=0.5)
        assert obs.is_advancing is True
        assert obs.is_declining is False
        assert obs.is_unchanged is False

    def test_is_declining_negative(self):
        obs = SecurityObservation("MSFT", price_change_pct=-1.0)
        assert obs.is_advancing is False
        assert obs.is_declining is True

    def test_is_unchanged_zero(self):
        obs = SecurityObservation("GOOG", price_change_pct=0.0)
        assert obs.is_unchanged is True
        assert obs.is_advancing is False
        assert obs.is_declining is False

    def test_default_fields(self):
        obs = SecurityObservation("X", 0.1)
        assert obs.sector == "unknown"
        assert obs.market_cap_tier == "unknown"
        assert obs.volume_ratio == 1.0
        assert obs.is_above_ma20 is False


# ── UniverseSnapshot ──────────────────────────────────────────────────────

class TestUniverseSnapshot:
    def _make(self, n_adv: int, n_dec: int, n_unc: int = 0) -> UniverseSnapshot:
        obs = (
            [SecurityObservation(f"A{i}", 0.5) for i in range(n_adv)]
            + [SecurityObservation(f"D{i}", -0.5) for i in range(n_dec)]
            + [SecurityObservation(f"U{i}", 0.0) for i in range(n_unc)]
        )
        return UniverseSnapshot("TEST", 0, time.time(), obs)

    def test_total(self):
        u = self._make(60, 30, 10)
        assert u.total == 100

    def test_advancing(self):
        u = self._make(60, 30, 10)
        assert len(u.advancing()) == 60

    def test_declining(self):
        u = self._make(60, 30, 10)
        assert len(u.declining()) == 30

    def test_unchanged(self):
        u = self._make(60, 30, 10)
        assert len(u.unchanged()) == 10

    def test_by_sector(self):
        obs = [
            SecurityObservation("A", 0.5, sector="Tech"),
            SecurityObservation("B", -0.5, sector="Finance"),
            SecurityObservation("C", 0.3, sector="Tech"),
        ]
        u = UniverseSnapshot("TEST", 0, time.time(), obs)
        by_sec = u.by_sector()
        assert "Tech" in by_sec
        assert len(by_sec["Tech"]) == 2

    def test_by_cap_tier(self):
        obs = [
            SecurityObservation("A", 0.5, market_cap_tier="large"),
            SecurityObservation("B", -0.5, market_cap_tier="small"),
        ]
        u = UniverseSnapshot("TEST", 0, time.time(), obs)
        by_tier = u.by_cap_tier()
        assert "large" in by_tier
        assert "small" in by_tier

    def test_empty_universe(self):
        u = UniverseSnapshot("EMPTY", 0, time.time(), [])
        assert u.total == 0
        assert len(u.advancing()) == 0


# ── BreadthData ───────────────────────────────────────────────────────────

class TestBreadthData:
    def test_construction(self):
        bd = BreadthData(
            advancing=70,
            declining=20,
            unchanged=10,
            total=100,
            breadth_pct=0.70,
            ad_ratio=3.5,
            ad_line=50.0,
            ad_momentum=0.0,
            breadth_trend=BreadthTrend.RISING,
            breadth_stability=0.8,
            metric_values={},
        )
        assert bd.breadth_pct == 0.70
        assert bd.ad_ratio == 3.5


# ── ParticipationSnapshot ─────────────────────────────────────────────────

class TestParticipationSnapshot:
    def test_construction(self):
        ps = ParticipationSnapshot(
            large_cap_pct=0.70,
            mid_cap_pct=0.60,
            small_cap_pct=0.50,
            sector_participation={"Tech": 0.80, "Finance": 0.60},
            above_ma20_pct=0.65,
            above_ma50_pct=0.55,
            new_highs=20,
            new_lows=5,
            nh_nl_ratio=4.0,
            market_participation_score=72.0,
            participation_breadth=0.80,
        )
        assert ps.participation_breadth == 0.80
        assert ps.nh_nl_ratio == 4.0


# ── MarketCapTier ─────────────────────────────────────────────────────────

class TestMarketCapTier:
    def test_values(self):
        assert MarketCapTier.LARGE.value == "large"
        assert MarketCapTier.MID.value == "mid"
        assert MarketCapTier.SMALL.value == "small"
        assert MarketCapTier.MICRO.value == "micro"


# ── BreadthRegimeType ─────────────────────────────────────────────────────

class TestBreadthRegimeType:
    def test_all_regimes_exist(self):
        expected = {
            "STRONG_PARTICIPATION", "HEALTHY_PARTICIPATION", "NEUTRAL",
            "WEAK_PARTICIPATION", "VERY_WEAK_PARTICIPATION",
            "BROAD_RALLY", "NARROW_RALLY", "BROAD_SELLOFF",
            "NARROW_SELLOFF", "UNKNOWN",
        }
        actual = {r.name for r in BreadthRegimeType}
        assert expected == actual


# ── BreadthEvent ──────────────────────────────────────────────────────────

class TestBreadthEvent:
    def test_default_optional_fields(self):
        ev = BreadthEvent(
            event_type=BreadthEventType.REGIME_CHANGE,
            universe_id="TEST",
            bar_index=5,
            severity=0.7,
            description="test",
        )
        assert ev.from_regime is None
        assert ev.to_regime is None

    def test_with_regime_transition(self):
        ev = BreadthEvent(
            event_type=BreadthEventType.REGIME_CHANGE,
            universe_id="TEST",
            bar_index=5,
            severity=0.5,
            from_regime=BreadthRegimeType.NEUTRAL,
            to_regime=BreadthRegimeType.BROAD_RALLY,
            description="transition",
        )
        assert ev.from_regime == BreadthRegimeType.NEUTRAL
        assert ev.to_regime == BreadthRegimeType.BROAD_RALLY


# ── DivergenceSignal ──────────────────────────────────────────────────────

class TestDivergenceSignal:
    def test_confirmed_flag(self):
        sig = DivergenceSignal(
            divergence_type=DivergenceType.BULLISH_BREADTH,
            strength=0.8,
            bars_active=5,
            description="test",
            confirmed=True,
        )
        assert sig.confirmed is True


# ── BreadthIntelligenceSnapshot ───────────────────────────────────────────

class TestBreadthIntelligenceSnapshot:
    def _make_snap(self) -> BreadthIntelligenceSnapshot:
        bd = BreadthData(
            advancing=70, declining=20, unchanged=10, total=100,
            breadth_pct=0.70, ad_ratio=3.5, ad_line=50.0,
            ad_momentum=0.05, breadth_trend=BreadthTrend.RISING,
            breadth_stability=0.8, metric_values={},
        )
        ps = ParticipationSnapshot(
            large_cap_pct=0.70, mid_cap_pct=0.60, small_cap_pct=0.50,
            sector_participation={}, above_ma20_pct=0.65, above_ma50_pct=0.55,
            new_highs=20, new_lows=5, nh_nl_ratio=4.0,
            market_participation_score=72.0, participation_breadth=0.80,
        )
        mh = MarketHealthSnapshot(
            health_score=75.0, internal_strength=0.75, leadership_breadth=0.6,
            lagging_breadth=0.4, participation_quality=0.7, internal_momentum=0.1,
            health_trend=HealthTrend.IMPROVING, leading_sectors=[], lagging_sectors=[],
        )
        rs = BreadthRegimeSnapshot(
            regime=BreadthRegimeType.BROAD_RALLY, confidence=0.85,
            duration_bars=5, previous_regime=None, transition_probability=0.1,
            regime_score=80.0,
        )
        conf = BreadthConfidenceScore(
            breadth_confidence=0.85, participation_confidence=0.80,
            leadership_confidence=0.75, internal_strength_score=75.0, overall_score=80.0,
        )
        return BreadthIntelligenceSnapshot(
            snapshot_id="abc", universe_id="TEST", bar_index=10,
            timestamp=time.time(), breadth_data=bd, participation=ps,
            market_health=mh, regime_snapshot=rs, active_divergences=[],
            confidence=conf, active_events=[], last_event=None,
        )

    def test_construction(self):
        snap = self._make_snap()
        assert snap.universe_id == "TEST"
        assert snap.bar_index == 10

    def test_to_dict(self):
        snap = self._make_snap()
        d = snap.to_dict()
        assert isinstance(d, dict)
        assert "snapshot_id" in d
        assert "regime" in d
        assert "breadth_data" in d
