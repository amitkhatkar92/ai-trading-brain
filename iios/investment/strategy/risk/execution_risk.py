"""iios/investment/strategy/risk/execution_risk.py
ExecutionRiskAnalyzer — evaluates strategy-specific execution risks.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from iios.investment.strategy.risk.risk_input import StrategyRiskInput
from iios.investment.strategy.risk.risk_statistics import clamp, vol_risk_score

# Asset-type base slippage (bps → 0-100 scale)
_ASSET_SLIPPAGE: Dict[str, float] = {
    "equity":    15.0,
    "etf":       10.0,
    "futures":   20.0,
    "options":   55.0,
    "forex":     10.0,
    "crypto":    50.0,
    "commodity": 35.0,
}

# Timeframe execution pressure
_TF_EXEC_PRESSURE: Dict[str, float] = {
    "tick":      90.0,
    "intraday":  60.0,
    "daily":     25.0,
    "weekly":    15.0,
    "monthly":   10.0,
}

# Strategy tag complexity multipliers
_TAG_COMPLEXITY: Dict[str, float] = {
    "high_frequency": 80.0,
    "hft":            80.0,
    "market_making":  70.0,
    "arbitrage":      50.0,
    "momentum":       20.0,
    "trend":          20.0,
    "mean_reversion": 25.0,
    "volatility":     40.0,
    "income":         10.0,
    "dividend":       10.0,
}


@dataclass(frozen=True)
class ExecutionRiskResult:
    """
    Decomposed execution risk scores.
    All scores in [0, 100].
    """
    strategy_id:    str

    slippage_risk:  float   # cost of entering/exiting position
    timing_risk:    float   # precision-required timing risk
    fill_risk:      float   # risk of incomplete / partial fills
    complexity_risk: float  # operational complexity of strategy execution

    overall_execution_risk: float

    @property
    def grade(self) -> str:
        s = self.overall_execution_risk
        if s <= 20: return "A"
        if s <= 40: return "B"
        if s <= 60: return "C"
        if s <= 80: return "D"
        return "F"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":      self.strategy_id,
            "slippage_risk":    round(self.slippage_risk, 2),
            "timing_risk":      round(self.timing_risk, 2),
            "fill_risk":        round(self.fill_risk, 2),
            "complexity_risk":  round(self.complexity_risk, 2),
            "overall_execution_risk": round(self.overall_execution_risk, 2),
            "grade":            self.grade,
        }


class ExecutionRiskAnalyzer:
    """Computes execution risk from strategy input metadata."""

    def analyse(self, inp: StrategyRiskInput) -> ExecutionRiskResult:
        slippage = self._slippage_risk(inp)
        timing   = self._timing_risk(inp)
        fill     = self._fill_risk(inp, slippage)
        complexity = self._complexity_risk(inp)

        overall = clamp(
            0.35 * slippage
            + 0.30 * timing
            + 0.20 * fill
            + 0.15 * complexity
        )
        return ExecutionRiskResult(
            strategy_id=inp.strategy_id,
            slippage_risk=slippage,
            timing_risk=timing,
            fill_risk=fill,
            complexity_risk=complexity,
            overall_execution_risk=overall,
        )

    def _slippage_risk(self, inp: StrategyRiskInput) -> float:
        scores = [_ASSET_SLIPPAGE.get(a, 20.0) for a in inp.asset_types] or [20.0]
        base = sum(scores) / len(scores)
        # Higher vol → more slippage
        vol_adj = vol_risk_score(inp.annualized_vol) * 0.30
        return clamp(base + vol_adj)

    def _timing_risk(self, inp: StrategyRiskInput) -> float:
        scores = [_TF_EXEC_PRESSURE.get(tf, 25.0) for tf in inp.supported_timeframes] or [25.0]
        return clamp(sum(scores) / len(scores))

    def _fill_risk(self, inp: StrategyRiskInput, slippage_risk: float) -> float:
        # Higher slippage assets also have worse fill quality
        return clamp(slippage_risk * 0.70)

    def _complexity_risk(self, inp: StrategyRiskInput) -> float:
        tag_scores = [_TAG_COMPLEXITY.get(t, 20.0) for t in inp.tags] or [20.0]
        return clamp(max(tag_scores))
