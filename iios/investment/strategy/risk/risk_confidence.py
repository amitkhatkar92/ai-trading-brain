"""iios/investment/strategy/risk/risk_confidence.py
RiskConfidence — assesses how confident we are in the risk assessment.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict

from iios.investment.strategy.risk.risk_input import StrategyRiskInput
from iios.investment.strategy.risk.risk_statistics import clamp


@dataclass(frozen=True)
class RiskConfidence:
    """
    Confidence in the risk evaluation. High confidence = reliable risk scores.
    All scores 0-100; 100 = maximum confidence.
    """
    strategy_id: str

    data_confidence:     float   # driven by evaluation confidence_score
    regime_confidence:   float   # known vs unknown regime
    model_confidence:    float   # driven by robustness_score
    stability_confidence: float  # does risk appear stable?
    overall_confidence:  float   # composite

    @property
    def grade(self) -> str:
        c = self.overall_confidence
        if c >= 80: return "HIGH"
        if c >= 55: return "MEDIUM"
        return "LOW"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":        self.strategy_id,
            "data_confidence":    round(self.data_confidence, 2),
            "regime_confidence":  round(self.regime_confidence, 2),
            "model_confidence":   round(self.model_confidence, 2),
            "stability_confidence": round(self.stability_confidence, 2),
            "overall_confidence": round(self.overall_confidence, 2),
            "grade":              self.grade,
        }

    @classmethod
    def compute(cls, inp: StrategyRiskInput) -> "RiskConfidence":
        data_conf   = clamp(inp.confidence_score)                         # direct from evaluation
        regime_conf = 90.0 if inp.current_regime != "unknown" else 45.0  # known regime
        model_conf  = clamp(inp.robustness_score * 100.0)
        stab_conf   = 80.0 if inp.evaluation_score >= 60.0 else 50.0

        overall = clamp(
            0.35 * data_conf
            + 0.25 * regime_conf
            + 0.25 * model_conf
            + 0.15 * stab_conf
        )
        return cls(
            strategy_id=inp.strategy_id,
            data_confidence=data_conf,
            regime_confidence=regime_conf,
            model_confidence=model_conf,
            stability_confidence=stab_conf,
            overall_confidence=overall,
        )
