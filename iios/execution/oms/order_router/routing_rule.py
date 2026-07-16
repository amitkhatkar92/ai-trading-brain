"""iios/execution/oms/order_router/routing_rule.py
==================================================
RoutingRule — a single evaluable routing criterion.

Rules inspect a RoutingCandidate + RoutingContext and either
award a positive score or discard the candidate.

C6 Execution Intelligence — Phase 2, Module 3
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from iios.execution.oms.order_router.constants import (
    BrokerCapability,
    CandidateScoreField,
    ExecutionMode,
    RoutingPolicyType,
)
from iios.execution.oms.order_router.routing_candidate import RoutingCandidate
from iios.execution.oms.order_router.routing_context import RoutingContext


@dataclass
class RoutingRule:
    """
    A single evaluation rule applied to one RoutingCandidate.

    Rules are pure functions: they may mutate the candidate's
    score or eligibility but never communicate with brokers.
    """
    rule_id:     str   = ""
    description: str   = ""
    weight:      float = 1.0
    is_hard:     bool  = False  # Hard rule: discard on failure (no score awarded)
    is_active:   bool  = True

    # Callable: (candidate, context) -> None
    _evaluator: Callable[[RoutingCandidate, RoutingContext], None] | None = field(
        default=None, repr=False, compare=False
    )

    def evaluate(self, candidate: RoutingCandidate, context: RoutingContext) -> None:
        """Apply this rule to the candidate in-place."""
        if not self.is_active or not candidate.is_eligible:
            return
        if self._evaluator is not None:
            self._evaluator(candidate, context)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id":     self.rule_id,
            "description": self.description,
            "weight":      self.weight,
            "is_hard":     self.is_hard,
            "is_active":   self.is_active,
        }


# ── Built-in Rule Factories ───────────────────────────────────────────────────

def make_availability_rule(weight: float = 10.0) -> RoutingRule:
    """Hard rule: discard unavailable brokers."""
    def _eval(c: RoutingCandidate, ctx: RoutingContext) -> None:
        if c.capabilities is None or not c.capabilities.is_available:
            c.discard("broker_unavailable")
        else:
            c.add_score(CandidateScoreField.AVAILABILITY, weight)

    return RoutingRule(
        rule_id="availability",
        description="Discard unavailable brokers; award score to available ones.",
        weight=weight,
        is_hard=True,
        _evaluator=_eval,
    )


def make_priority_rule(weight: float = 5.0) -> RoutingRule:
    """Score based on broker priority (higher priority = higher score)."""
    def _eval(c: RoutingCandidate, ctx: RoutingContext) -> None:
        if c.capabilities is None:
            return
        c.add_score(CandidateScoreField.PRIORITY, c.capabilities.priority * weight)

    return RoutingRule(
        rule_id="priority",
        description="Award score proportional to broker priority.",
        weight=weight,
        is_hard=False,
        _evaluator=_eval,
    )


def make_capability_rule(required: frozenset[BrokerCapability], weight: float = 8.0) -> RoutingRule:
    """Hard rule: discard brokers missing required capabilities."""
    def _eval(c: RoutingCandidate, ctx: RoutingContext) -> None:
        if c.capabilities is None:
            c.discard("no_capabilities")
            return
        missing = required - c.capabilities.supported_capabilities
        if missing:
            c.discard(f"missing_capabilities:{','.join(m.value for m in missing)}")
        else:
            c.add_score(CandidateScoreField.CAPABILITY, weight)

    return RoutingRule(
        rule_id="capability",
        description="Discard brokers missing required capabilities.",
        weight=weight,
        is_hard=True,
        _evaluator=_eval,
    )


def make_exchange_rule(weight: float = 6.0) -> RoutingRule:
    """Prefer brokers that explicitly list the target exchange."""
    def _eval(c: RoutingCandidate, ctx: RoutingContext) -> None:
        if not ctx.exchange or c.capabilities is None:
            return
        if c.capabilities.supported_exchanges and ctx.exchange not in c.capabilities.supported_exchanges:
            c.discard(f"exchange_not_supported:{ctx.exchange}")
        elif ctx.exchange and (not c.capabilities.supported_exchanges or
                               ctx.exchange in c.capabilities.supported_exchanges):
            c.add_score(CandidateScoreField.EXCHANGE_MATCH, weight)

    return RoutingRule(
        rule_id="exchange",
        description="Award score for exchange match; hard-discard on mismatch.",
        weight=weight,
        is_hard=True,
        _evaluator=_eval,
    )


def make_execution_mode_rule(weight: float = 7.0) -> RoutingRule:
    """Hard rule: discard brokers that do not support the requested execution mode."""
    def _eval(c: RoutingCandidate, ctx: RoutingContext) -> None:
        if c.capabilities is None:
            return
        if ctx.is_paper and not c.capabilities.supported_execution_modes:
            # If no modes declared, assume live only — discard for paper
            c.discard("broker_does_not_support_paper")
            return
        if (c.capabilities.supported_execution_modes and
                ctx.execution_mode not in c.capabilities.supported_execution_modes):
            c.discard(f"execution_mode_unsupported:{ctx.execution_mode.value}")
        else:
            c.add_score(CandidateScoreField.POLICY_MATCH, weight)

    return RoutingRule(
        rule_id="execution_mode",
        description="Discard brokers that do not support the execution mode.",
        weight=weight,
        is_hard=True,
        _evaluator=_eval,
    )


def make_order_type_rule(weight: float = 4.0) -> RoutingRule:
    """Hard rule: discard brokers that do not support the order type."""
    def _eval(c: RoutingCandidate, ctx: RoutingContext) -> None:
        if not ctx.order_type or c.capabilities is None:
            return
        if (c.capabilities.supported_order_types and
                ctx.order_type not in c.capabilities.supported_order_types):
            c.discard(f"order_type_unsupported:{ctx.order_type}")
        else:
            c.add_score(CandidateScoreField.CAPABILITY, weight)

    return RoutingRule(
        rule_id="order_type",
        description="Discard brokers not supporting the order type.",
        weight=weight,
        is_hard=True,
        _evaluator=_eval,
    )
