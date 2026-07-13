"""iios/investment/strategy/risk/drawdown_profile.py
DrawdownProfile — immutable drawdown characteristics of a strategy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from iios.investment.strategy.risk.drawdown_statistics import (
    expected_drawdown, max_expected_drawdown,
    recovery_days_estimate, recovery_probability,
    calmar_ratio, drawdown_risk_score
)


@dataclass(frozen=True)
class DrawdownProfile:
    """
    Immutable snapshot of drawdown characteristics for a strategy.
    Derived from evaluation intelligence; not independently computed.
    """
    strategy_id:   str

    # Historical drawdown (from EvaluationEngine)
    max_drawdown:  float     # 0-1 (e.g. 0.15 = 15%)

    # Derived estimates
    expected_drawdown:     float    # typical drawdown to expect
    max_expected_drawdown: float    # worst-case drawdown under GBM
    calmar_ratio:          float    # return-to-drawdown quality
    recovery_days:         float    # expected trading days to recover
    recovery_probability:  float    # probability of full recovery (0-1)
    drawdown_risk_score:   float    # 0-100 composite

    profiled_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def grade(self) -> str:
        s = self.drawdown_risk_score
        if s <= 20: return "A"
        if s <= 40: return "B"
        if s <= 60: return "C"
        if s <= 80: return "D"
        return "F"

    @property
    def recovery_days_display(self) -> str:
        if self.recovery_days == float("inf"):
            return "N/A (negative expected return)"
        return f"{self.recovery_days:.0f} trading days"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":         self.strategy_id,
            "max_drawdown":        round(self.max_drawdown, 4),
            "expected_drawdown":   round(self.expected_drawdown, 4),
            "max_expected_drawdown": round(self.max_expected_drawdown, 4),
            "calmar_ratio":        round(self.calmar_ratio, 4),
            "recovery_days":       self.recovery_days if self.recovery_days != float("inf") else None,
            "recovery_probability": round(self.recovery_probability, 4),
            "drawdown_risk_score": round(self.drawdown_risk_score, 2),
            "grade":               self.grade,
            "profiled_at":         self.profiled_at.isoformat(),
        }

    @classmethod
    def from_evaluation(
        cls,
        strategy_id:       str,
        max_drawdown:      float,
        annualized_return: float,
        annualized_vol:    float,
        win_rate:          float,
        sharpe_ratio:      float,
    ) -> "DrawdownProfile":
        exp_dd  = expected_drawdown(max_drawdown, win_rate)
        max_exp = max_expected_drawdown(annualized_vol)
        calmar  = calmar_ratio(annualized_return, max_drawdown)
        rec_days = recovery_days_estimate(max_drawdown, annualized_return)
        rec_prob = recovery_probability(max_drawdown, win_rate, sharpe_ratio)
        dd_score = drawdown_risk_score(max_drawdown, exp_dd)

        return cls(
            strategy_id=strategy_id,
            max_drawdown=max_drawdown,
            expected_drawdown=exp_dd,
            max_expected_drawdown=max_exp,
            calmar_ratio=calmar,
            recovery_days=rec_days,
            recovery_probability=rec_prob,
            drawdown_risk_score=dd_score,
        )
