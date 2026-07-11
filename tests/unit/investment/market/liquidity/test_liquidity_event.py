"""tests/unit/investment/market/liquidity/test_liquidity_event.py"""
from __future__ import annotations

import pytest

from iios.investment.market.liquidity.models import (
    LiquidityEventType, VolumeTrend, EffortResultType, EffortResultAnalysis,
    ParticipationSnapshot, ParticipationBias, VolumeProfile,
)
from iios.investment.market.liquidity.liquidity_event import LiquidityEventDetector
from iios.investment.market.liquidity.liquidity_transition import (
    LiquidityTransitionType, LiquidityTransitionDetector, LiquidityTransition,
)
from iios.investment.market.liquidity.liquidity_alerts import (
    AlertSeverity, LiquidityAlertGenerator,
)
from iios.investment.market.liquidity.models import LiquidityEvent, LiquidityProfile

from tests.unit.investment.market.liquidity.conftest import make_volume_bar


def _make_participation(score: float = 50.0) -> ParticipationSnapshot:
    return ParticipationSnapshot(
        buying_participation=0.5, selling_participation=0.5,
        institutional_participation=0.4, retail_participation=0.6,
        participation_balance=0.0, participation_bias=ParticipationBias.NEUTRAL,
        participation_confidence=0.7, participation_score=score,
    )


def _make_er(er_type: EffortResultType, initiative_buying=False, initiative_selling=False,
             is_absorption=False, absorption_strength=0.0) -> EffortResultAnalysis:
    is_climax = er_type == EffortResultType.CLIMAX
    is_divergent = er_type == EffortResultType.DIVERGENT
    is_abs = is_absorption or er_type == EffortResultType.ABSORPTION
    return EffortResultAnalysis(
        effort=0.7, result=0.3, ratio=0.43,
        effort_result_type=er_type,
        is_confirmed=False, is_divergent=is_divergent,
        is_absorption=is_abs, is_climax=is_climax,
        absorption_strength=absorption_strength,
        climax_score=0.9 if is_climax else 0.0,
        initiative_buying=initiative_buying,
        initiative_selling=initiative_selling,
        responsive_buying=False, responsive_selling=False,
    )


def _make_volume_profile(trend: VolumeTrend = VolumeTrend.STABLE) -> VolumeProfile:
    return VolumeProfile(
        period_bars=20, avg_volume=100_000.0, std_volume=5000.0,
        median_volume=100_000.0, peak_volume=200_000.0, min_volume=50_000.0,
        recent_avg=100_000.0, volume_trend=trend,
        up_volume=1_000_000.0, down_volume=1_000_000.0, up_down_ratio=1.0,
    )


class TestLiquidityEventDetector:
    def setup_method(self):
        self.detector = LiquidityEventDetector()

    def test_volume_spike_detected(self):
        vbar = make_volume_bar(relative_volume=3.0, volume=300_000.0)
        events = self.detector.detect(
            vbar, _make_volume_profile(), _make_participation(),
            _make_er(EffortResultType.NEUTRAL), "TEST", "1d",
        )
        types = [e.event_type for e in events]
        assert LiquidityEventType.VOLUME_SPIKE in types

    def test_volume_vacuum_detected(self):
        vbar = make_volume_bar(relative_volume=0.1, volume=10_000.0)
        events = self.detector.detect(
            vbar, _make_volume_profile(), _make_participation(),
            _make_er(EffortResultType.NEUTRAL), "TEST", "1d",
        )
        types = [e.event_type for e in events]
        assert LiquidityEventType.VOLUME_VACUUM in types

    def test_high_participation_detected(self):
        vbar = make_volume_bar()
        events = self.detector.detect(
            vbar, _make_volume_profile(), _make_participation(score=85.0),
            _make_er(EffortResultType.NEUTRAL), "TEST", "1d",
        )
        types = [e.event_type for e in events]
        assert LiquidityEventType.HIGH_PARTICIPATION in types

    def test_buying_climax_detected(self):
        vbar = make_volume_bar()
        events = self.detector.detect(
            vbar, _make_volume_profile(),
            _make_participation(),
            _make_er(EffortResultType.CLIMAX, initiative_buying=True),
            "TEST", "1d",
        )
        types = [e.event_type for e in events]
        assert LiquidityEventType.BUYING_CLIMAX in types

    def test_selling_climax_detected(self):
        vbar = make_volume_bar()
        events = self.detector.detect(
            vbar, _make_volume_profile(),
            _make_participation(),
            _make_er(EffortResultType.CLIMAX, initiative_selling=True),
            "TEST", "1d",
        )
        types = [e.event_type for e in events]
        assert LiquidityEventType.SELLING_CLIMAX in types

    def test_absorption_detected(self):
        vbar = make_volume_bar()
        events = self.detector.detect(
            vbar, _make_volume_profile(),
            _make_participation(),
            _make_er(EffortResultType.ABSORPTION, is_absorption=True, absorption_strength=0.7),
            "TEST", "1d",
        )
        types = [e.event_type for e in events]
        assert LiquidityEventType.ABSORPTION_DETECTED in types

    def test_shock_detected(self):
        vbar = make_volume_bar(relative_volume=4.0, price_change_pct=3.0)
        events = self.detector.detect(
            vbar, _make_volume_profile(), _make_participation(),
            _make_er(EffortResultType.NEUTRAL), "TEST", "1d",
        )
        types = [e.event_type for e in events]
        assert LiquidityEventType.SHOCK in types

    def test_normal_bar_no_events(self):
        vbar = make_volume_bar(relative_volume=1.0, price_change_pct=0.5)
        events = self.detector.detect(
            vbar, _make_volume_profile(), _make_participation(score=50.0),
            _make_er(EffortResultType.NEUTRAL), "TEST", "1d",
        )
        assert len(events) == 0

    def test_severity_correct_shock(self):
        vbar = make_volume_bar(relative_volume=4.0, price_change_pct=3.0)
        events = self.detector.detect(
            vbar, _make_volume_profile(), _make_participation(),
            _make_er(EffortResultType.NEUTRAL), "TEST", "1d",
        )
        shock = next(e for e in events if e.event_type == LiquidityEventType.SHOCK)
        assert shock.severity == 1.0

    def test_multiple_events_possible(self):
        # spike + high participation
        vbar = make_volume_bar(relative_volume=3.0)
        events = self.detector.detect(
            vbar, _make_volume_profile(), _make_participation(score=85.0),
            _make_er(EffortResultType.NEUTRAL), "TEST", "1d",
        )
        assert len(events) >= 2


class TestLiquidityTransitionDetector:
    def setup_method(self):
        self.detector = LiquidityTransitionDetector(change_threshold=10.0)

    def _profile(self, quality: float) -> LiquidityProfile:
        return LiquidityProfile(
            availability=0.5, stability=0.5, depth=0.5,
            concentration=0.5, fragmentation=0.5,
            quality=quality, liquidity_confidence=0.5,
        )

    def test_first_call_no_transition(self):
        result = self.detector.detect(self._profile(50.0), 0)
        assert result is None

    def test_quality_improves_15_pts(self):
        self.detector.detect(self._profile(40.0), 0)
        result = self.detector.detect(self._profile(55.0), 1)
        assert result is not None
        assert result.transition_type == LiquidityTransitionType.IMPROVING

    def test_quality_drops_15_pts(self):
        self.detector.detect(self._profile(60.0), 0)
        result = self.detector.detect(self._profile(45.0), 1)
        assert result is not None
        assert result.transition_type == LiquidityTransitionType.DEGRADING

    def test_quality_drops_30_pts_shock(self):
        self.detector.detect(self._profile(80.0), 0)
        result = self.detector.detect(self._profile(50.0), 1)
        assert result is not None
        assert result.transition_type == LiquidityTransitionType.SHOCK

    def test_stable_change_no_transition(self):
        self.detector.detect(self._profile(50.0), 0)
        result = self.detector.detect(self._profile(55.0), 1)
        # 5 pt change < 10 threshold
        assert result is None

    def test_recovering_after_shock(self):
        self.detector.detect(self._profile(80.0), 0)
        self.detector.detect(self._profile(50.0), 1)   # SHOCK: -30
        result = self.detector.detect(self._profile(75.0), 2)  # +25 after shock
        assert result is not None
        assert result.transition_type == LiquidityTransitionType.RECOVERING


class TestLiquidityAlertGenerator:
    def setup_method(self):
        self.gen = LiquidityAlertGenerator()

    def _event(self, etype: LiquidityEventType) -> LiquidityEvent:
        return LiquidityEvent(event_type=etype, symbol="TEST")

    def test_shock_is_critical(self):
        alert = self.gen.generate_single(self._event(LiquidityEventType.SHOCK))
        assert alert.severity == AlertSeverity.CRITICAL

    def test_buying_climax_is_critical(self):
        alert = self.gen.generate_single(self._event(LiquidityEventType.BUYING_CLIMAX))
        assert alert.severity == AlertSeverity.CRITICAL

    def test_volume_spike_is_warning(self):
        alert = self.gen.generate_single(self._event(LiquidityEventType.VOLUME_SPIKE))
        assert alert.severity == AlertSeverity.WARNING

    def test_high_participation_is_info(self):
        alert = self.gen.generate_single(self._event(LiquidityEventType.HIGH_PARTICIPATION))
        assert alert.severity == AlertSeverity.INFO

    def test_empty_events_empty_alerts(self):
        alerts = self.gen.generate([])
        assert alerts == []

    def test_generate_multiple(self):
        events = [
            self._event(LiquidityEventType.SHOCK),
            self._event(LiquidityEventType.VOLUME_SPIKE),
        ]
        alerts = self.gen.generate(events)
        assert len(alerts) == 2
