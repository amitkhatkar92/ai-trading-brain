"""iios/investment/strategy/risk/risk_score.py
RiskScore — composite institutional-grade risk score for a strategy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from iios.investment.strategy.risk.risk_input import StrategyRiskInput
from iios.investment.strategy.risk.risk_analysis import RiskAnalysis, RiskAnalysisResult
from iios.investment.strategy.risk.drawdown_engine import DrawdownEngine, DrawdownReport
from iios.investment.strategy.risk.stress_testing import StressTestingEngine, StressTestReport
from iios.investment.strategy.risk.risk_statistics import clamp


@dataclass(frozen=True)
class RiskScore:
    """
    Final composite risk score for a strategy.
    All component scores 0-100; 0=no risk, 100=maximum risk.
    Grade: A(≤20)  B(≤40)  C(≤60)  D(≤80)  F(>80)
    """
    strategy_id: str

    # Dimension scores
    market_risk_score:    float
    execution_risk_score: float
    liquidity_risk_score: float
    model_risk_score:     float
    drawdown_risk_score:  float
    stress_risk_score:    float   # aggregate stress score

    # Final composite
    overall_risk_score: float

    # Supporting info
    risk_grade:    str
    is_acceptable: bool    # overall_risk_score <= max_risk_threshold

    scored_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    _WEIGHTS = {
        "market":    0.30,
        "model":     0.25,
        "drawdown":  0.20,
        "liquidity": 0.15,
        "execution": 0.10,
    }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":         self.strategy_id,
            "overall_risk_score":  round(self.overall_risk_score, 2),
            "risk_grade":          self.risk_grade,
            "is_acceptable":       self.is_acceptable,
            "dimensions": {
                "market":    round(self.market_risk_score, 2),
                "execution": round(self.execution_risk_score, 2),
                "liquidity": round(self.liquidity_risk_score, 2),
                "model":     round(self.model_risk_score, 2),
                "drawdown":  round(self.drawdown_risk_score, 2),
                "stress":    round(self.stress_risk_score, 2),
            },
            "scored_at": self.scored_at.isoformat(),
        }


def _grade(score: float) -> str:
    if score <= 20: return "A"
    if score <= 40: return "B"
    if score <= 60: return "C"
    if score <= 80: return "D"
    return "F"


class RiskScoreCalculator:
    """
    Computes the final RiskScore from all risk sub-engines.
    Stress score is included with lower weight when available.
    """

    def __init__(
        self,
        risk_analysis:    Optional[RiskAnalysis]       = None,
        drawdown_engine:  Optional[DrawdownEngine]     = None,
        stress_engine:    Optional[StressTestingEngine] = None,
        max_risk_threshold: float = 75.0,
    ) -> None:
        self._analysis  = risk_analysis    or RiskAnalysis()
        self._drawdown  = drawdown_engine  or DrawdownEngine()
        self._stress    = stress_engine    or StressTestingEngine()
        self._threshold = max_risk_threshold

    def score(
        self,
        inp: StrategyRiskInput,
        analysis: Optional[RiskAnalysisResult] = None,
        drawdown: Optional[DrawdownReport]      = None,
        stress:   Optional[StressTestReport]    = None,
    ) -> RiskScore:
        a = analysis or self._analysis.analyse(inp)
        d = drawdown or self._drawdown.evaluate(inp)
        s = stress   or self._stress.run(inp)

        w = RiskScore._WEIGHTS
        # Include stress as 15% if available, redistributing from market
        overall = clamp(
            w["market"]    * a.market.overall_market_risk
            + w["model"]   * a.model.overall_model_risk
            + w["drawdown"] * d.overall_drawdown_risk_score
            + w["liquidity"] * a.liquidity.overall_liquidity_risk
            + w["execution"] * a.execution.overall_execution_risk
        )

        # Stress nudge: if aggregate stress > overall, pull up slightly
        if s.aggregate_stress_score > overall:
            overall = clamp(0.85 * overall + 0.15 * s.aggregate_stress_score)

        grade = _grade(overall)
        return RiskScore(
            strategy_id=inp.strategy_id,
            market_risk_score=a.market.overall_market_risk,
            execution_risk_score=a.execution.overall_execution_risk,
            liquidity_risk_score=a.liquidity.overall_liquidity_risk,
            model_risk_score=a.model.overall_model_risk,
            drawdown_risk_score=d.overall_drawdown_risk_score,
            stress_risk_score=s.aggregate_stress_score,
            overall_risk_score=overall,
            risk_grade=grade,
            is_acceptable=overall <= self._threshold,
        )
