"""iios/investment/strategy/risk/risk_quality.py
RiskQuality — assesses the quality and completeness of the risk assessment.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

from iios.investment.strategy.risk.risk_input import StrategyRiskInput
from iios.investment.strategy.risk.risk_score import RiskScore
from iios.investment.strategy.risk.risk_confidence import RiskConfidence
from iios.investment.strategy.risk.risk_statistics import clamp


@dataclass(frozen=True)
class RiskQuality:
    """
    Meta-quality assessment of the risk evaluation process itself.
    High quality = all inputs present, consistency across dimensions,
    no conflicting signals.
    """
    strategy_id: str

    input_completeness: float    # 0-100: all required inputs populated?
    dimension_consistency: float # 0-100: risk dims agree directionally?
    score_stability:     float   # 0-100: is the risk score internally consistent?
    data_freshness:      float   # 0-100: how recent is the input data?

    overall_quality:     float   # composite
    quality_issues:      List[str]   # list of detected issues

    assessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def grade(self) -> str:
        q = self.overall_quality
        if q >= 80: return "A"
        if q >= 65: return "B"
        if q >= 50: return "C"
        if q >= 35: return "D"
        return "F"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":         self.strategy_id,
            "input_completeness":  round(self.input_completeness, 2),
            "dimension_consistency": round(self.dimension_consistency, 2),
            "score_stability":     round(self.score_stability, 2),
            "data_freshness":      round(self.data_freshness, 2),
            "overall_quality":     round(self.overall_quality, 2),
            "grade":               self.grade,
            "quality_issues":      self.quality_issues,
            "assessed_at":         self.assessed_at.isoformat(),
        }

    @classmethod
    def assess(
        cls,
        inp:        StrategyRiskInput,
        risk_score: RiskScore,
        confidence: RiskConfidence,
    ) -> "RiskQuality":
        issues: List[str] = []

        # Input completeness: check required fields
        completeness = 100.0
        if inp.current_regime == "unknown":
            completeness -= 15.0
            issues.append("Current market regime unknown — regime risk may be underestimated")
        if not inp.sectors:
            completeness -= 5.0
        if not inp.tags:
            completeness -= 5.0
        if inp.evaluation_score == 0.0:
            completeness -= 20.0
            issues.append("Evaluation score is zero — risk assessment reliability degraded")

        # Dimension consistency: do high-vol strategies also show high market risk?
        # If vol is high but market_risk is low → inconsistency
        market_risk = risk_score.market_risk_score
        vol_proxy   = min(100.0, inp.annualized_vol * 250.0)
        diff        = abs(market_risk - vol_proxy)
        consistency = max(0.0, 100.0 - diff)

        # Score stability: are model and drawdown risk directionally aligned?
        model_dd_diff = abs(risk_score.model_risk_score - risk_score.drawdown_risk_score)
        stability     = max(0.0, 100.0 - model_dd_diff * 0.5)

        # Data freshness (always 100 since we only have current inputs)
        freshness = 100.0

        overall = clamp(
            0.40 * completeness
            + 0.25 * consistency
            + 0.25 * stability
            + 0.10 * freshness
        )
        return cls(
            strategy_id=inp.strategy_id,
            input_completeness=completeness,
            dimension_consistency=consistency,
            score_stability=stability,
            data_freshness=freshness,
            overall_quality=overall,
            quality_issues=issues,
        )
