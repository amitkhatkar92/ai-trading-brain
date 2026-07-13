"""iios/investment/strategy/learning/parameter_analysis.py
ParameterAnalysis — assesses stability and drift of strategy parameters over time.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.learning.learning_input import LearningObservation
from iios.investment.strategy.learning.learning_statistics import (
    consistency_score, linear_trend, clamp, coefficient_of_variation
)


@dataclass(frozen=True)
class ParameterStabilityResult:
    """Stability assessment of the implicit parameters visible through observations."""
    strategy_id:         str
    assessed_at:         datetime

    sharpe_stability:    float    # 0-100; 100 = highly consistent Sharpe
    drawdown_stability:  float
    win_rate_stability:  float
    vol_stability:       float
    overall_stability:   float    # weighted composite

    parameter_cv:        Dict[str, float]   # coefficient of variation per metric
    is_stable:           bool               # overall_stability >= 60
    instability_drivers: List[str]          # which parameters are unstable

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":        self.strategy_id,
            "assessed_at":        self.assessed_at.isoformat(),
            "sharpe_stability":   round(self.sharpe_stability, 2),
            "drawdown_stability": round(self.drawdown_stability, 2),
            "win_rate_stability": round(self.win_rate_stability, 2),
            "vol_stability":      round(self.vol_stability, 2),
            "overall_stability":  round(self.overall_stability, 2),
            "is_stable":          self.is_stable,
            "instability_drivers": self.instability_drivers,
        }


class ParameterAnalyzer:
    """
    Analyses the stability of observable parameters (sharpe, drawdown, win_rate, vol)
    across the full observation history. Detects parameter drift without modifying anything.
    """

    def __init__(self, instability_threshold: float = 0.40) -> None:
        self._threshold = instability_threshold

    def analyse(self, observations: List[LearningObservation]) -> Optional[ParameterStabilityResult]:
        if len(observations) < 3:
            return None

        sid = observations[0].strategy_id
        sharpes   = [o.sharpe_ratio     for o in observations]
        drawdowns = [o.max_drawdown     for o in observations]
        win_rates = [o.win_rate         for o in observations]
        vols      = [o.annualized_vol   for o in observations]

        sharpe_stab   = consistency_score(sharpes)
        drawdown_stab = consistency_score(drawdowns)
        win_rate_stab = consistency_score(win_rates)
        vol_stab      = consistency_score(vols)

        overall = clamp(
            0.35 * sharpe_stab
            + 0.25 * drawdown_stab
            + 0.25 * win_rate_stab
            + 0.15 * vol_stab
        )

        cv_map = {
            "sharpe_ratio":    round(coefficient_of_variation(sharpes),   4),
            "max_drawdown":    round(coefficient_of_variation(drawdowns),  4),
            "win_rate":        round(coefficient_of_variation(win_rates),  4),
            "annualized_vol":  round(coefficient_of_variation(vols),       4),
        }

        drivers: List[str] = []
        if sharpe_stab < 50:
            drivers.append("Sharpe ratio is highly variable — signal consistency may be degrading")
        if drawdown_stab < 50:
            drivers.append("Max drawdown varies widely — risk management inconsistency detected")
        if win_rate_stab < 50:
            drivers.append("Win rate fluctuates significantly — entry signal quality is unstable")
        if vol_stab < 50:
            drivers.append("Portfolio volatility is inconsistent — market exposure is changing")

        return ParameterStabilityResult(
            strategy_id=sid,
            assessed_at=datetime.now(timezone.utc),
            sharpe_stability=sharpe_stab,
            drawdown_stability=drawdown_stab,
            win_rate_stability=win_rate_stab,
            vol_stability=vol_stab,
            overall_stability=overall,
            parameter_cv=cv_map,
            is_stable=overall >= 60.0,
            instability_drivers=drivers,
        )
