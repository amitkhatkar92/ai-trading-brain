"""iios/investment/portfolio/risk/recovery_analysis.py

Recovery analysis: expected time to recover from a drawdown.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.risk.risk_types import (
    RiskPosition, portfolio_volatility, TRADING_DAYS,
)


@dataclass(frozen=True)
class RecoveryAnalysis:
    """Recovery time and probability analysis after drawdowns."""

    result_id:               str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:            str   = ""

    # Expected recovery from typical (avg) drawdown
    expected_recovery_days:   int  = 0

    # Recovery from severe drawdown (20%)
    recovery_days_from_20pct: int  = 0
    recovery_days_from_30pct: int  = 0

    # Probability of recovering within N days (from a 10% drawdown)
    recovery_prob_30d:        float = 0.0
    recovery_prob_60d:        float = 0.0
    recovery_prob_90d:        float = 0.0

    # Recovery trajectory: "fast" / "moderate" / "slow"
    recovery_trajectory:      str  = "moderate"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "expected_recovery_days":   self.expected_recovery_days,
            "recovery_days_from_20pct": self.recovery_days_from_20pct,
            "recovery_days_from_30pct": self.recovery_days_from_30pct,
            "recovery_prob_30d":        round(self.recovery_prob_30d, 4),
            "recovery_prob_60d":        round(self.recovery_prob_60d, 4),
            "recovery_prob_90d":        round(self.recovery_prob_90d, 4),
            "recovery_trajectory":      self.recovery_trajectory,
        }


def _recovery_days(drawdown: float, daily_vol: float) -> int:
    """Expected recovery days under Brownian motion: T = DD² / (2 × σ²)."""
    if daily_vol <= 0 or drawdown <= 0:
        return 0
    return int(min(1000, (drawdown ** 2) / (2.0 * daily_vol ** 2)))


def _recovery_prob_within(
    drawdown: float, daily_vol: float, horizon_days: int
) -> float:
    """P(recover within horizon) ≈ erfc(drawdown / sqrt(2 × σ² × T))."""
    if daily_vol <= 0 or horizon_days <= 0 or drawdown <= 0:
        return 0.0
    sigma_sqrt_t = daily_vol * math.sqrt(horizon_days)
    z = drawdown / sigma_sqrt_t
    return round(max(0.0, min(1.0, 1.0 - math.erf(z / math.sqrt(2.0)))), 6)


def analyze_recovery(
    positions:    List[RiskPosition],
    portfolio_id: str = "",
    reference_drawdown: float = 0.10,   # default 10% reference loss
) -> RecoveryAnalysis:
    if not positions:
        return RecoveryAnalysis(portfolio_id=portfolio_id)

    port_vol  = portfolio_volatility(positions)   # daily vol
    ann_vol   = port_vol * math.sqrt(TRADING_DAYS)

    avg_dd   = ann_vol * 0.40   # typical avg drawdown proxy
    exp_days = _recovery_days(avg_dd, port_vol)
    days_20  = _recovery_days(0.20, port_vol)
    days_30  = _recovery_days(0.30, port_vol)

    p30  = _recovery_prob_within(reference_drawdown, port_vol, 30)
    p60  = _recovery_prob_within(reference_drawdown, port_vol, 60)
    p90  = _recovery_prob_within(reference_drawdown, port_vol, 90)

    if exp_days <= 30:
        trajectory = "fast"
    elif exp_days <= 90:
        trajectory = "moderate"
    else:
        trajectory = "slow"

    return RecoveryAnalysis(
        portfolio_id             = portfolio_id,
        expected_recovery_days   = exp_days,
        recovery_days_from_20pct = days_20,
        recovery_days_from_30pct = days_30,
        recovery_prob_30d        = p30,
        recovery_prob_60d        = p60,
        recovery_prob_90d        = p90,
        recovery_trajectory      = trajectory,
    )
