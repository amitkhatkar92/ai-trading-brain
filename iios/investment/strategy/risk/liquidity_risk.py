"""iios/investment/strategy/risk/liquidity_risk.py
LiquidityRiskAnalyzer — evaluates strategy-specific liquidity risks.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from iios.investment.strategy.risk.risk_input import StrategyRiskInput
from iios.investment.strategy.risk.risk_statistics import clamp

_ASSET_LIQUIDITY: Dict[str, float] = {
    "equity":     20.0,
    "etf":        15.0,
    "futures":    25.0,
    "options":    55.0,
    "forex":      10.0,
    "crypto":     60.0,
    "commodity":  40.0,
}

_SECTOR_LIQUIDITY: Dict[str, float] = {
    "technology":   10.0,
    "finance":      10.0,
    "consumer":     20.0,
    "healthcare":   20.0,
    "energy":       25.0,
    "utilities":    30.0,
    "real_estate":  40.0,
    "materials":    35.0,
    "industrial":   25.0,
}

_MARKET_LIQUIDITY_PENALTY: Dict[str, float] = {
    "high":   0.0,
    "normal": 10.0,
    "low":    40.0,
}


@dataclass(frozen=True)
class LiquidityRiskResult:
    """
    Decomposed liquidity risk scores.  All in [0, 100].
    """
    strategy_id: str

    asset_liquidity_risk:   float   # based on asset class
    sector_liquidity_risk:  float   # based on sector
    market_liquidity_risk:  float   # ambient market liquidity conditions
    spread_risk:            float   # bid-ask spread sensitivity
    depth_risk:             float   # market depth / impact risk

    overall_liquidity_risk: float

    @property
    def grade(self) -> str:
        s = self.overall_liquidity_risk
        if s <= 20: return "A"
        if s <= 40: return "B"
        if s <= 60: return "C"
        if s <= 80: return "D"
        return "F"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":          self.strategy_id,
            "asset_liquidity_risk": round(self.asset_liquidity_risk, 2),
            "sector_liquidity_risk": round(self.sector_liquidity_risk, 2),
            "market_liquidity_risk": round(self.market_liquidity_risk, 2),
            "spread_risk":          round(self.spread_risk, 2),
            "depth_risk":           round(self.depth_risk, 2),
            "overall_liquidity_risk": round(self.overall_liquidity_risk, 2),
            "grade":                self.grade,
        }


class LiquidityRiskAnalyzer:
    """Computes liquidity risk from strategy input metadata."""

    def analyse(self, inp: StrategyRiskInput) -> LiquidityRiskResult:
        asset_liq  = self._asset_liquidity(inp)
        sector_liq = self._sector_liquidity(inp)
        mkt_liq    = _MARKET_LIQUIDITY_PENALTY.get(inp.market_liquidity, 10.0)
        spread     = clamp(asset_liq * 0.80)
        depth      = clamp(asset_liq * 0.60 + sector_liq * 0.40)

        overall = clamp(
            0.30 * asset_liq
            + 0.20 * sector_liq
            + 0.20 * mkt_liq
            + 0.15 * spread
            + 0.15 * depth
        )
        return LiquidityRiskResult(
            strategy_id=inp.strategy_id,
            asset_liquidity_risk=asset_liq,
            sector_liquidity_risk=sector_liq,
            market_liquidity_risk=mkt_liq,
            spread_risk=spread,
            depth_risk=depth,
            overall_liquidity_risk=overall,
        )

    def _asset_liquidity(self, inp: StrategyRiskInput) -> float:
        scores = [_ASSET_LIQUIDITY.get(a, 25.0) for a in inp.asset_types] or [25.0]
        return clamp(sum(scores) / len(scores))

    def _sector_liquidity(self, inp: StrategyRiskInput) -> float:
        if not inp.sectors:
            return 20.0
        scores = [_SECTOR_LIQUIDITY.get(s, 25.0) for s in inp.sectors]
        return clamp(sum(scores) / len(scores))
