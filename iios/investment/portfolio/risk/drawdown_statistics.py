"""iios/investment/portfolio/risk/drawdown_statistics.py

Drawdown distribution statistics: percentile drawdown estimates.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.risk.risk_types import (
    NORMAL_Z_95, NORMAL_Z_99, RiskPosition, portfolio_volatility, TRADING_DAYS,
)


@dataclass(frozen=True)
class DrawdownDistribution:
    """Percentile-based drawdown distribution from vol scaling."""

    result_id:   str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id: str  = ""

    # Percentile drawdown estimates (as fraction of portfolio)
    p50_drawdown:  float = 0.0   # median maximum drawdown over horizon
    p75_drawdown:  float = 0.0
    p90_drawdown:  float = 0.0
    p95_drawdown:  float = 0.0
    p99_drawdown:  float = 0.0

    # Expected shortfall beyond p99
    expected_tail_drawdown: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "p50_drawdown":          round(self.p50_drawdown, 4),
            "p75_drawdown":          round(self.p75_drawdown, 4),
            "p90_drawdown":          round(self.p90_drawdown, 4),
            "p95_drawdown":          round(self.p95_drawdown, 4),
            "p99_drawdown":          round(self.p99_drawdown, 4),
            "expected_tail_drawdown":round(self.expected_tail_drawdown, 4),
        }


def compute_drawdown_distribution(
    positions:    List[RiskPosition],
    portfolio_id: str  = "",
    horizon_days: int  = 252,
) -> DrawdownDistribution:
    if not positions:
        return DrawdownDistribution(portfolio_id=portfolio_id)

    port_vol  = portfolio_volatility(positions)
    ann_vol   = port_vol * math.sqrt(TRADING_DAYS)

    # Scale vol-based percentiles using normal quantiles as multipliers
    # P50 ≈ 0.6 × 1-sigma annual loss, P95 = 1.645-sigma, P99 = 2.326-sigma
    horizon_vol = ann_vol * math.sqrt(horizon_days / TRADING_DAYS)

    p50  = horizon_vol * 0.60
    p75  = horizon_vol * 0.85
    p90  = horizon_vol * 1.28
    p95  = horizon_vol * NORMAL_Z_95
    p99  = horizon_vol * NORMAL_Z_99
    tail = horizon_vol * 2.80   # ≈ 3-sigma

    return DrawdownDistribution(
        portfolio_id           = portfolio_id,
        p50_drawdown           = round(min(p50,  1.0), 6),
        p75_drawdown           = round(min(p75,  1.0), 6),
        p90_drawdown           = round(min(p90,  1.0), 6),
        p95_drawdown           = round(min(p95,  1.0), 6),
        p99_drawdown           = round(min(p99,  1.0), 6),
        expected_tail_drawdown = round(min(tail, 1.0), 6),
    )
