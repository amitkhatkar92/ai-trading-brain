"""iios/investment/strategy/evaluation/strategy_explanation.py
StrategyExplanation — top-level explainability report.
Orchestrates SignalExplainer and EvaluationSummaryBuilder.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from iios.investment.strategy.evaluation.evaluation_input import EvaluationInput
from iios.investment.strategy.evaluation.signal_explanation import (
    SignalExplainer, SignalExplanation
)
from iios.investment.strategy.evaluation.evaluation_summary import (
    EvaluationSummaryBuilder, EvaluationSummary
)


@dataclass(frozen=True)
class StrategyExplanation:
    signal: SignalExplanation
    summary: EvaluationSummary

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal":  self.signal.to_dict(),
            "summary": self.summary.to_dict(),
        }


class StrategyExplainer:

    def __init__(self) -> None:
        self._signal_explainer = SignalExplainer()
        self._summary_builder = EvaluationSummaryBuilder()

    def explain(
        self,
        inp: EvaluationInput,
        *,
        sharpe: float = 0.0,
        max_drawdown: float = 0.0,
        win_rate: float = 0.0,
        profit_factor: float = 0.0,
        mc_robustness: float = 0.0,
        wf_stability: float = 0.0,
        stress_survival: float = 0.0,
        overall_score: float = 0.0,
    ) -> StrategyExplanation:
        signal = self._signal_explainer.explain(inp.trades)
        summary = self._summary_builder.build(
            sharpe=sharpe,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            mc_robustness=mc_robustness,
            wf_stability=wf_stability,
            stress_survival=stress_survival,
            n_trades=len(inp.trades),
            duration_years=inp.duration_years,
            overall_score=overall_score,
        )
        return StrategyExplanation(signal=signal, summary=summary)
