"""iios/investment/decision/core/decision_types.py
Descriptors and metadata for each DecisionType.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Tuple

from iios.investment.decision.core.decision_constants import (
    ActionType,
    DecisionPriority,
    DecisionType,
    EnvironmentProfile,
    RecommendationType,
)


@dataclass(frozen=True)
class DecisionTypeDescriptor:
    """Static metadata about a registered decision type."""
    decision_type:          DecisionType
    display_name:           str
    description:            str
    allowed_recommendations: FrozenSet[RecommendationType]
    allowed_actions:         FrozenSet[ActionType]
    default_priority:        DecisionPriority
    requires_evidence:       bool
    requires_risk_review:    bool
    requires_approval:       bool
    supported_environments:  FrozenSet[EnvironmentProfile]
    capabilities:            Tuple[str, ...]
    version:                 str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_type":           self.decision_type.value,
            "display_name":            self.display_name,
            "description":             self.description,
            "allowed_recommendations": [r.value for r in sorted(self.allowed_recommendations, key=lambda x: x.value)],
            "allowed_actions":         [a.value for a in sorted(self.allowed_actions, key=lambda x: x.value)],
            "default_priority":        self.default_priority.value,
            "requires_evidence":       self.requires_evidence,
            "requires_risk_review":    self.requires_risk_review,
            "requires_approval":       self.requires_approval,
            "supported_environments":  [e.value for e in sorted(self.supported_environments, key=lambda x: x.value)],
            "capabilities":            list(self.capabilities),
            "version":                 self.version,
        }


# Built-in descriptors
_ALL_ENVS = frozenset(EnvironmentProfile)
_ALL_RECS = frozenset(RecommendationType)
_ALL_ACTS = frozenset(ActionType)

DECISION_TYPE_DESCRIPTORS: Dict[DecisionType, DecisionTypeDescriptor] = {
    DecisionType.INVESTMENT: DecisionTypeDescriptor(
        decision_type=DecisionType.INVESTMENT,
        display_name="Investment Decision",
        description="A decision to buy, sell, or hold a security or asset.",
        allowed_recommendations=_ALL_RECS,
        allowed_actions=frozenset({
            ActionType.BUY_ORDER, ActionType.SELL_ORDER,
            ActionType.REDUCE_POSITION, ActionType.INCREASE_POSITION,
            ActionType.EXIT, ActionType.MONITOR,
        }),
        default_priority=DecisionPriority.NORMAL,
        requires_evidence=True,
        requires_risk_review=True,
        requires_approval=True,
        supported_environments=_ALL_ENVS,
        capabilities=("evidence_collection", "scoring", "risk_review", "approval", "publishing"),
    ),
    DecisionType.PORTFOLIO_ADJUSTMENT: DecisionTypeDescriptor(
        decision_type=DecisionType.PORTFOLIO_ADJUSTMENT,
        display_name="Portfolio Adjustment",
        description="A decision to rebalance or restructure a portfolio.",
        allowed_recommendations=frozenset({
            RecommendationType.HOLD,
            RecommendationType.REDUCE,
            RecommendationType.ACCUMULATE,
        }),
        allowed_actions=frozenset({
            ActionType.REBALANCE, ActionType.REDUCE_POSITION,
            ActionType.INCREASE_POSITION, ActionType.PORTFOLIO_ADJUSTMENT,
        }),
        default_priority=DecisionPriority.HIGH,
        requires_evidence=True,
        requires_risk_review=True,
        requires_approval=True,
        supported_environments=_ALL_ENVS,
        capabilities=("evidence_collection", "scoring", "risk_review", "approval", "publishing"),
    ),
    DecisionType.RISK_ACTION: DecisionTypeDescriptor(
        decision_type=DecisionType.RISK_ACTION,
        display_name="Risk Action",
        description="An immediate risk-mitigation action (stop-loss, hedge, exit).",
        allowed_recommendations=frozenset({
            RecommendationType.SELL, RecommendationType.STRONG_SELL,
            RecommendationType.REDUCE, RecommendationType.AVOID,
        }),
        allowed_actions=frozenset({
            ActionType.EXIT, ActionType.HEDGE, ActionType.SELL_ORDER,
            ActionType.REDUCE_POSITION, ActionType.RISK_ACTION, ActionType.ALERT,
        }),
        default_priority=DecisionPriority.URGENT,
        requires_evidence=False,
        requires_risk_review=True,
        requires_approval=False,
        supported_environments=_ALL_ENVS,
        capabilities=("scoring", "risk_review", "publishing"),
    ),
    DecisionType.RESEARCH: DecisionTypeDescriptor(
        decision_type=DecisionType.RESEARCH,
        display_name="Research Decision",
        description="A decision to initiate or prioritise additional research.",
        allowed_recommendations=frozenset({
            RecommendationType.RESEARCH_REQUIRED,
            RecommendationType.WATCHLIST,
            RecommendationType.HOLD,
        }),
        allowed_actions=frozenset({ActionType.RESEARCH, ActionType.MONITOR, ActionType.ALERT}),
        default_priority=DecisionPriority.LOW,
        requires_evidence=True,
        requires_risk_review=False,
        requires_approval=False,
        supported_environments=_ALL_ENVS,
        capabilities=("evidence_collection", "scoring", "publishing"),
    ),
    DecisionType.SYSTEM: DecisionTypeDescriptor(
        decision_type=DecisionType.SYSTEM,
        display_name="System Decision",
        description="Internal framework or system-level decision.",
        allowed_recommendations=frozenset({RecommendationType.HOLD}),
        allowed_actions=frozenset({ActionType.MONITOR, ActionType.ALERT}),
        default_priority=DecisionPriority.NORMAL,
        requires_evidence=False,
        requires_risk_review=False,
        requires_approval=False,
        supported_environments=_ALL_ENVS,
        capabilities=("publishing",),
    ),
}


def get_descriptor(decision_type: DecisionType) -> DecisionTypeDescriptor:
    return DECISION_TYPE_DESCRIPTORS[decision_type]
