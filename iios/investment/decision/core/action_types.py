"""iios/investment/decision/core/action_types.py
Metadata descriptors for each ActionType.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from iios.investment.decision.core.decision_constants import ActionType


@dataclass(frozen=True)
class ActionDescriptor:
    action_type:   ActionType
    display_name:  str
    description:   str
    urgency:       str      # "low" | "medium" | "high" | "immediate"
    risk_level:    str      # "low" | "medium" | "high"
    is_reversible: bool
    requires_execution: bool   # True = execution layer must act

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type":          self.action_type.value,
            "display_name":         self.display_name,
            "description":          self.description,
            "urgency":              self.urgency,
            "risk_level":           self.risk_level,
            "is_reversible":        self.is_reversible,
            "requires_execution":   self.requires_execution,
        }


ACTION_DESCRIPTORS: Dict[ActionType, ActionDescriptor] = {
    ActionType.BUY_ORDER: ActionDescriptor(
        action_type=ActionType.BUY_ORDER,
        display_name="Buy Order",
        description="Place a buy order for a security.",
        urgency="medium", risk_level="medium", is_reversible=True, requires_execution=True,
    ),
    ActionType.SELL_ORDER: ActionDescriptor(
        action_type=ActionType.SELL_ORDER,
        display_name="Sell Order",
        description="Place a sell order for a security.",
        urgency="medium", risk_level="medium", is_reversible=True, requires_execution=True,
    ),
    ActionType.REDUCE_POSITION: ActionDescriptor(
        action_type=ActionType.REDUCE_POSITION,
        display_name="Reduce Position",
        description="Partially reduce an existing position.",
        urgency="medium", risk_level="medium", is_reversible=True, requires_execution=True,
    ),
    ActionType.INCREASE_POSITION: ActionDescriptor(
        action_type=ActionType.INCREASE_POSITION,
        display_name="Increase Position",
        description="Add to an existing position.",
        urgency="medium", risk_level="medium", is_reversible=True, requires_execution=True,
    ),
    ActionType.REBALANCE: ActionDescriptor(
        action_type=ActionType.REBALANCE,
        display_name="Rebalance",
        description="Rebalance portfolio allocations to target weights.",
        urgency="low", risk_level="low", is_reversible=True, requires_execution=True,
    ),
    ActionType.HEDGE: ActionDescriptor(
        action_type=ActionType.HEDGE,
        display_name="Hedge",
        description="Implement a hedging strategy to reduce downside risk.",
        urgency="high", risk_level="medium", is_reversible=True, requires_execution=True,
    ),
    ActionType.EXIT: ActionDescriptor(
        action_type=ActionType.EXIT,
        display_name="Exit",
        description="Full exit from a position.",
        urgency="immediate", risk_level="low", is_reversible=False, requires_execution=True,
    ),
    ActionType.RESEARCH: ActionDescriptor(
        action_type=ActionType.RESEARCH,
        display_name="Research",
        description="Trigger additional research on a subject.",
        urgency="low", risk_level="low", is_reversible=True, requires_execution=False,
    ),
    ActionType.MONITOR: ActionDescriptor(
        action_type=ActionType.MONITOR,
        display_name="Monitor",
        description="Continue monitoring without action.",
        urgency="low", risk_level="low", is_reversible=True, requires_execution=False,
    ),
    ActionType.ALERT: ActionDescriptor(
        action_type=ActionType.ALERT,
        display_name="Alert",
        description="Issue an alert for human review.",
        urgency="high", risk_level="low", is_reversible=True, requires_execution=False,
    ),
    ActionType.PORTFOLIO_ADJUSTMENT: ActionDescriptor(
        action_type=ActionType.PORTFOLIO_ADJUSTMENT,
        display_name="Portfolio Adjustment",
        description="Execute a structured portfolio restructuring.",
        urgency="medium", risk_level="medium", is_reversible=True, requires_execution=True,
    ),
    ActionType.RISK_ACTION: ActionDescriptor(
        action_type=ActionType.RISK_ACTION,
        display_name="Risk Action",
        description="Execute an emergency risk-management action.",
        urgency="immediate", risk_level="high", is_reversible=False, requires_execution=True,
    ),
}


def get_action_descriptor(action_type: ActionType) -> ActionDescriptor:
    return ACTION_DESCRIPTORS[action_type]
