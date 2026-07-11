"""iios/investment/market/correlation/correlation_classifier.py
Classifies the current correlation regime from the CorrelationMatrix and
IntermarketAnalysis.
"""
from __future__ import annotations

from iios.investment.market.correlation.models import (
    CorrelationMatrix,
    CorrelationRegimeSnapshot,
    CorrelationRegimeType,
    IntermarketAnalysis,
    SystemicRiskMetrics,
)
from iios.investment.market.correlation.correlation_regime import build_regime_snapshot
from iios.investment.market.correlation.correlation_statistics import CorrelationStatistics


# ── Thresholds ────────────────────────────────────────────────────────────
_HIGHLY_CORR    = 0.70   # avg |corr| above this → HIGHLY_CORRELATED
_MODERATELY     = 0.45
_WEAKLY         = 0.20
_INDEPENDENT    = 0.10
_INVERSE        = -0.30  # avg corr below this → INVERSE_CORRELATION
_BREAKDOWN      = 0.15   # abs drop in avg corr from prev → BREAKDOWN


class CorrelationRegimeClassifier:
    """
    Classifies the current correlation regime and builds a
    CorrelationRegimeSnapshot.
    """

    def classify(
        self,
        matrix: CorrelationMatrix,
        stats: CorrelationStatistics,
        intermarket: IntermarketAnalysis,
        systemic: SystemicRiskMetrics,
        previous_regime: CorrelationRegimeType | None,
        duration_bars: int,
    ) -> CorrelationRegimeSnapshot:
        avg_corr  = matrix.avg_correlation()
        avg_abs   = matrix.avg_abs_correlation()
        prev_avg  = stats.avg_rolling_correlation()

        regime = self._choose_regime(
            avg_corr, avg_abs, prev_avg, intermarket, systemic, stats
        )
        confidence     = self._confidence(matrix, stats, avg_abs)
        trans_prob     = self._transition_prob(stats, regime, duration_bars)
        regime_score   = self._regime_score(avg_abs, regime)

        return build_regime_snapshot(
            regime=regime,
            confidence=confidence,
            duration_bars=duration_bars,
            previous_regime=previous_regime,
            avg_correlation=avg_corr,
            transition_probability=trans_prob,
            regime_score=regime_score,
        )

    # ── Regime selection ──────────────────────────────────────────────────

    def _choose_regime(
        self,
        avg_corr: float,
        avg_abs: float,
        prev_avg: float,
        intermarket: IntermarketAnalysis,
        systemic: SystemicRiskMetrics,
        stats: CorrelationStatistics,
    ) -> CorrelationRegimeType:
        # Flight to safety: strong safe-haven demand
        if intermarket.flight_to_safety:
            return CorrelationRegimeType.FLIGHT_TO_SAFETY

        # Correlation breakdown: large drop in average correlation
        if len(stats) >= 5 and prev_avg > _MODERATELY:
            drop = prev_avg - avg_abs
            if drop > _BREAKDOWN:
                return CorrelationRegimeType.CORRELATION_BREAKDOWN

        # Risk-on / risk-off from intermarket signals
        if intermarket.risk_on_signals > intermarket.risk_off_signals + 1:
            return CorrelationRegimeType.RISK_ON

        if intermarket.risk_off_signals > intermarket.risk_on_signals + 1:
            return CorrelationRegimeType.RISK_OFF

        # Purely correlation-level based
        if avg_corr <= _INVERSE:
            return CorrelationRegimeType.INVERSE_CORRELATION

        if avg_abs >= _HIGHLY_CORR:
            return CorrelationRegimeType.HIGHLY_CORRELATED

        if avg_abs >= _MODERATELY:
            return CorrelationRegimeType.MODERATELY_CORRELATED

        if avg_abs >= _WEAKLY:
            return CorrelationRegimeType.WEAKLY_CORRELATED

        if avg_abs <= _INDEPENDENT:
            return CorrelationRegimeType.INDEPENDENT

        return CorrelationRegimeType.WEAKLY_CORRELATED

    # ── Confidence ────────────────────────────────────────────────────────

    def _confidence(
        self,
        matrix: CorrelationMatrix,
        stats: CorrelationStatistics,
        avg_abs: float,
    ) -> float:
        obs_factor     = min(1.0, matrix.n_observations / max(matrix.window, 1))
        stability      = stats.correlation_stability() if len(stats) >= 5 else 0.5
        n_asset_factor = min(1.0, len(matrix.symbols) / 10)
        return max(0.10, min(0.99, obs_factor * 0.40 + stability * 0.40 + n_asset_factor * 0.20))

    # ── Transition probability ─────────────────────────────────────────────

    def _transition_prob(
        self,
        stats: CorrelationStatistics,
        regime: CorrelationRegimeType,
        duration_bars: int,
    ) -> float:
        instability    = 1.0 - stats.correlation_stability()
        duration_disc  = min(0.10, duration_bars * 0.005)
        prob = 0.10 + instability * 0.30 - duration_disc
        return max(0.01, min(0.70, prob))

    # ── Regime score ──────────────────────────────────────────────────────

    def _regime_score(
        self, avg_abs: float, regime: CorrelationRegimeType
    ) -> float:
        bands: dict[CorrelationRegimeType, tuple[float, float]] = {
            CorrelationRegimeType.INDEPENDENT:           (0.0, _INDEPENDENT),
            CorrelationRegimeType.WEAKLY_CORRELATED:     (_INDEPENDENT, _MODERATELY),
            CorrelationRegimeType.MODERATELY_CORRELATED: (_MODERATELY, _HIGHLY_CORR),
            CorrelationRegimeType.HIGHLY_CORRELATED:     (_HIGHLY_CORR, 1.0),
        }
        band = bands.get(regime)
        if band is None:
            return 50.0
        lo, hi = band
        span = hi - lo
        if span < 1e-10:
            return 50.0
        pos = (avg_abs - lo) / span
        return max(0.0, min(100.0, pos * 100))
