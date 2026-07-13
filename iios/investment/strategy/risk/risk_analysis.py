"""iios/investment/strategy/risk/risk_analysis.py
RiskAnalysis — orchestrates all risk dimensions into a unified result.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.risk.risk_input import StrategyRiskInput
from iios.investment.strategy.risk.market_risk import MarketRiskAnalyzer, MarketRiskResult
from iios.investment.strategy.risk.execution_risk import ExecutionRiskAnalyzer, ExecutionRiskResult
from iios.investment.strategy.risk.liquidity_risk import LiquidityRiskAnalyzer, LiquidityRiskResult
from iios.investment.strategy.risk.model_risk import ModelRiskAnalyzer, ModelRiskResult
from iios.investment.strategy.risk.risk_statistics import (
    clamp, expected_daily_loss, expected_weekly_loss, expected_monthly_loss
)


@dataclass(frozen=True)
class RiskAnalysisResult:
    """
    Complete risk analysis decomposition for a single strategy.
    All risk scores in [0, 100]; 0 = minimum risk, 100 = maximum risk.
    """
    strategy_id: str

    market:    MarketRiskResult
    execution: ExecutionRiskResult
    liquidity: LiquidityRiskResult
    model:     ModelRiskResult

    # Composite
    composite_risk_score: float

    # Expected loss estimates (fraction of capital)
    expected_daily_loss_95:   float
    expected_weekly_loss_95:  float
    expected_monthly_loss_95: float

    # Convenience
    risk_factors: List[str]    # top-3 highest-risk dimensions
    analysed_at:  datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def grade(self) -> str:
        s = self.composite_risk_score
        if s <= 20: return "A"
        if s <= 40: return "B"
        if s <= 60: return "C"
        if s <= 80: return "D"
        return "F"

    @property
    def is_high_risk(self) -> bool:
        return self.composite_risk_score > 60.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":            self.strategy_id,
            "composite_risk_score":   round(self.composite_risk_score, 2),
            "grade":                  self.grade,
            "is_high_risk":           self.is_high_risk,
            "market":                 self.market.to_dict(),
            "execution":              self.execution.to_dict(),
            "liquidity":              self.liquidity.to_dict(),
            "model":                  self.model.to_dict(),
            "expected_daily_loss_95":   round(self.expected_daily_loss_95, 6),
            "expected_weekly_loss_95":  round(self.expected_weekly_loss_95, 6),
            "expected_monthly_loss_95": round(self.expected_monthly_loss_95, 6),
            "risk_factors":           self.risk_factors,
            "analysed_at":            self.analysed_at.isoformat(),
        }


class RiskAnalysis:
    """
    Orchestrates all four risk analyzers and produces RiskAnalysisResult.
    Weights:
        Market    35%
        Model     30%
        Liquidity 20%
        Execution 15%
    """
    _WEIGHTS = {
        "market":    0.35,
        "model":     0.30,
        "liquidity": 0.20,
        "execution": 0.15,
    }

    def __init__(
        self,
        market_analyzer:    Optional[MarketRiskAnalyzer]    = None,
        execution_analyzer: Optional[ExecutionRiskAnalyzer] = None,
        liquidity_analyzer: Optional[LiquidityRiskAnalyzer] = None,
        model_analyzer:     Optional[ModelRiskAnalyzer]     = None,
    ) -> None:
        self._market    = market_analyzer    or MarketRiskAnalyzer()
        self._execution = execution_analyzer or ExecutionRiskAnalyzer()
        self._liquidity = liquidity_analyzer or LiquidityRiskAnalyzer()
        self._model     = model_analyzer     or ModelRiskAnalyzer()

    def analyse(self, inp: StrategyRiskInput) -> RiskAnalysisResult:
        market    = self._market.analyse(inp)
        execution = self._execution.analyse(inp)
        liquidity = self._liquidity.analyse(inp)
        model     = self._model.analyse(inp)

        w = self._WEIGHTS
        composite = clamp(
            w["market"]    * market.overall_market_risk
            + w["model"]   * model.overall_model_risk
            + w["liquidity"] * liquidity.overall_liquidity_risk
            + w["execution"] * execution.overall_execution_risk
        )

        # Top risk contributors
        scored = {
            "Market":    market.overall_market_risk,
            "Model":     model.overall_model_risk,
            "Liquidity": liquidity.overall_liquidity_risk,
            "Execution": execution.overall_execution_risk,
        }
        risk_factors = sorted(scored, key=scored.get, reverse=True)[:3]  # type: ignore[arg-type]

        return RiskAnalysisResult(
            strategy_id=inp.strategy_id,
            market=market,
            execution=execution,
            liquidity=liquidity,
            model=model,
            composite_risk_score=composite,
            expected_daily_loss_95=expected_daily_loss(inp.annualized_vol),
            expected_weekly_loss_95=expected_weekly_loss(inp.annualized_vol),
            expected_monthly_loss_95=expected_monthly_loss(inp.annualized_vol),
            risk_factors=risk_factors,
        )
