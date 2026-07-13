"""iios/investment/strategy/risk/model_risk.py
ModelRiskAnalyzer — evaluates risk from model assumptions and data quality.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from iios.investment.strategy.risk.risk_input import StrategyRiskInput
from iios.investment.strategy.risk.risk_statistics import clamp, safe_div


@dataclass(frozen=True)
class ModelRiskResult:
    """
    Decomposed model risk scores.  All in [0, 100].
    """
    strategy_id: str

    overfitting_risk:        float   # inverse of robustness_score
    regime_sensitivity_risk: float   # too few regimes supported
    confidence_risk:         float   # low evaluation confidence
    complexity_risk:         float   # strategy structural complexity
    data_quality_risk:       float   # confidence proxy for data sufficiency

    overall_model_risk: float

    @property
    def grade(self) -> str:
        s = self.overall_model_risk
        if s <= 20: return "A"
        if s <= 40: return "B"
        if s <= 60: return "C"
        if s <= 80: return "D"
        return "F"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":         self.strategy_id,
            "overfitting_risk":    round(self.overfitting_risk, 2),
            "regime_sensitivity":  round(self.regime_sensitivity_risk, 2),
            "confidence_risk":     round(self.confidence_risk, 2),
            "complexity_risk":     round(self.complexity_risk, 2),
            "data_quality_risk":   round(self.data_quality_risk, 2),
            "overall_model_risk":  round(self.overall_model_risk, 2),
            "grade":               self.grade,
        }


class ModelRiskAnalyzer:
    """Computes model-quality risk from evaluation metadata."""

    def analyse(self, inp: StrategyRiskInput) -> ModelRiskResult:
        overfit    = self._overfitting_risk(inp)
        regime_sen = self._regime_sensitivity(inp)
        conf_risk  = self._confidence_risk(inp)
        complexity = self._complexity_risk(inp)
        dq_risk    = self._data_quality_risk(inp)

        overall = clamp(
            0.30 * overfit
            + 0.25 * regime_sen
            + 0.20 * conf_risk
            + 0.15 * complexity
            + 0.10 * dq_risk
        )
        return ModelRiskResult(
            strategy_id=inp.strategy_id,
            overfitting_risk=overfit,
            regime_sensitivity_risk=regime_sen,
            confidence_risk=conf_risk,
            complexity_risk=complexity,
            data_quality_risk=dq_risk,
            overall_model_risk=overall,
        )

    def _overfitting_risk(self, inp: StrategyRiskInput) -> float:
        # robustness_score 0-1; low robustness → high overfit risk
        return clamp((1.0 - inp.robustness_score) * 100.0)

    def _regime_sensitivity(self, inp: StrategyRiskInput) -> float:
        n = len(inp.supported_regimes)
        if n == 0:
            return 90.0
        if n == 1:
            return 70.0
        if n == 2:
            return 45.0
        if n == 3:
            return 25.0
        return 10.0

    def _confidence_risk(self, inp: StrategyRiskInput) -> float:
        # confidence_score 0-100; low confidence → high risk
        return clamp((100.0 - inp.confidence_score))

    def _complexity_risk(self, inp: StrategyRiskInput) -> float:
        # More tags → more parameters → higher complexity risk
        n_tags = len(inp.tags)
        return clamp(min(n_tags * 8.0, 60.0))

    def _data_quality_risk(self, inp: StrategyRiskInput) -> float:
        # Low evaluation score on a strategy with high vol → data quality concern
        if inp.evaluation_score >= 70.0 and inp.robustness_score >= 0.7:
            return 10.0
        if inp.evaluation_score >= 55.0:
            return 30.0
        return 55.0
