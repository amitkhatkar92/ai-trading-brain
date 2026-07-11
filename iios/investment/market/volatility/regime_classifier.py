"""iios/investment/market/volatility/regime_classifier.py
Classifies the current volatility regime from VolatilityState and behaviour.

Regime boundaries are expressed in terms of normalized_volatility (0-1
percentile rank) and relative_volatility (short/medium ratio).  Ordering
of checks matters: special regimes (SHOCK, RECOVERY, EXPANSION, COMPRESSION)
are tested before the tier-based regimes.
"""
from __future__ import annotations

from iios.investment.market.volatility.models import (
    VolatilityBehaviour,
    VolatilityRegimeSnapshot,
    VolatilityRegimeType,
    VolatilityState,
    VolatilityTransitionType,
)
from iios.investment.market.volatility.volatility_regime import (
    build_regime_snapshot,
    infer_transition_type,
)


# ── Thresholds (tunable at module level) ─────────────────────────────────────

_SHOCK_THRESHOLD     = 0.93
_EXTREME_THRESHOLD   = 0.85
_HIGH_THRESHOLD      = 0.70
_ELEVATED_THRESHOLD  = 0.55
_NORMAL_THRESHOLD    = 0.25
_LOW_THRESHOLD       = 0.10

# For EXPANSION/COMPRESSION: min relative vol change required
_EXPANSION_REL_MIN   = 1.10   # short_vol / medium_vol > 1.10
_COMPRESSION_REL_MAX = 0.92   # short_vol / medium_vol < 0.92
_EXPANSION_NORM_MIN  = 0.45   # normalized_vol > 0.45 during expansion
_COMPRESSION_NORM_MAX = 0.50  # normalized_vol < 0.50 during compression


class RegimeClassifier:
    """Classifies VolatilityRegimeType from VolatilityState and behaviour."""

    def classify(
        self,
        state: VolatilityState,
        behaviour: VolatilityBehaviour,
        previous_regime: VolatilityRegimeType | None,
        duration_bars: int,
    ) -> VolatilityRegimeSnapshot:
        regime = self._choose_regime(state, behaviour, previous_regime)
        confidence = self._regime_confidence(state, regime)
        transition_type = infer_transition_type(
            regime, previous_regime, state.relative_volatility
        )
        transition_prob = self._transition_probability(
            state, regime, previous_regime, duration_bars
        )
        regime_score = self._regime_score(state, regime)

        return build_regime_snapshot(
            regime=regime,
            confidence=confidence,
            duration_bars=duration_bars,
            previous_regime=previous_regime,
            transition_type=transition_type,
            transition_probability=transition_prob,
            regime_score=regime_score,
        )

    # ── Regime selection ──────────────────────────────────────────────────

    def _choose_regime(
        self,
        state: VolatilityState,
        behaviour: VolatilityBehaviour,
        previous_regime: VolatilityRegimeType | None,
    ) -> VolatilityRegimeType:
        norm = state.normalized_volatility
        rel  = state.relative_volatility

        # RECOVERY: previous was extreme/shock and vol is now falling
        if (
            previous_regime in (VolatilityRegimeType.EXTREME, VolatilityRegimeType.SHOCK)
            and rel < 0.95
            and norm < 0.80
        ):
            return VolatilityRegimeType.RECOVERY

        # SHOCK: extreme spike
        if norm >= _SHOCK_THRESHOLD:
            return VolatilityRegimeType.SHOCK

        # EXTREME
        if norm >= _EXTREME_THRESHOLD:
            return VolatilityRegimeType.EXTREME

        # EXPANSION: vol actively rising and above mid range
        if (
            norm > _EXPANSION_NORM_MIN
            and rel > _EXPANSION_REL_MIN
            and behaviour in (
                VolatilityBehaviour.EXPANDING,
                VolatilityBehaviour.ACCELERATING,
                VolatilityBehaviour.CLIMAX,
            )
        ):
            return VolatilityRegimeType.EXPANSION

        # COMPRESSION: vol actively falling and below mid range
        if (
            norm < _COMPRESSION_NORM_MAX
            and rel < _COMPRESSION_REL_MAX
            and behaviour in (
                VolatilityBehaviour.COMPRESSING,
                VolatilityBehaviour.COOLING,
                VolatilityBehaviour.DECELERATING,
            )
        ):
            return VolatilityRegimeType.COMPRESSION

        # Tier-based regimes
        if norm >= _HIGH_THRESHOLD:
            return VolatilityRegimeType.HIGH
        if norm >= _ELEVATED_THRESHOLD:
            return VolatilityRegimeType.ELEVATED
        if norm >= _NORMAL_THRESHOLD:
            return VolatilityRegimeType.NORMAL
        if norm >= _LOW_THRESHOLD:
            return VolatilityRegimeType.LOW
        return VolatilityRegimeType.VERY_LOW

    # ── Confidence ────────────────────────────────────────────────────────

    def _regime_confidence(
        self, state: VolatilityState, regime: VolatilityRegimeType
    ) -> float:
        base = state.volatility_stability * 0.5 + 0.5 * (
            1.0 - abs(state.normalized_volatility - self._regime_centre(regime))
        )
        if not state.is_initialized:
            base *= 0.6
        return max(0.1, min(0.99, base))

    def _regime_centre(self, regime: VolatilityRegimeType) -> float:
        """Approximate centre of the normalised-vol band for each regime."""
        centres = {
            VolatilityRegimeType.VERY_LOW:    0.05,
            VolatilityRegimeType.LOW:         0.175,
            VolatilityRegimeType.NORMAL:      0.40,
            VolatilityRegimeType.ELEVATED:    0.625,
            VolatilityRegimeType.HIGH:        0.775,
            VolatilityRegimeType.EXTREME:     0.90,
            VolatilityRegimeType.SHOCK:       0.97,
            VolatilityRegimeType.COMPRESSION: 0.30,
            VolatilityRegimeType.EXPANSION:   0.60,
            VolatilityRegimeType.RECOVERY:    0.50,
        }
        return centres.get(regime, 0.50)

    # ── Transition probability ────────────────────────────────────────────

    def _transition_probability(
        self,
        state: VolatilityState,
        regime: VolatilityRegimeType,
        previous_regime: VolatilityRegimeType | None,
        duration_bars: int,
    ) -> float:
        """Heuristic transition probability based on stability and duration."""
        base = 0.05

        # Longer in same regime → higher chance of staying (mean reversion)
        stability_bonus = min(0.20, duration_bars * 0.002)

        # High vol-of-vol → higher transition risk
        instability_factor = min(0.40, state.vol_of_vol / max(state.medium_term_vol, 1e-8))

        # Recovery regime transitions quickly
        if regime == VolatilityRegimeType.RECOVERY:
            base = 0.15

        prob = base + instability_factor - stability_bonus
        return max(0.01, min(0.70, prob))

    # ── Regime score ──────────────────────────────────────────────────────

    def _regime_score(
        self, state: VolatilityState, regime: VolatilityRegimeType
    ) -> float:
        """Position within the regime band, 0-100."""
        bands = {
            VolatilityRegimeType.VERY_LOW:    (0.0,  _LOW_THRESHOLD),
            VolatilityRegimeType.LOW:         (_LOW_THRESHOLD,  _NORMAL_THRESHOLD),
            VolatilityRegimeType.NORMAL:      (_NORMAL_THRESHOLD, _ELEVATED_THRESHOLD),
            VolatilityRegimeType.ELEVATED:    (_ELEVATED_THRESHOLD, _HIGH_THRESHOLD),
            VolatilityRegimeType.HIGH:        (_HIGH_THRESHOLD, _EXTREME_THRESHOLD),
            VolatilityRegimeType.EXTREME:     (_EXTREME_THRESHOLD, _SHOCK_THRESHOLD),
            VolatilityRegimeType.SHOCK:       (_SHOCK_THRESHOLD, 1.0),
        }
        band = bands.get(regime)
        if band is None:
            return 50.0
        lo, hi = band
        span = hi - lo
        if span < 1e-10:
            return 50.0
        pos = (state.normalized_volatility - lo) / span
        return max(0.0, min(100.0, pos * 100.0))
