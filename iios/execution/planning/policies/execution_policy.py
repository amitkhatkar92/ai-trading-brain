"""iios/execution/planning/policies/execution_policy.py
Execution policy framework — broker-independent execution constraints.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.planning.planning_constants import PolicyType, ExecutionMode
from iios.execution.planning.planning_exceptions import PolicyViolationError
from iios.execution.planning.core.execution_plan import ExecutionPlan


@dataclass
class PolicyRule:
    """A single evaluatable rule within a policy."""

    rule_id:     str            = field(default_factory=lambda: str(uuid.uuid4()))
    name:        str            = ""
    description: str            = ""
    is_hard:     bool           = True    # hard = blocking; soft = advisory
    parameters:  dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id":     self.rule_id,
            "name":        self.name,
            "description": self.description,
            "is_hard":     self.is_hard,
            "parameters":  self.parameters,
        }


@dataclass
class PolicyEvaluation:
    """Result of evaluating a policy against an execution plan."""

    policy_id:      str           = ""
    plan_id:        str           = ""
    approved:       bool          = True
    violations:     list[str]     = field(default_factory=list)
    advisories:     list[str]     = field(default_factory=list)
    evaluated_at:   float         = field(default_factory=time.time)
    metadata:       dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id":    self.policy_id,
            "plan_id":      self.plan_id,
            "approved":     self.approved,
            "violations":   self.violations,
            "advisories":   self.advisories,
            "evaluated_at": self.evaluated_at,
        }


class ExecutionPolicy:
    """
    Base execution policy.

    Subclass and override ``evaluate`` to add custom logic.
    The base implementation approves all plans unconditionally.
    """

    def __init__(
        self,
        policy_id:   str        = "",
        name:        str        = "DefaultPolicy",
        policy_type: PolicyType = PolicyType.IMMEDIATE,
        rules:       list[PolicyRule] | None = None,
    ) -> None:
        self.policy_id   = policy_id or str(uuid.uuid4())
        self.name        = name
        self.policy_type = policy_type
        self.rules:      list[PolicyRule] = rules or []

    def evaluate(self, plan: ExecutionPlan) -> PolicyEvaluation:
        """Override to add policy-specific checks."""
        return PolicyEvaluation(policy_id=self.policy_id, plan_id=plan.plan_id, approved=True)

    def enforce(self, plan: ExecutionPlan) -> PolicyEvaluation:
        """Evaluate and raise PolicyViolationError on hard violations."""
        result = self.evaluate(plan)
        if not result.approved and result.violations:
            raise PolicyViolationError(policy_name=self.name)
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id":   self.policy_id,
            "name":        self.name,
            "policy_type": self.policy_type.value,
            "rules":       [r.to_dict() for r in self.rules],
        }


class ImmediatePolicy(ExecutionPolicy):
    """Approves immediate-mode plans only."""

    def __init__(self) -> None:
        super().__init__(
            name        = "ImmediatePolicy",
            policy_type = PolicyType.IMMEDIATE,
        )

    def evaluate(self, plan: ExecutionPlan) -> PolicyEvaluation:
        violations: list[str] = []
        if plan.execution_mode != ExecutionMode.IMMEDIATE:
            violations.append(
                f"ImmediatePolicy: execution_mode must be IMMEDIATE, got {plan.execution_mode.value}"
            )
        return PolicyEvaluation(
            policy_id  = self.policy_id,
            plan_id    = plan.plan_id,
            approved   = not violations,
            violations = violations,
        )


class RiskLimitedPolicy(ExecutionPolicy):
    """Blocks plans whose estimated cost exceeds a threshold."""

    def __init__(self, max_total_cost: float = 1_000_000.0) -> None:
        super().__init__(
            name        = "RiskLimitedPolicy",
            policy_type = PolicyType.RISK_LIMITED,
        )
        self.max_total_cost = max_total_cost

    def evaluate(self, plan: ExecutionPlan) -> PolicyEvaluation:
        violations: list[str] = []
        total = plan.estimated_cost.total_estimated_cost
        if total > self.max_total_cost:
            violations.append(
                f"RiskLimitedPolicy: estimated cost {total:.2f} "
                f"exceeds limit {self.max_total_cost:.2f}"
            )
        return PolicyEvaluation(
            policy_id  = self.policy_id,
            plan_id    = plan.plan_id,
            approved   = not violations,
            violations = violations,
        )


class PolicyRegistry:
    """Thread-safe registry of named execution policies."""

    import threading as _threading

    def __init__(self) -> None:
        import threading
        self._lock     = threading.RLock()
        self._policies: dict[str, ExecutionPolicy] = {}

    def register(self, policy: ExecutionPolicy, *, overwrite: bool = False) -> None:
        with self._lock:
            if policy.policy_id in self._policies and not overwrite:
                raise KeyError(f"Policy already registered: {policy.policy_id!r}")
            self._policies[policy.policy_id] = policy

    def get(self, policy_id: str) -> ExecutionPolicy:
        with self._lock:
            if policy_id not in self._policies:
                raise KeyError(f"Policy not found: {policy_id!r}")
            return self._policies[policy_id]

    def all_policies(self) -> list[ExecutionPolicy]:
        with self._lock:
            return list(self._policies.values())

    def evaluate_all(self, plan: ExecutionPlan) -> list[PolicyEvaluation]:
        with self._lock:
            policies = list(self._policies.values())
        return [p.evaluate(plan) for p in policies]
