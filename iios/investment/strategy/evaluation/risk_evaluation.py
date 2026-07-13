"""iios/investment/strategy/evaluation/risk_evaluation.py
RiskMetrics — combined risk report.  Orchestrates drawdown, volatility, tail risk.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from iios.investment.strategy.evaluation.evaluation_input import EvaluationInput
from iios.investment.strategy.evaluation.drawdown_analysis import DrawdownAnalyzer, DrawdownMetrics
from iios.investment.strategy.evaluation.volatility_analysis import VolatilityAnalyzer, VolatilityMetrics
from iios.investment.strategy.evaluation.tail_risk import TailRiskAnalyzer, TailRiskMetrics


@dataclass(frozen=True)
class RiskMetrics:
    drawdown: DrawdownMetrics
    volatility: VolatilityMetrics
    tail: TailRiskMetrics

    # Convenience flat access
    @property
    def max_drawdown(self) -> float:
        return self.drawdown.max_drawdown

    @property
    def ulcer_index(self) -> float:
        return self.drawdown.ulcer_index

    @property
    def annualized_volatility(self) -> float:
        return self.volatility.annualized_volatility

    @property
    def var_95(self) -> float:
        return self.tail.var_95

    @property
    def cvar_95(self) -> float:
        return self.tail.cvar_95

    def to_dict(self) -> Dict[str, Any]:
        return {
            "drawdown":   self.drawdown.to_dict(),
            "volatility": self.volatility.to_dict(),
            "tail":       self.tail.to_dict(),
        }


class RiskEvaluator:
    """Composes DrawdownAnalyzer, VolatilityAnalyzer, TailRiskAnalyzer."""

    def __init__(self) -> None:
        self._dd = DrawdownAnalyzer()
        self._vol = VolatilityAnalyzer()
        self._tail = TailRiskAnalyzer()

    def evaluate(
        self, inp: EvaluationInput, ann_return: float = 0.0
    ) -> RiskMetrics:
        curve = inp.equity_curve
        dd = self._dd.analyze(curve)
        vol = self._vol.analyze(
            curve, ann_return, inp.rf_per_period, inp.periods_per_year
        )
        tail = self._tail.analyze(curve)
        return RiskMetrics(drawdown=dd, volatility=vol, tail=tail)
