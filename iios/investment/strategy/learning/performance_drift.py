"""iios/investment/strategy/learning/performance_drift.py
PerformanceDrift — rolling window comparison of recent vs baseline performance.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.learning.learning_input import LearningObservation
from iios.investment.strategy.learning.learning_statistics import (
    drift_magnitude, clamp, ewma
)


@dataclass(frozen=True)
class DriftWindow:
    """Statistics for a single observation window."""
    mean_score:     float
    mean_risk:      float
    mean_win_rate:  float
    mean_sharpe:    float
    mean_drawdown:  float
    observation_count: int


@dataclass(frozen=True)
class PerformanceDrift:
    """
    Point-in-time drift report comparing recent performance to baseline.
    All drift values: positive = improvement, negative = degradation.
    """
    strategy_id:       str
    assessed_at:       datetime

    baseline:          DriftWindow
    recent:            DriftWindow

    score_drift:       float    # pct change in eval score
    risk_drift:        float    # pct change in risk (positive = more risky)
    win_rate_drift:    float
    sharpe_drift:      float
    drawdown_drift:    float    # positive = drawdown increased (worse)

    overall_drift:     float    # composite: positive = improving
    drift_direction:   str      # "improving" | "degrading" | "stable"
    is_significant:    bool     # any single metric > mild threshold

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":    self.strategy_id,
            "assessed_at":    self.assessed_at.isoformat(),
            "score_drift":    round(self.score_drift, 4),
            "risk_drift":     round(self.risk_drift, 4),
            "win_rate_drift": round(self.win_rate_drift, 4),
            "sharpe_drift":   round(self.sharpe_drift, 4),
            "drawdown_drift": round(self.drawdown_drift, 4),
            "overall_drift":  round(self.overall_drift, 4),
            "drift_direction": self.drift_direction,
            "is_significant": self.is_significant,
        }


class PerformanceDriftAnalyzer:
    """
    Computes drift by comparing a baseline window to a recent window.
    Stateless — call analyse() with observation lists each time.
    """

    def __init__(self, mild_threshold: float = 0.05) -> None:
        self._mild_thr = mild_threshold

    def analyse(
        self,
        baseline_obs: List[LearningObservation],
        recent_obs:   List[LearningObservation],
    ) -> Optional[PerformanceDrift]:
        if not baseline_obs or not recent_obs:
            return None

        bl = self._window(baseline_obs)
        rc = self._window(recent_obs)

        score_drift    = drift_magnitude(bl.mean_score, rc.mean_score)
        risk_drift     = drift_magnitude(bl.mean_risk, rc.mean_risk)
        win_rate_drift = drift_magnitude(bl.mean_win_rate, rc.mean_win_rate)
        sharpe_drift   = drift_magnitude(bl.mean_sharpe, rc.mean_sharpe)
        drawdown_drift = drift_magnitude(bl.mean_drawdown, rc.mean_drawdown)

        # Composite: score and sharpe improvement positive; risk and drawdown increase negative
        overall_drift = (
            0.40 * score_drift
            + 0.25 * sharpe_drift
            - 0.20 * risk_drift
            + 0.15 * win_rate_drift
            - 0.10 * drawdown_drift    # penalty for drawdown increase
        )

        if overall_drift > self._mild_thr:
            direction = "improving"
        elif overall_drift < -self._mild_thr:
            direction = "degrading"
        else:
            direction = "stable"

        is_significant = any(
            abs(d) > self._mild_thr
            for d in (score_drift, risk_drift, win_rate_drift, sharpe_drift, drawdown_drift)
        )

        return PerformanceDrift(
            strategy_id=recent_obs[0].strategy_id,
            assessed_at=datetime.now(timezone.utc),
            baseline=bl,
            recent=rc,
            score_drift=score_drift,
            risk_drift=risk_drift,
            win_rate_drift=win_rate_drift,
            sharpe_drift=sharpe_drift,
            drawdown_drift=drawdown_drift,
            overall_drift=overall_drift,
            drift_direction=direction,
            is_significant=is_significant,
        )

    @staticmethod
    def _window(obs: List[LearningObservation]) -> DriftWindow:
        def mean(vals: List[float]) -> float:
            return statistics.mean(vals) if vals else 0.0

        return DriftWindow(
            mean_score=mean([o.evaluation_score for o in obs]),
            mean_risk=mean([o.risk_score for o in obs]),
            mean_win_rate=mean([o.win_rate for o in obs]),
            mean_sharpe=mean([o.sharpe_ratio for o in obs]),
            mean_drawdown=mean([o.max_drawdown for o in obs]),
            observation_count=len(obs),
        )
