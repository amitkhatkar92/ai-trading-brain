"""iios/investment/strategy/risk/scenario_engine.py
ScenarioEngine — pluggable scenario evaluation.
Apply a StressScenario to a StrategyRiskInput and produce a ScenarioResult.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from iios.investment.strategy.risk.risk_input import StrategyRiskInput
from iios.investment.strategy.risk.stress_scenarios import StressScenario
from iios.investment.strategy.risk.risk_analysis import RiskAnalysis, RiskAnalysisResult
from iios.investment.strategy.risk.stress_statistics import (
    stressed_vol, stressed_drawdown, risk_amplification,
    survival_probability, stressed_expected_loss, worst_case_loss
)
from iios.investment.strategy.risk.risk_statistics import clamp


@dataclass(frozen=True)
class ScenarioResult:
    """Risk evaluation of a strategy under one stress scenario."""
    strategy_id:            str
    scenario_name:          str
    base_risk_score:        float
    stressed_risk_score:    float
    risk_amplification:     float    # stressed / base (>1 = worse)
    survival_probability:   float    # 0–1
    expected_loss_pct:      float    # expected daily loss under scenario (fraction)
    worst_case_loss_pct:    float    # worst-case portfolio loss (fraction)
    scenario_probability:   float    # P(scenario occurs)
    passes:                 bool     # strategy survives (stressed_score <= 80)
    analysed_at:            datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":          self.strategy_id,
            "scenario_name":        self.scenario_name,
            "base_risk_score":      round(self.base_risk_score, 2),
            "stressed_risk_score":  round(self.stressed_risk_score, 2),
            "risk_amplification":   round(self.risk_amplification, 3),
            "survival_probability": round(self.survival_probability, 4),
            "expected_loss_pct":    round(self.expected_loss_pct, 6),
            "worst_case_loss_pct":  round(self.worst_case_loss_pct, 6),
            "scenario_probability": round(self.scenario_probability, 4),
            "passes":               self.passes,
            "analysed_at":          self.analysed_at.isoformat(),
        }


# ScenarioFn: callable that takes (inp, scenario, base_result) → stressed_score
ScenarioFn = Callable[[StrategyRiskInput, StressScenario, RiskAnalysisResult], float]


def _default_scenario_fn(
    inp: StrategyRiskInput,
    scenario: StressScenario,
    base: RiskAnalysisResult,
) -> float:
    """
    Default stress scoring:
      stressed_score = market_part * vol_mult + liquidity_part * liq_mult + ...
    """
    stressed_mkt = clamp(base.market.overall_market_risk * scenario.vol_multiplier)
    stressed_liq = clamp(base.liquidity.overall_liquidity_risk * scenario.liquidity_multiplier)
    stressed_exc = clamp(base.execution.overall_execution_risk * scenario.execution_multiplier)
    stressed_dd  = clamp(base.market.drawdown_risk * scenario.drawdown_multiplier)

    return clamp(
        0.30 * stressed_mkt
        + 0.25 * stressed_dd
        + 0.25 * stressed_liq
        + 0.20 * stressed_exc
    )


class ScenarioEngine:
    """
    Evaluates a StressScenario against a StrategyRiskInput.
    Pluggable: custom scenario functions can be registered per scenario name.
    """

    def __init__(self, risk_analysis: Optional[RiskAnalysis] = None) -> None:
        self._analysis = risk_analysis or RiskAnalysis()
        self._custom_fns: Dict[str, ScenarioFn] = {}

    def register_scenario_fn(self, scenario_name: str, fn: ScenarioFn) -> None:
        """Register a custom stress function for a named scenario."""
        self._custom_fns[scenario_name] = fn

    def evaluate(
        self,
        inp:      StrategyRiskInput,
        scenario: StressScenario,
        base:     Optional[RiskAnalysisResult] = None,
    ) -> ScenarioResult:
        if base is None:
            base = self._analysis.analyse(inp)

        fn = self._custom_fns.get(scenario.name, _default_scenario_fn)
        stressed_score = fn(inp, scenario, base)

        ampl   = risk_amplification(base.composite_risk_score, stressed_score)
        surv   = survival_probability(base.composite_risk_score, ampl)
        el     = stressed_expected_loss(inp.annualized_vol, scenario.vol_multiplier)
        wc     = worst_case_loss(inp.max_drawdown, scenario.drawdown_multiplier, inp.portfolio_weight or 1.0)

        return ScenarioResult(
            strategy_id=inp.strategy_id,
            scenario_name=scenario.name,
            base_risk_score=base.composite_risk_score,
            stressed_risk_score=stressed_score,
            risk_amplification=ampl,
            survival_probability=surv,
            expected_loss_pct=el,
            worst_case_loss_pct=wc,
            scenario_probability=scenario.probability,
            passes=stressed_score <= 80.0,
        )
