"""iios/investment/portfolio/risk/market_risk.py

Market risk analysis: volatility, VaR, CVaR, beta, diversification benefit.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.risk.risk_types import (
    NORMAL_Z_95, NORMAL_Z_99,
    VAR_95_1D_WARNING, VAR_95_1D_CRITICAL, VOL_HIGH, VOL_VERY_HIGH,
    RiskLevel, TRADING_DAYS,
    cvar_parametric, portfolio_volatility, risk_score_to_level,
    var_parametric, weighted_average, RiskPosition,
)


@dataclass(frozen=True)
class MarketRiskResult:
    """Comprehensive market risk metrics for a portfolio snapshot."""

    result_id:               str       = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:            str       = ""
    n_positions:             int       = 0

    # Volatility
    portfolio_vol_annual:    float     = 0.0   # σ_p annual
    portfolio_vol_daily:     float     = 0.0   # σ_p daily
    weighted_avg_vol_annual: float     = 0.0   # Σ w_i * σ_i  (undiversified)

    # VaR / CVaR (as fraction of portfolio value)
    var_95_1d:               float     = 0.0
    var_99_1d:               float     = 0.0
    var_95_10d:              float     = 0.0
    var_99_10d:              float     = 0.0
    cvar_95_1d:              float     = 0.0   # Expected Shortfall

    # Decomposition
    systematic_risk:         float     = 0.0   # undiversified component
    diversification_benefit: float     = 0.0   # 1 - σ_p / Σw_iσ_i
    beta_proxy:              float     = 1.0   # weighted risk_score / market baseline

    # Classification
    risk_level:              RiskLevel = RiskLevel.MODERATE
    is_elevated:             bool      = False
    warnings:                tuple     = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_vol_annual":    round(self.portfolio_vol_annual, 4),
            "portfolio_vol_daily":     round(self.portfolio_vol_daily, 6),
            "weighted_avg_vol_annual": round(self.weighted_avg_vol_annual, 4),
            "var_95_1d":               round(self.var_95_1d, 4),
            "var_99_1d":               round(self.var_99_1d, 4),
            "var_95_10d":              round(self.var_95_10d, 4),
            "cvar_95_1d":              round(self.cvar_95_1d, 4),
            "systematic_risk":         round(self.systematic_risk, 4),
            "diversification_benefit": round(self.diversification_benefit, 4),
            "beta_proxy":              round(self.beta_proxy, 4),
            "risk_level":              self.risk_level.value,
            "is_elevated":             self.is_elevated,
            "warnings":                list(self.warnings),
        }


def analyze_market_risk(
    positions:    List[RiskPosition],
    portfolio_id: str = "",
) -> MarketRiskResult:
    """Compute market risk metrics for a list of positions."""
    if not positions:
        return MarketRiskResult(portfolio_id=portfolio_id)

    port_vol       = portfolio_volatility(positions)
    port_vol_daily = port_vol / math.sqrt(TRADING_DAYS)
    w_avg_vol      = weighted_average(positions, "annual_volatility")

    # Diversification benefit: σ_p < Σw_iσ_i
    div_benefit = max(0.0, 1.0 - port_vol / w_avg_vol) if w_avg_vol > 1e-10 else 0.0

    # Parametric VaR / CVaR
    v95   = var_parametric(port_vol, NORMAL_Z_95, 1)
    v99   = var_parametric(port_vol, NORMAL_Z_99, 1)
    v95_10= var_parametric(port_vol, NORMAL_Z_95, 10)
    v99_10= var_parametric(port_vol, NORMAL_Z_99, 10)
    es95  = cvar_parametric(port_vol, NORMAL_Z_95, 1)

    # Systematic risk proxy = weighted avg vol (undiversified)
    systematic = w_avg_vol

    # Beta proxy: avg risk_score relative to market baseline (0.25 = "market")
    avg_risk = weighted_average(positions, "risk_score")
    beta_proxy = avg_risk / 0.25 if avg_risk > 0 else 1.0

    # Classification
    normalised = min(1.0, port_vol / 0.60)
    risk_level = risk_score_to_level(normalised)
    is_elevated = v95 >= VAR_95_1D_WARNING

    warnings = []
    if v95 >= VAR_95_1D_CRITICAL:
        warnings.append(f"Critical 1-day 95% VaR at {v95:.1%}")
    elif v95 >= VAR_95_1D_WARNING:
        warnings.append(f"Elevated 1-day 95% VaR at {v95:.1%}")
    if port_vol >= VOL_VERY_HIGH:
        warnings.append(f"Extreme portfolio volatility {port_vol:.1%} annual")
    elif port_vol >= VOL_HIGH:
        warnings.append(f"High portfolio volatility {port_vol:.1%} annual")
    if div_benefit < 0.05:
        warnings.append("Minimal diversification benefit — positions highly correlated")
    if beta_proxy > 1.50:
        warnings.append(f"High market sensitivity (beta proxy {beta_proxy:.2f})")

    return MarketRiskResult(
        portfolio_id            = portfolio_id,
        n_positions             = len(positions),
        portfolio_vol_annual    = round(port_vol, 6),
        portfolio_vol_daily     = round(port_vol_daily, 6),
        weighted_avg_vol_annual = round(w_avg_vol, 6),
        var_95_1d               = round(v95, 6),
        var_99_1d               = round(v99, 6),
        var_95_10d              = round(v95_10, 6),
        var_99_10d              = round(v99_10, 6),
        cvar_95_1d              = round(es95, 6),
        systematic_risk         = round(systematic, 6),
        diversification_benefit = round(div_benefit, 6),
        beta_proxy              = round(beta_proxy, 4),
        risk_level              = risk_level,
        is_elevated             = is_elevated,
        warnings                = tuple(warnings),
    )
