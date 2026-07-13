"""iios/investment/strategy/risk/recovery_analysis.py
RecoveryAnalysis — evaluates how quickly and reliably a strategy recovers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict

from iios.investment.strategy.risk.risk_input import StrategyRiskInput
from iios.investment.strategy.risk.drawdown_statistics import (
    recovery_days_estimate, recovery_probability
)
from iios.investment.strategy.risk.risk_statistics import clamp


class RecoveryCategory(str, Enum):
    RAPID    = "rapid"        # < 20 trading days
    MODERATE = "moderate"     # 20–60 days
    SLOW     = "slow"         # 60–180 days
    PROLONGED = "prolonged"   # > 180 days
    UNCERTAIN = "uncertain"   # negative expected return


@dataclass(frozen=True)
class RecoveryReport:
    """Immutable recovery analysis for a strategy."""
    strategy_id:          str
    recovery_days:        float          # trading days to recover from max_drawdown
    recovery_probability: float          # 0–1
    recovery_category:    RecoveryCategory
    recovery_risk_score:  float          # 0–100; high = slow / uncertain recovery
    resilience_score:     float          # 0–100; high = bounces back well
    analysed_at:          datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def grade(self) -> str:
        s = self.recovery_risk_score
        if s <= 20: return "A"
        if s <= 40: return "B"
        if s <= 60: return "C"
        if s <= 80: return "D"
        return "F"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":         self.strategy_id,
            "recovery_days":       self.recovery_days if self.recovery_days != float("inf") else None,
            "recovery_probability": round(self.recovery_probability, 4),
            "recovery_category":   self.recovery_category.value,
            "recovery_risk_score": round(self.recovery_risk_score, 2),
            "resilience_score":    round(self.resilience_score, 2),
            "grade":               self.grade,
            "analysed_at":         self.analysed_at.isoformat(),
        }


def _category(recovery_days: float) -> RecoveryCategory:
    if recovery_days == float("inf"):
        return RecoveryCategory.UNCERTAIN
    if recovery_days < 20:
        return RecoveryCategory.RAPID
    if recovery_days < 60:
        return RecoveryCategory.MODERATE
    if recovery_days < 180:
        return RecoveryCategory.SLOW
    return RecoveryCategory.PROLONGED


def _recovery_risk(recovery_days: float, recovery_prob: float) -> float:
    if recovery_days == float("inf"):
        return 90.0
    if recovery_days < 20:
        base = 10.0
    elif recovery_days < 60:
        base = 30.0
    elif recovery_days < 180:
        base = 55.0
    else:
        base = 75.0
    # Low probability of recovery → higher risk
    prob_penalty = (1.0 - recovery_prob) * 20.0
    return clamp(base + prob_penalty)


class RecoveryAnalysis:
    """Produces a RecoveryReport for a strategy."""

    def analyse(self, inp: StrategyRiskInput) -> RecoveryReport:
        days = recovery_days_estimate(inp.max_drawdown, inp.annualized_return)
        prob = recovery_probability(inp.max_drawdown, inp.win_rate, inp.sharpe_ratio)
        cat  = _category(days)
        rr   = _recovery_risk(days, prob)
        # Resilience: how good is the strategy at recovering → inverse risk
        resilience = clamp(
            inp.win_rate * 40.0
            + inp.sharpe_ratio * 15.0
            + (1.0 - inp.max_drawdown) * 40.0
            + inp.robustness_score * 5.0
        )
        return RecoveryReport(
            strategy_id=inp.strategy_id,
            recovery_days=days,
            recovery_probability=prob,
            recovery_category=cat,
            recovery_risk_score=rr,
            resilience_score=resilience,
        )
