"""iios/investment/portfolio/risk/drawdown_analysis.py

NEW comprehensive drawdown analysis module (separate from the existing
drawdown_engine.py which is retained for backward compat).

Uses vol-based maximum drawdown approximation and position-level risk.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.risk.risk_types import (
    DrawdownLevel, RiskPosition, drawdown_to_level,
    portfolio_volatility, TRADING_DAYS,
)


# Max drawdown approximation for T trading days:  MaxDD ≈ σ × √(2 ln T) / √T
# For T=252: σ_daily × √(2 × ln(252)) × (1/√252) but for annual vol it is:
#   MaxDD ≈ σ_annual × √(2 ln T / T)


def _max_dd_proxy(annual_vol: float, trading_days: int = 252) -> float:
    """Hull-White maximum drawdown proxy using annual volatility."""
    if annual_vol <= 0 or trading_days <= 1:
        return 0.0
    # MaxDD ≈ σ × sqrt(2 × ln(T) / T)  — typical MDD formula
    return annual_vol * math.sqrt(2.0 * math.log(trading_days) / trading_days) * math.sqrt(trading_days)


@dataclass(frozen=True)
class DrawdownAnalysisResult:
    """Comprehensive drawdown analysis result."""

    result_id:              str          = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:           str          = ""

    # Drawdown proxies (as fraction of portfolio)
    max_drawdown_proxy:     float        = 0.0   # MaxDD over ~1yr
    expected_drawdown:      float        = 0.0   # E[MaxDD] over 252 days
    expected_drawdown_90d:  float        = 0.0
    avg_drawdown_proxy:     float        = 0.0   # ≈ 0.5 × MaxDD
    current_drawdown_proxy: float        = 0.0   # proxy (no actual NAV series)

    # Recovery proxy
    expected_recovery_days: int          = 0

    # Calmar proxy: annual return / MaxDD (higher = better)
    calmar_proxy:           float        = 0.0

    # Vol-of-vol proxy (dispersion of risk_scores)
    vol_of_vol_proxy:       float        = 0.0

    drawdown_level:         DrawdownLevel = DrawdownLevel.NONE
    warnings:               tuple        = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_drawdown_proxy":    round(self.max_drawdown_proxy, 4),
            "expected_drawdown":     round(self.expected_drawdown, 4),
            "avg_drawdown_proxy":    round(self.avg_drawdown_proxy, 4),
            "expected_recovery_days": self.expected_recovery_days,
            "calmar_proxy":          round(self.calmar_proxy, 4),
            "vol_of_vol_proxy":      round(self.vol_of_vol_proxy, 4),
            "drawdown_level":        self.drawdown_level.value,
            "warnings":              list(self.warnings),
        }


def analyze_drawdown(
    positions:    List[RiskPosition],
    portfolio_id: str = "",
    nav_series:   Optional[List[float]] = None,
) -> DrawdownAnalysisResult:
    if not positions:
        return DrawdownAnalysisResult(portfolio_id=portfolio_id)

    port_vol = portfolio_volatility(positions)
    annual_vol = port_vol * math.sqrt(TRADING_DAYS)

    max_dd    = _max_dd_proxy(annual_vol, TRADING_DAYS)
    max_dd_90 = _max_dd_proxy(annual_vol, 90)
    avg_dd    = max_dd * 0.5

    # Recovery proxy: time = MaxDD² / (2 × daily_vol²) under Brownian motion
    daily_vol = port_vol
    recovery_days = int(max_dd ** 2 / (2.0 * daily_vol ** 2)) if daily_vol > 0 else 0
    recovery_days = min(recovery_days, 500)

    # Calmar proxy: assume expected annual return ≈ annual_vol × Sharpe=0.7
    expected_annual_return = annual_vol * 0.7
    calmar = expected_annual_return / max_dd if max_dd > 0 else 0.0

    # Vol-of-vol proxy: std dev of risk_scores across positions
    if len(positions) > 1:
        mean_rs = sum(p.risk_score for p in positions) / len(positions)
        vov = math.sqrt(
            sum((p.risk_score - mean_rs) ** 2 for p in positions) / len(positions)
        )
    else:
        vov = 0.0

    dd_level = drawdown_to_level(max_dd)

    warnings = []
    if max_dd >= 0.30:
        warnings.append(f"Expected max drawdown {max_dd:.1%} — extreme risk")
    elif max_dd >= 0.20:
        warnings.append(f"Expected max drawdown {max_dd:.1%} — severe risk")
    elif max_dd >= 0.10:
        warnings.append(f"Expected max drawdown {max_dd:.1%} — moderate drawdown risk")
    if recovery_days >= 120:
        warnings.append(f"Estimated recovery time ~{recovery_days} days")

    return DrawdownAnalysisResult(
        portfolio_id           = portfolio_id,
        max_drawdown_proxy     = round(max_dd, 6),
        expected_drawdown      = round(max_dd * 0.75, 6),
        expected_drawdown_90d  = round(max_dd_90, 6),
        avg_drawdown_proxy     = round(avg_dd, 6),
        current_drawdown_proxy = 0.0,
        expected_recovery_days = recovery_days,
        calmar_proxy           = round(calmar, 4),
        vol_of_vol_proxy       = round(vov, 4),
        drawdown_level         = dd_level,
        warnings               = tuple(warnings),
    )
