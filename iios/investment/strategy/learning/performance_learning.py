"""iios/investment/strategy/learning/performance_learning.py
PerformanceLearner — learns from cumulative strategy observation history.
Extracts regime performance maps, winning / losing characteristics, and
consistency metrics without modifying strategies.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.learning.learning_input import LearningObservation
from iios.investment.strategy.learning.learning_statistics import (
    clamp, consistency_score, ewma, linear_trend
)


@dataclass(frozen=True)
class PerformanceLearningResult:
    """Learned performance intelligence for a strategy."""
    strategy_id:         str
    assessed_at:         datetime

    # Regime analysis
    regime_performance:  Dict[str, float]   # regime → mean eval score
    best_regime:         str
    worst_regime:        str

    # Summary statistics
    mean_evaluation_score:  float
    median_evaluation_score: float
    score_consistency:      float   # 0-100; higher = more consistent
    mean_sharpe:            float
    mean_win_rate:          float
    mean_max_drawdown:      float
    mean_risk_score:        float

    # Trend
    score_trend_direction:  str     # "improving" | "declining" | "stable"
    score_trend_magnitude:  float   # raw slope

    # Qualitative findings
    winning_characteristics: List[str]
    losing_characteristics:  List[str]
    insight_summary:         str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":             self.strategy_id,
            "assessed_at":             self.assessed_at.isoformat(),
            "regime_performance":      {k: round(v, 2) for k, v in self.regime_performance.items()},
            "best_regime":             self.best_regime,
            "worst_regime":            self.worst_regime,
            "mean_evaluation_score":   round(self.mean_evaluation_score, 2),
            "score_consistency":       round(self.score_consistency, 2),
            "score_trend_direction":   self.score_trend_direction,
            "winning_characteristics": self.winning_characteristics,
            "losing_characteristics":  self.losing_characteristics,
            "insight_summary":         self.insight_summary,
        }


class PerformanceLearner:
    """
    Learns from a list of LearningObservation objects.
    Pure observation — no strategy modification.
    """

    def __init__(self, min_observations: int = 3) -> None:
        self._min_obs = min_observations

    def learn(self, observations: List[LearningObservation]) -> Optional[PerformanceLearningResult]:
        if len(observations) < self._min_obs:
            return None

        sid = observations[0].strategy_id

        # Regime performance
        regime_map: Dict[str, List[float]] = {}
        for o in observations:
            regime_map.setdefault(o.current_regime, []).append(o.evaluation_score)
        regime_performance = {r: statistics.mean(vs) for r, vs in regime_map.items()}

        best_regime  = max(regime_performance, key=regime_performance.get)  # type: ignore[arg-type]
        worst_regime = min(regime_performance, key=regime_performance.get)  # type: ignore[arg-type]

        scores     = [o.evaluation_score for o in observations]
        risks      = [o.risk_score       for o in observations]
        sharpes    = [o.sharpe_ratio     for o in observations]
        win_rates  = [o.win_rate         for o in observations]
        drawdowns  = [o.max_drawdown     for o in observations]

        mean_score  = statistics.mean(scores)
        median_score = statistics.median(scores)
        consistency  = consistency_score(scores)
        slope        = linear_trend(scores)

        # Trend direction
        if slope > 0.10:
            direction = "improving"
        elif slope < -0.10:
            direction = "declining"
        else:
            direction = "stable"

        # Qualitative characteristics
        winning = self._winning_chars(observations)
        losing  = self._losing_chars(observations)

        summary = self._build_summary(
            mean_score, consistency, direction, best_regime, worst_regime
        )

        return PerformanceLearningResult(
            strategy_id=sid,
            assessed_at=datetime.now(timezone.utc),
            regime_performance=regime_performance,
            best_regime=best_regime,
            worst_regime=worst_regime,
            mean_evaluation_score=mean_score,
            median_evaluation_score=median_score,
            score_consistency=consistency,
            mean_sharpe=statistics.mean(sharpes),
            mean_win_rate=statistics.mean(win_rates),
            mean_max_drawdown=statistics.mean(drawdowns),
            mean_risk_score=statistics.mean(risks),
            score_trend_direction=direction,
            score_trend_magnitude=slope,
            winning_characteristics=winning,
            losing_characteristics=losing,
            insight_summary=summary,
        )

    def _winning_chars(self, obs: List[LearningObservation]) -> List[str]:
        chars: List[str] = []
        top = sorted(obs, key=lambda o: o.evaluation_score, reverse=True)[:max(1, len(obs)//3)]
        if not top:
            return chars

        # Regime alignment
        aligned = sum(1 for o in top if not o.regime_mismatch)
        if aligned / len(top) >= 0.7:
            chars.append("Performs best when deployed in aligned market regimes")

        # Low drawdown
        avg_dd = statistics.mean(o.max_drawdown for o in top)
        if avg_dd < 0.12:
            chars.append(f"Top-quartile periods show controlled drawdown (avg {avg_dd:.1%})")

        # High sharpe
        avg_sharpe = statistics.mean(o.sharpe_ratio for o in top)
        if avg_sharpe >= 1.2:
            chars.append(f"Best periods exhibit strong risk-adjusted returns (avg Sharpe {avg_sharpe:.2f})")

        # Market conditions
        low_vol = sum(1 for o in top if o.current_volatility_level in ("low", "normal"))
        if low_vol / len(top) >= 0.7:
            chars.append("Success concentrated in low/normal volatility environments")

        return chars

    def _losing_chars(self, obs: List[LearningObservation]) -> List[str]:
        chars: List[str] = []
        bottom = sorted(obs, key=lambda o: o.evaluation_score)[:max(1, len(obs)//3)]
        if not bottom:
            return chars

        mismatched = sum(1 for o in bottom if o.regime_mismatch)
        if mismatched / len(bottom) >= 0.5:
            chars.append("Poor performance concentrated during regime-mismatch periods")

        avg_dd = statistics.mean(o.max_drawdown for o in bottom)
        if avg_dd > 0.20:
            chars.append(f"Weak periods show high drawdown (avg {avg_dd:.1%})")

        high_vol = sum(1 for o in bottom if o.current_volatility_level in ("high", "extreme"))
        if high_vol / len(bottom) >= 0.5:
            chars.append("Underperformance clusters during elevated volatility periods")

        return chars

    @staticmethod
    def _build_summary(
        mean_score: float,
        consistency: float,
        direction: str,
        best_regime: str,
        worst_regime: str,
    ) -> str:
        quality = "strong" if mean_score >= 70 else ("moderate" if mean_score >= 50 else "weak")
        cons    = "consistently" if consistency >= 70 else ("variably" if consistency >= 40 else "erratically")
        return (
            f"Strategy demonstrates {quality} average performance ({mean_score:.1f}/100), "
            f"{cons} delivered, with a {direction} trajectory. "
            f"Best regime: {best_regime}; worst: {worst_regime}."
        )
