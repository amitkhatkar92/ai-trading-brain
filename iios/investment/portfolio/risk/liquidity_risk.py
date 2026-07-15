"""iios/investment/portfolio/risk/liquidity_risk.py

Liquidity risk analysis: bid-ask spread proxies, illiquid position weight,
liquidity-adjusted VaR.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.risk.risk_types import (
    ILLIQUID_WEIGHT_CRITICAL, ILLIQUID_WEIGHT_WARNING,
    LIQUIDITY_CRITICAL_THRESHOLD, LIQUIDITY_LOW_THRESHOLD,
    NORMAL_Z_95, RiskLevel, TRADING_DAYS,
    portfolio_volatility, var_parametric, weighted_average,
    risk_score_to_level, RiskPosition,
)
import math


@dataclass(frozen=True)
class LiquidityRiskResult:
    """Liquidity risk measures for a portfolio."""

    result_id:               str       = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:            str       = ""

    # Liquidity scores
    avg_liquidity_score:     float     = 0.0
    min_liquidity_score:     float     = 0.0
    portfolio_liquidity_hhi: float     = 0.0   # concentration in illiquid assets

    # Illiquid exposure (liquidity < 0.30)
    illiquid_weight:         float     = 0.0
    semi_liquid_weight:      float     = 0.0   # liquidity 0.30-0.60
    liquid_weight:           float     = 0.0

    # Liquidity-adjusted VaR (LVAR)
    lvar_95_1d:              float     = 0.0   # base VaR + liquidation cost
    liquidation_cost_proxy:  float     = 0.0   # half-spread × illiquid_weight

    # Worst case: days-to-liquidate proxy
    estimated_days_to_liquidate: float = 1.0

    risk_level:              RiskLevel = RiskLevel.LOW
    warnings:                tuple     = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "avg_liquidity_score":     round(self.avg_liquidity_score, 4),
            "min_liquidity_score":     round(self.min_liquidity_score, 4),
            "illiquid_weight":         round(self.illiquid_weight, 4),
            "lvar_95_1d":              round(self.lvar_95_1d, 4),
            "liquidation_cost_proxy":  round(self.liquidation_cost_proxy, 4),
            "estimated_days_to_liquidate": round(self.estimated_days_to_liquidate, 2),
            "risk_level":              self.risk_level.value,
            "warnings":                list(self.warnings),
        }


def analyze_liquidity_risk(
    positions:    List[RiskPosition],
    portfolio_id: str = "",
) -> LiquidityRiskResult:
    if not positions:
        return LiquidityRiskResult(portfolio_id=portfolio_id)

    avg_liq = weighted_average(positions, "liquidity")
    min_liq = min(p.liquidity for p in positions)

    illiquid_w    = sum(p.weight for p in positions if p.liquidity < 0.30)
    semi_liquid_w = sum(p.weight for p in positions if 0.30 <= p.liquidity < 0.60)
    liquid_w      = sum(p.weight for p in positions if p.liquidity >= 0.60)

    # HHI of illiquidity exposure
    liq_hhi = sum(
        (p.weight * (1.0 - p.liquidity)) ** 2 for p in positions
    )

    # Liquidation cost proxy: illiquid positions cost ~2% to liquidate
    liq_cost = illiquid_w * 0.02 + semi_liquid_w * 0.005

    # LVAR = base VaR + liquidation cost
    port_vol = portfolio_volatility(positions)
    base_var = var_parametric(port_vol, NORMAL_Z_95, 1)
    lvar = base_var + liq_cost

    # Days to liquidate proxy: higher illiquid weight → more days
    days_to_liq = 1.0 + illiquid_w * 9.0 + semi_liquid_w * 2.0

    # Risk level: driven by illiquid weight and avg liquidity
    raw_risk = illiquid_w * 0.7 + (1.0 - avg_liq) * 0.3
    risk_level = risk_score_to_level(raw_risk)

    warnings = []
    if avg_liq < LIQUIDITY_CRITICAL_THRESHOLD:
        warnings.append(f"Critical average liquidity score {avg_liq:.2f}")
    elif avg_liq < LIQUIDITY_LOW_THRESHOLD:
        warnings.append(f"Low average liquidity score {avg_liq:.2f}")
    if illiquid_w >= ILLIQUID_WEIGHT_CRITICAL:
        warnings.append(f"Critical illiquid weight {illiquid_w:.1%}")
    elif illiquid_w >= ILLIQUID_WEIGHT_WARNING:
        warnings.append(f"Elevated illiquid weight {illiquid_w:.1%}")

    return LiquidityRiskResult(
        portfolio_id                = portfolio_id,
        avg_liquidity_score         = round(avg_liq, 4),
        min_liquidity_score         = round(min_liq, 4),
        portfolio_liquidity_hhi     = round(liq_hhi, 4),
        illiquid_weight             = round(illiquid_w, 4),
        semi_liquid_weight          = round(semi_liquid_w, 4),
        liquid_weight               = round(liquid_w, 4),
        lvar_95_1d                  = round(lvar, 6),
        liquidation_cost_proxy      = round(liq_cost, 4),
        estimated_days_to_liquidate = round(days_to_liq, 2),
        risk_level                  = risk_level,
        warnings                    = tuple(warnings),
    )
