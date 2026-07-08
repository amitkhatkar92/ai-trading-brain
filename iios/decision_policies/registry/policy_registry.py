"""iios/decision_policies/registry/policy_registry.py — Master registry for all policy types."""
from __future__ import annotations

import threading

from ..compliance.compliance_policy import CompliancePolicy
from ..constraints.constraint import Constraint
from ..policy_exceptions import PolicyAlreadyExistsError, PolicyNotFoundError
from ..rules.rule import Rule
from ..rules.rule_group import RuleGroup


class PolicyRegistry:
    """
    Master registry that stores all policy artefacts:
    Rules, RuleGroups, Constraints, CompliancePolicies.
    """

    def __init__(self) -> None:
        self._rules:       dict[str, Rule]            = {}
        self._groups:      dict[str, RuleGroup]        = {}
        self._constraints: dict[str, Constraint]       = {}
        self._compliance:  dict[str, CompliancePolicy] = {}
        self._lock = threading.RLock()

    # ── Rules ──────────────────────────────────────────────────────────────

    def register_rule(self, rule: Rule, *, overwrite: bool = False) -> None:
        with self._lock:
            if not overwrite and rule.rule_id in self._rules:
                raise PolicyAlreadyExistsError(rule.rule_id)
            self._rules[rule.rule_id] = rule

    def get_rule(self, rule_id: str) -> Rule:
        with self._lock:
            if rule_id not in self._rules:
                raise PolicyNotFoundError(rule_id)
            return self._rules[rule_id]

    def has_rule(self, rule_id: str) -> bool:
        with self._lock:
            return rule_id in self._rules

    def all_rules(self) -> list[Rule]:
        with self._lock:
            return list(self._rules.values())

    # ── Groups ─────────────────────────────────────────────────────────────

    def register_group(self, group: RuleGroup, *, overwrite: bool = False) -> None:
        with self._lock:
            if not overwrite and group.group_id in self._groups:
                raise PolicyAlreadyExistsError(group.group_id)
            self._groups[group.group_id] = group

    def get_group(self, group_id: str) -> RuleGroup:
        with self._lock:
            if group_id not in self._groups:
                raise PolicyNotFoundError(group_id)
            return self._groups[group_id]

    def all_groups(self) -> list[RuleGroup]:
        with self._lock:
            return list(self._groups.values())

    # ── Constraints ────────────────────────────────────────────────────────

    def register_constraint(self, constraint: Constraint, *, overwrite: bool = False) -> None:
        with self._lock:
            if not overwrite and constraint.constraint_id in self._constraints:
                raise PolicyAlreadyExistsError(constraint.constraint_id)
            self._constraints[constraint.constraint_id] = constraint

    def get_constraint(self, constraint_id: str) -> Constraint:
        with self._lock:
            if constraint_id not in self._constraints:
                raise PolicyNotFoundError(constraint_id)
            return self._constraints[constraint_id]

    def all_constraints(self) -> list[Constraint]:
        with self._lock:
            return list(self._constraints.values())

    # ── Compliance ─────────────────────────────────────────────────────────

    def register_compliance(self, policy: CompliancePolicy, *, overwrite: bool = False) -> None:
        with self._lock:
            if not overwrite and policy.policy_id in self._compliance:
                raise PolicyAlreadyExistsError(policy.policy_id)
            self._compliance[policy.policy_id] = policy

    def get_compliance(self, policy_id: str) -> CompliancePolicy:
        with self._lock:
            if policy_id not in self._compliance:
                raise PolicyNotFoundError(policy_id)
            return self._compliance[policy_id]

    def all_compliance(self) -> list[CompliancePolicy]:
        with self._lock:
            return list(self._compliance.values())

    # ── Stats ──────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        with self._lock:
            return {
                "total_rules":       len(self._rules),
                "total_groups":      len(self._groups),
                "total_constraints": len(self._constraints),
                "total_compliance":  len(self._compliance),
            }


# ── Module-level singleton ────────────────────────────────────────────────────

_registry: PolicyRegistry | None = None
_lock = threading.Lock()


def get_policy_registry() -> PolicyRegistry:
    global _registry
    if _registry is None:
        with _lock:
            if _registry is None:
                _registry = PolicyRegistry()
    return _registry


def reset_policy_registry() -> None:
    global _registry
    with _lock:
        _registry = None
