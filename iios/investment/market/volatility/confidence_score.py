"""iios/investment/market/volatility/confidence_score.py
Stateless function to compute ConfidenceScore components.
"""
from __future__ import annotations

from iios.investment.market.volatility.models import (
    BehaviourSnapshot,
    ConfidenceScore,
    VolatilityEstimate,
    VolatilityRegimeSnapshot,
    VolatilityState,
)
from typing import Dict


def compute_confidence(
    state: VolatilityState,
    regime_snap: VolatilityRegimeSnapshot,
    behaviour: BehaviourSnapshot,
    estimates: "Dict[str, VolatilityEstimate]",
) -> ConfidenceScore:
    """Build a ConfidenceScore from engine sub-snapshots."""

    # ── Volatility confidence: quality of the vol estimate ────────────────
    n_estimators = len(estimates)
    estimator_factor = min(1.0, n_estimators / 3.0)
    avg_conf = (
        sum(e.confidence for e in estimates.values()) / n_estimators
        if n_estimators > 0
        else 0.5
    )
    init_factor = 1.0 if state.is_initialized else 0.6
    vol_conf = avg_conf * estimator_factor * init_factor
    vol_conf = max(0.10, min(0.95, vol_conf))

    # ── Forecast confidence: how reliable is near-term vol prediction ─────
    # High persistence + stable regime → high forecast confidence
    fc = state.volatility_persistence * 0.50 + state.volatility_stability * 0.30
    fc += (1.0 - regime_snap.transition_probability) * 0.20
    fc = max(0.10, min(0.95, fc))

    # ── Regime stability: how long + confidently in current regime ────────
    duration_factor = min(1.0, regime_snap.duration_bars / 20.0)
    reg_stability = regime_snap.confidence * 0.60 + duration_factor * 0.40
    reg_stability = max(0.05, min(0.95, reg_stability))

    # ── Expected persistence of current vol level ─────────────────────────
    exp_persistence = state.volatility_persistence * 0.70 + state.volatility_stability * 0.30
    exp_persistence = max(0.05, min(0.95, exp_persistence))

    return ConfidenceScore(
        volatility_confidence=round(vol_conf, 4),
        forecast_confidence=round(fc, 4),
        regime_stability=round(reg_stability, 4),
        expected_persistence=round(exp_persistence, 4),
        transition_probability=round(regime_snap.transition_probability, 4),
    )
