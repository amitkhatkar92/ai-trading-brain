"""iios/investment/market/breadth/breadth_classifier.py
Classifies the current breadth regime from BreadthData and participation.
"""
from __future__ import annotations

from iios.investment.market.breadth.models import (
    BreadthData,
    BreadthRegimeSnapshot,
    BreadthRegimeType,
    MarketHealthSnapshot,
    ParticipationSnapshot,
)
from iios.investment.market.breadth.breadth_regime import build_regime_snapshot


# ── Thresholds ────────────────────────────────────────────────────────────────

_STRONG_PCT   = 0.65
_HEALTHY_PCT  = 0.55
_NEUTRAL_LO   = 0.40
_NEUTRAL_HI   = 0.55
_WEAK_PCT     = 0.30
_BROAD_RALLY_PCT    = 0.70
_BROAD_RALLY_SECT   = 0.60
_BROAD_SELLOFF_PCT  = 0.30
_BROAD_SELLOFF_SECT = 0.40


class BreadthClassifier:
    def classify(
        self,
        breadth: BreadthData,
        participation: ParticipationSnapshot,
        health: MarketHealthSnapshot,
        previous_regime: BreadthRegimeType | None,
        duration_bars: int,
    ) -> BreadthRegimeSnapshot:
        regime = self._choose_regime(breadth, participation, health)
        confidence = self._regime_confidence(breadth, participation, regime)
        transition_prob = self._transition_prob(breadth, regime, duration_bars)
        regime_score = self._regime_score(breadth, regime)

        return build_regime_snapshot(
            regime=regime,
            confidence=confidence,
            duration_bars=duration_bars,
            previous_regime=previous_regime,
            transition_probability=transition_prob,
            regime_score=regime_score,
        )

    # ── Regime selection ──────────────────────────────────────────────────

    def _choose_regime(
        self,
        breadth: BreadthData,
        participation: ParticipationSnapshot,
        health: MarketHealthSnapshot,
    ) -> BreadthRegimeType:
        pct  = breadth.breadth_pct
        sect = participation.participation_breadth

        # Broad rally: overwhelming majority advancing
        if pct >= _BROAD_RALLY_PCT and sect >= _BROAD_RALLY_SECT:
            return BreadthRegimeType.BROAD_RALLY

        # Broad selloff: overwhelming majority declining
        if pct <= _BROAD_SELLOFF_PCT and sect <= _BROAD_SELLOFF_SECT:
            return BreadthRegimeType.BROAD_SELLOFF

        # Strong participation
        if pct >= _STRONG_PCT:
            return BreadthRegimeType.STRONG_PARTICIPATION

        # Narrow rally: breadth below 55% but positive momentum / health
        if _NEUTRAL_HI < pct < _STRONG_PCT and sect < 0.45:
            return BreadthRegimeType.NARROW_RALLY

        # Healthy participation
        if pct >= _HEALTHY_PCT:
            return BreadthRegimeType.HEALTHY_PARTICIPATION

        # Neutral zone
        if _NEUTRAL_LO <= pct < _HEALTHY_PCT:
            return BreadthRegimeType.NEUTRAL

        # Narrow selloff: moderate decline but limited sector breadth
        if _WEAK_PCT <= pct < _NEUTRAL_LO and sect > 0.45:
            return BreadthRegimeType.NARROW_SELLOFF

        # Weak participation
        if pct >= _WEAK_PCT:
            return BreadthRegimeType.WEAK_PARTICIPATION

        # Very weak
        return BreadthRegimeType.VERY_WEAK_PARTICIPATION

    # ── Confidence ────────────────────────────────────────────────────────

    def _regime_confidence(
        self,
        breadth: BreadthData,
        participation: ParticipationSnapshot,
        regime: BreadthRegimeType,
    ) -> float:
        stability_part = breadth.breadth_stability * 0.50
        sector_part    = participation.participation_breadth * 0.30
        ma_part        = participation.above_ma20_pct * 0.20
        base = stability_part + sector_part + ma_part
        return max(0.10, min(0.99, base))

    # ── Transition probability ─────────────────────────────────────────────

    def _transition_prob(
        self,
        breadth: BreadthData,
        regime: BreadthRegimeType,
        duration_bars: int,
    ) -> float:
        base = 0.10
        instability = 1.0 - breadth.breadth_stability
        # Longer duration → lower transition probability
        duration_discount = min(0.10, duration_bars * 0.005)
        prob = base + instability * 0.30 - duration_discount
        return max(0.01, min(0.70, prob))

    # ── Regime score ──────────────────────────────────────────────────────

    def _regime_score(self, breadth: BreadthData, regime: BreadthRegimeType) -> float:
        """Position of breadth_pct within the regime band, 0-100."""
        bands: dict[BreadthRegimeType, tuple[float, float]] = {
            BreadthRegimeType.VERY_WEAK_PARTICIPATION: (0.0, _WEAK_PCT),
            BreadthRegimeType.WEAK_PARTICIPATION:       (_WEAK_PCT, _NEUTRAL_LO),
            BreadthRegimeType.NEUTRAL:                  (_NEUTRAL_LO, _HEALTHY_PCT),
            BreadthRegimeType.HEALTHY_PARTICIPATION:    (_HEALTHY_PCT, _STRONG_PCT),
            BreadthRegimeType.STRONG_PARTICIPATION:     (_STRONG_PCT, _BROAD_RALLY_PCT),
            BreadthRegimeType.BROAD_RALLY:              (_BROAD_RALLY_PCT, 1.0),
            BreadthRegimeType.BROAD_SELLOFF:            (0.0, _BROAD_SELLOFF_PCT),
        }
        band = bands.get(regime)
        if band is None:
            return 50.0
        lo, hi = band
        span = hi - lo
        if span < 1e-10:
            return 50.0
        pos = (breadth.breadth_pct - lo) / span
        return max(0.0, min(100.0, pos * 100))
