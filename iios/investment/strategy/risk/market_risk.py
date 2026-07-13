"""iios/investment/strategy/risk/market_risk.py
MarketRiskAnalyzer — evaluates market-facing risk dimensions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from iios.investment.strategy.risk.risk_input import StrategyRiskInput
from iios.investment.strategy.risk.risk_statistics import (
    clamp, vol_risk_score, drawdown_risk_score, tail_risk_score,
    regime_mismatch_penalty, vol_level_penalty
)

# Asset-type gap risk multipliers
_ASSET_GAP_RISK: Dict[str, float] = {
    "equity":    30.0,
    "etf":       20.0,
    "futures":   50.0,
    "options":   70.0,
    "forex":     20.0,
    "crypto":    80.0,
    "commodity": 40.0,
}

# Timeframe intraday risk multipliers
_TF_EXECUTION_MULT: Dict[str, float] = {
    "tick":      1.0,
    "intraday":  0.8,
    "daily":     0.4,
    "weekly":    0.2,
    "monthly":   0.1,
}


@dataclass(frozen=True)
class MarketRiskResult:
    """
    Decomposed market risk scores for a strategy.
    All scores in [0, 100] where 100 = maximum risk.
    """
    strategy_id:       str

    vol_risk:          float   # volatility risk
    drawdown_risk:     float   # historical drawdown depth risk
    tail_risk:         float   # extreme-event / tail risk
    regime_risk:       float   # regime mismatch risk
    gap_risk:          float   # overnight / gap risk
    volatility_regime_risk: float  # ambient market-vol-level risk

    overall_market_risk: float  # weighted composite

    @property
    def grade(self) -> str:
        s = self.overall_market_risk
        if s <= 20: return "A"
        if s <= 40: return "B"
        if s <= 60: return "C"
        if s <= 80: return "D"
        return "F"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":      self.strategy_id,
            "vol_risk":         round(self.vol_risk, 2),
            "drawdown_risk":    round(self.drawdown_risk, 2),
            "tail_risk":        round(self.tail_risk, 2),
            "regime_risk":      round(self.regime_risk, 2),
            "gap_risk":         round(self.gap_risk, 2),
            "volatility_regime_risk": round(self.volatility_regime_risk, 2),
            "overall_market_risk":    round(self.overall_market_risk, 2),
            "grade":            self.grade,
        }


class MarketRiskAnalyzer:
    """
    Computes market risk dimensions from StrategyRiskInput.
    Consumes pre-computed evaluation metrics — does not re-evaluate strategies.
    """

    def analyse(self, inp: StrategyRiskInput) -> MarketRiskResult:
        vol_risk  = vol_risk_score(inp.annualized_vol)
        dd_risk   = drawdown_risk_score(inp.max_drawdown)
        t_risk    = tail_risk_score(inp.max_drawdown, inp.win_rate)
        reg_risk  = regime_mismatch_penalty(inp.regime_mismatch)
        gap_risk  = self._gap_risk(inp)
        vr_risk   = vol_level_penalty(inp.current_volatility_level)

        overall = clamp(
            0.25 * vol_risk
            + 0.20 * dd_risk
            + 0.20 * t_risk
            + 0.15 * reg_risk
            + 0.10 * gap_risk
            + 0.10 * vr_risk
        )

        return MarketRiskResult(
            strategy_id=inp.strategy_id,
            vol_risk=vol_risk,
            drawdown_risk=dd_risk,
            tail_risk=t_risk,
            regime_risk=reg_risk,
            gap_risk=gap_risk,
            volatility_regime_risk=vr_risk,
            overall_market_risk=overall,
        )

    def _gap_risk(self, inp: StrategyRiskInput) -> float:
        asset_scores = [_ASSET_GAP_RISK.get(a, 30.0) for a in inp.asset_types] or [30.0]
        avg_asset = sum(asset_scores) / len(asset_scores)
        # Intraday strategies have lower gap exposure
        tf_scores = [_TF_EXECUTION_MULT.get(tf, 0.4) for tf in inp.supported_timeframes] or [0.4]
        tf_mult = sum(tf_scores) / len(tf_scores)
        return clamp(avg_asset * tf_mult)
