"""iios/execution/oms/order_router/routing_policy.py
==================================================
RoutingPolicy — an ordered collection of RoutingRules.

Seven named policies cover all institutional routing scenarios.

C6 Execution Intelligence — Phase 2, Module 3
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.execution.oms.order_router.constants import (
    BrokerCapability,
    CandidateScoreField,
    ExecutionMode,
    RoutingPolicyType,
)
from iios.execution.oms.order_router.routing_candidate import RoutingCandidate
from iios.execution.oms.order_router.routing_context import RoutingContext
from iios.execution.oms.order_router.routing_rule import (
    RoutingRule,
    make_availability_rule,
    make_capability_rule,
    make_exchange_rule,
    make_execution_mode_rule,
    make_order_type_rule,
    make_priority_rule,
)


@dataclass
class RoutingPolicy:
    """
    Named policy holding an ordered list of routing rules.

    apply() runs all rules against a list of candidates.
    """
    policy_type: RoutingPolicyType = RoutingPolicyType.DEFAULT
    rules:       list[RoutingRule] = field(default_factory=list)
    description: str = ""
    is_active:   bool = True

    def apply(
        self,
        candidates: list[RoutingCandidate],
        context: RoutingContext,
    ) -> list[RoutingCandidate]:
        """
        Evaluate all active rules against all candidates.
        Returns the original list (mutated in-place) — callers filter eligible.
        """
        if not self.is_active:
            return candidates
        for rule in self.rules:
            for candidate in candidates:
                rule.evaluate(candidate, context)
        return candidates

    def eligible(self, candidates: list[RoutingCandidate]) -> list[RoutingCandidate]:
        """Return only eligible (non-discarded) candidates."""
        return [c for c in candidates if c.is_eligible]

    def add_rule(self, rule: RoutingRule) -> None:
        self.rules.append(rule)

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_type": self.policy_type.value,
            "description": self.description,
            "is_active":   self.is_active,
            "rules":       [r.to_dict() for r in self.rules],
        }


# ── Policy Factories ──────────────────────────────────────────────────────────

def make_default_policy() -> RoutingPolicy:
    """
    Default Policy — availability + exchange + order type + priority.
    Routes to the first available, compatible broker.
    """
    return RoutingPolicy(
        policy_type=RoutingPolicyType.DEFAULT,
        description="Route to best available compatible broker.",
        rules=[
            make_availability_rule(weight=10.0),
            make_exchange_rule(weight=6.0),
            make_order_type_rule(weight=4.0),
            make_priority_rule(weight=5.0),
        ],
    )


def make_priority_policy() -> RoutingPolicy:
    """
    Priority Policy — heavily weights broker priority ranking.
    Use when specific broker preference is required.
    """
    return RoutingPolicy(
        policy_type=RoutingPolicyType.PRIORITY,
        description="Route to highest priority available broker.",
        rules=[
            make_availability_rule(weight=10.0),
            make_priority_rule(weight=20.0),   # priority dominates
            make_exchange_rule(weight=4.0),
            make_order_type_rule(weight=3.0),
        ],
    )


def make_capability_policy(required_caps: frozenset[BrokerCapability] | None = None) -> RoutingPolicy:
    """
    Capability Policy — ensures broker supports required capabilities.
    """
    caps = required_caps or frozenset()
    rules: list[RoutingRule] = [
        make_availability_rule(weight=10.0),
        make_capability_rule(caps, weight=8.0),
        make_exchange_rule(weight=5.0),
        make_order_type_rule(weight=4.0),
        make_priority_rule(weight=3.0),
    ]
    return RoutingPolicy(
        policy_type=RoutingPolicyType.CAPABILITY,
        description="Route to broker with required capabilities.",
        rules=rules,
    )


def make_exchange_policy() -> RoutingPolicy:
    """
    Exchange Policy — exchange support is the primary constraint.
    """
    return RoutingPolicy(
        policy_type=RoutingPolicyType.EXCHANGE,
        description="Route based on exchange support.",
        rules=[
            make_availability_rule(weight=10.0),
            make_exchange_rule(weight=15.0),    # exchange dominates
            make_order_type_rule(weight=4.0),
            make_priority_rule(weight=3.0),
        ],
    )


def make_paper_trading_policy() -> RoutingPolicy:
    """
    Paper Trading Policy — only paper-capable brokers accepted.
    """
    mode_rule = make_execution_mode_rule(weight=12.0)
    return RoutingPolicy(
        policy_type=RoutingPolicyType.PAPER_TRADE,
        description="Route to a broker that supports paper trading.",
        rules=[
            make_availability_rule(weight=10.0),
            mode_rule,
            make_priority_rule(weight=5.0),
        ],
    )


def make_backtest_policy() -> RoutingPolicy:
    """
    Backtest Policy — only backtest-capable brokers accepted.
    """
    def _backtest_eval(c: RoutingCandidate, ctx: RoutingContext) -> None:
        if c.capabilities is None:
            c.discard("no_capabilities_for_backtest")
            return
        if (c.capabilities.supported_execution_modes and
                ExecutionMode.BACKTEST not in c.capabilities.supported_execution_modes):
            c.discard("broker_does_not_support_backtest")
        else:
            c.add_score(CandidateScoreField.POLICY_MATCH, 12.0)

    from iios.execution.oms.order_router.routing_rule import RoutingRule
    bt_rule = RoutingRule(
        rule_id="backtest_mode",
        description="Discard brokers that do not support BACKTEST mode.",
        weight=12.0,
        is_hard=True,
        _evaluator=_backtest_eval,
    )
    return RoutingPolicy(
        policy_type=RoutingPolicyType.BACKTEST,
        description="Route to a broker that supports backtest execution.",
        rules=[
            make_availability_rule(weight=10.0),
            bt_rule,
            make_priority_rule(weight=5.0),
        ],
    )


def make_recovery_policy() -> RoutingPolicy:
    """
    Recovery Policy — lenient; accepts any available broker for order recovery.
    Priority is the only differentiator.
    """
    return RoutingPolicy(
        policy_type=RoutingPolicyType.RECOVERY,
        description="Route to any available broker for order recovery.",
        rules=[
            make_availability_rule(weight=10.0),
            make_priority_rule(weight=5.0),
        ],
    )


# ── Policy Registry mapping ───────────────────────────────────────────────────

def get_policy(policy_type: RoutingPolicyType) -> RoutingPolicy:
    """Return a fresh policy instance for the given type."""
    _map: dict[RoutingPolicyType, Any] = {
        RoutingPolicyType.DEFAULT:     make_default_policy,
        RoutingPolicyType.PRIORITY:    make_priority_policy,
        RoutingPolicyType.CAPABILITY:  make_capability_policy,
        RoutingPolicyType.EXCHANGE:    make_exchange_policy,
        RoutingPolicyType.PAPER_TRADE: make_paper_trading_policy,
        RoutingPolicyType.BACKTEST:    make_backtest_policy,
        RoutingPolicyType.RECOVERY:    make_recovery_policy,
    }
    factory = _map.get(policy_type)
    if factory is None:
        return make_default_policy()
    return factory()
