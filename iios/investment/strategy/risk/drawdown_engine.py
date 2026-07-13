"""iios/investment/strategy/risk/drawdown_engine.py
DrawdownEngine — integrates DrawdownProfile and RecoveryAnalysis.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from iios.investment.strategy.risk.risk_input import StrategyRiskInput
from iios.investment.strategy.risk.drawdown_profile import DrawdownProfile
from iios.investment.strategy.risk.recovery_analysis import RecoveryAnalysis, RecoveryReport
from iios.investment.strategy.risk.risk_statistics import clamp


@dataclass(frozen=True)
class DrawdownReport:
    """Complete drawdown intelligence for a strategy."""
    strategy_id: str
    profile:     DrawdownProfile
    recovery:    RecoveryReport
    overall_drawdown_risk_score: float   # 0-100
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def grade(self) -> str:
        s = self.overall_drawdown_risk_score
        if s <= 20: return "A"
        if s <= 40: return "B"
        if s <= 60: return "C"
        if s <= 80: return "D"
        return "F"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":               self.strategy_id,
            "overall_drawdown_risk_score": round(self.overall_drawdown_risk_score, 2),
            "grade":                     self.grade,
            "profile":                   self.profile.to_dict(),
            "recovery":                  self.recovery.to_dict(),
            "generated_at":              self.generated_at.isoformat(),
        }


class DrawdownEngine:
    """
    Produces comprehensive DrawdownReport by combining DrawdownProfile
    and RecoveryAnalysis.
    """

    def __init__(
        self,
        recovery_analysis: Optional[RecoveryAnalysis] = None,
    ) -> None:
        self._recovery = recovery_analysis or RecoveryAnalysis()

    def evaluate(self, inp: StrategyRiskInput) -> DrawdownReport:
        profile = DrawdownProfile.from_evaluation(
            strategy_id=inp.strategy_id,
            max_drawdown=inp.max_drawdown,
            annualized_return=inp.annualized_return,
            annualized_vol=inp.annualized_vol,
            win_rate=inp.win_rate,
            sharpe_ratio=inp.sharpe_ratio,
        )
        recovery = self._recovery.analyse(inp)

        # Blend: 60% drawdown profile depth, 40% recovery risk
        overall = clamp(
            0.60 * profile.drawdown_risk_score
            + 0.40 * recovery.recovery_risk_score
        )
        return DrawdownReport(
            strategy_id=inp.strategy_id,
            profile=profile,
            recovery=recovery,
            overall_drawdown_risk_score=overall,
        )
