"""iios/investment/strategy/portfolio/rebalance_policy.py
RebalancePolicy — declarative rules that define when a portfolio should rebalance.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class RebalanceTrigger(str, Enum):
    TIME_BASED        = "time_based"
    THRESHOLD_BASED   = "threshold_based"
    RISK_BASED        = "risk_based"
    PERFORMANCE_BASED = "performance_based"
    EVENT_DRIVEN      = "event_driven"
    MANUAL            = "manual"


@dataclass(frozen=True)
class RebalancePolicy:
    """
    Declares when a portfolio is eligible for rebalancing.
    Multiple triggers are OR-combined: any matching trigger fires rebalancing.
    """
    policy_name: str = "default"

    # Time-based: rebalance every N calendar days
    time_based_days: int = 30
    enable_time_trigger: bool = True

    # Threshold-based: rebalance if any weight drifts beyond this
    drift_threshold: float = 0.05       # 5% drift triggers
    enable_drift_trigger: bool = True

    # Risk-based: rebalance if max_drawdown proxy exceeds threshold
    max_portfolio_drawdown: float = 0.15  # 15%
    enable_risk_trigger: bool = False

    # Performance-based: rebalance if worst strategy evaluation_score drops below this
    min_strategy_eval_score: float = 40.0
    enable_performance_trigger: bool = False

    # Event-driven: rebalance on regime change
    rebalance_on_regime_change: bool = False

    # Anti-churn: minimum days between rebalances
    cooldown_days: int = 5

    def active_triggers(self) -> List[RebalanceTrigger]:
        triggers = []
        if self.enable_time_trigger:
            triggers.append(RebalanceTrigger.TIME_BASED)
        if self.enable_drift_trigger:
            triggers.append(RebalanceTrigger.THRESHOLD_BASED)
        if self.enable_risk_trigger:
            triggers.append(RebalanceTrigger.RISK_BASED)
        if self.enable_performance_trigger:
            triggers.append(RebalanceTrigger.PERFORMANCE_BASED)
        if self.rebalance_on_regime_change:
            triggers.append(RebalanceTrigger.EVENT_DRIVEN)
        return triggers

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_name":          self.policy_name,
            "time_based_days":      self.time_based_days,
            "drift_threshold":      self.drift_threshold,
            "cooldown_days":        self.cooldown_days,
            "active_triggers":      [t.value for t in self.active_triggers()],
        }


DEFAULT_POLICY = RebalancePolicy(policy_name="default")

AGGRESSIVE_POLICY = RebalancePolicy(
    policy_name="aggressive",
    time_based_days=7,
    drift_threshold=0.02,
    cooldown_days=2,
    enable_risk_trigger=True,
    enable_performance_trigger=True,
)

CONSERVATIVE_POLICY = RebalancePolicy(
    policy_name="conservative",
    time_based_days=90,
    drift_threshold=0.10,
    cooldown_days=30,
    enable_drift_trigger=True,
    enable_time_trigger=True,
)
