"""iios/investment/strategy/risk/risk_limits.py
RiskLimits — declarative thresholds for a strategy's permissible risk level.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class RiskLimits:
    """
    Risk limit profile for a strategy.
    All limits are max-allowed values.
    Loss limits are expressed as fractions of capital (e.g. 0.02 = 2%).
    """
    # Overall risk score ceiling
    max_risk_score:         float = 75.0   # 0-100 scale

    # Capital loss limits (fraction of capital per period)
    daily_loss_limit:       float = 0.02   # 2%
    weekly_loss_limit:      float = 0.05   # 5%
    monthly_loss_limit:     float = 0.10   # 10%

    # Drawdown limit
    max_drawdown_limit:     float = 0.20   # 20%

    # Volatility ceiling
    max_annualized_vol:     float = 0.40   # 40%

    # Exposure / allocation
    max_portfolio_weight:   float = 0.40   # 40% of portfolio
    max_leverage:           float = 2.0    # 2× leverage

    # Stress test requirement
    min_stress_pass_rate:   float = 0.50   # must pass at least 50% of scenarios
    max_aggregate_stress:   float = 70.0   # max allowed aggregate stress score

    # Stop conditions
    enable_emergency_stop:  bool  = True
    emergency_stop_score:   float = 90.0   # auto-disable above this risk score

    policy_name:            str   = "default"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_name":          self.policy_name,
            "max_risk_score":       self.max_risk_score,
            "daily_loss_limit":     self.daily_loss_limit,
            "weekly_loss_limit":    self.weekly_loss_limit,
            "monthly_loss_limit":   self.monthly_loss_limit,
            "max_drawdown_limit":   self.max_drawdown_limit,
            "max_annualized_vol":   self.max_annualized_vol,
            "max_portfolio_weight": self.max_portfolio_weight,
            "max_leverage":         self.max_leverage,
            "min_stress_pass_rate": self.min_stress_pass_rate,
            "max_aggregate_stress": self.max_aggregate_stress,
            "emergency_stop_score": self.emergency_stop_score,
        }


# ── Built-in limit profiles ───────────────────────────────────────────────────

DEFAULT_LIMITS = RiskLimits(policy_name="default")

CONSERVATIVE_LIMITS = RiskLimits(
    max_risk_score=55.0,
    daily_loss_limit=0.01,
    weekly_loss_limit=0.03,
    monthly_loss_limit=0.06,
    max_drawdown_limit=0.12,
    max_annualized_vol=0.20,
    max_portfolio_weight=0.25,
    max_leverage=1.0,
    min_stress_pass_rate=0.75,
    max_aggregate_stress=55.0,
    policy_name="conservative",
)

AGGRESSIVE_LIMITS = RiskLimits(
    max_risk_score=85.0,
    daily_loss_limit=0.04,
    weekly_loss_limit=0.10,
    monthly_loss_limit=0.20,
    max_drawdown_limit=0.35,
    max_annualized_vol=0.60,
    max_portfolio_weight=0.60,
    max_leverage=4.0,
    min_stress_pass_rate=0.25,
    max_aggregate_stress=80.0,
    policy_name="aggressive",
)

INSTITUTIONAL_LIMITS = RiskLimits(
    max_risk_score=65.0,
    daily_loss_limit=0.015,
    weekly_loss_limit=0.04,
    monthly_loss_limit=0.08,
    max_drawdown_limit=0.15,
    max_annualized_vol=0.30,
    max_portfolio_weight=0.30,
    max_leverage=1.5,
    min_stress_pass_rate=0.625,
    max_aggregate_stress=62.0,
    policy_name="institutional",
)
