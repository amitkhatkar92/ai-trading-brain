"""iios/investment/portfolio/rebalancing/rebalance_policy.py

Policy definitions for portfolio rebalancing.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from iios.investment.portfolio.rebalancing.rebalancing_types import (
    CALENDAR_QUARTERLY_DAYS, DRIFT_THRESHOLD_MODERATE,
    PolicyType, RebalanceTrigger,
)


@dataclass(frozen=True)
class PolicyParameters:
    """Configurable parameters for a rebalancing policy."""

    # Threshold-based
    drift_threshold:           float = DRIFT_THRESHOLD_MODERATE  # 5% default
    max_position_drift:        float = 0.10   # per-position max before forced rebalance
    min_portfolio_drift:       float = 0.03   # minimum total drift to consider

    # Calendar-based
    calendar_frequency_days:   int   = CALENDAR_QUARTERLY_DAYS  # 91 days
    min_days_since_rebalance:  int   = 14     # never rebalance within 14 days

    # Cost control
    max_turnover_per_rebal:    float = 0.30   # 30% max single-rebalance turnover
    min_benefit_cost_ratio:    float = 1.5    # minimum benefit/cost to proceed

    # Tax sensitivity
    tax_aware:                 bool  = True
    avoid_stcg_sells:          bool  = False  # avoid selling positions < 1 year
    min_tax_saving_to_harvest: float = 0.01   # 1% tax benefit threshold

    # Risk-based
    max_portfolio_risk:        float = 0.70   # risk score threshold
    min_liquidity:             float = 0.40   # minimum weighted liquidity

    # Trade sizing
    min_trade_size:            float = 0.005  # 0.5% minimum trade
    round_lot_pct:             float = 0.005  # round to nearest 0.5%

    def to_dict(self) -> Dict[str, Any]:
        return {
            "drift_threshold":         self.drift_threshold,
            "calendar_frequency_days": self.calendar_frequency_days,
            "max_turnover_per_rebal":  self.max_turnover_per_rebal,
            "tax_aware":               self.tax_aware,
            "min_benefit_cost_ratio":  self.min_benefit_cost_ratio,
        }


@dataclass(frozen=True)
class RebalancePolicy:
    """Complete rebalancing policy definition."""

    policy_id:       str             = field(default_factory=lambda: str(uuid.uuid4()))
    name:            str             = "default"
    description:     str             = ""
    policy_type:     PolicyType      = PolicyType.THRESHOLD
    trigger:         RebalanceTrigger= RebalanceTrigger.THRESHOLD
    parameters:      PolicyParameters= field(default_factory=PolicyParameters)
    is_default:      bool            = False
    is_active:       bool            = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id":   self.policy_id,
            "name":        self.name,
            "policy_type": self.policy_type.value,
            "trigger":     self.trigger.value,
            "is_default":  self.is_default,
            "parameters":  self.parameters.to_dict(),
        }


@dataclass(frozen=True)
class PolicyEvalResult:
    """Result of evaluating a rebalancing policy."""

    policy_id:          str               = ""
    policy_name:        str               = ""
    trigger:            RebalanceTrigger  = RebalanceTrigger.NONE
    triggered:          bool              = False
    confidence:         float             = 0.0   # [0, 1]
    reasons:            tuple             = field(default_factory=tuple)   # str
    blocking_reasons:   tuple             = field(default_factory=tuple)   # str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id":   self.policy_id,
            "triggered":   self.triggered,
            "trigger":     self.trigger.value,
            "confidence":  round(self.confidence, 4),
            "reasons":     list(self.reasons),
        }
