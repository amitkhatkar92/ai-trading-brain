"""compliance/policy_validator.py — Configurable governance policy engine."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from iios.integration.research.governance.governance_constants import ComplianceStatus, PolicyType
from iios.integration.research.governance.governance_exceptions import PolicyNotFoundError, PolicyViolationError


@dataclass
class PolicyViolation:
    """A single rule violation found during compliance checking."""
    violation_id: str
    policy_id:    str
    rule_id:      str
    severity:     str   # "low" | "medium" | "high" | "critical"
    message:      str
    entity_id:    Optional[str]
    detail:       dict[str, Any]
    occurred_at:  float

    @classmethod
    def create(
        cls,
        policy_id:  str,
        rule_id:    str,
        severity:   str,
        message:    str,
        *,
        entity_id:    Optional[str] = None,
        detail:       Optional[dict] = None,
        violation_id: Optional[str]  = None,
    ) -> "PolicyViolation":
        return cls(
            violation_id = violation_id or f"pv_{uuid.uuid4().hex[:10]}",
            policy_id    = policy_id,
            rule_id      = rule_id,
            severity     = severity,
            message      = message,
            entity_id    = entity_id,
            detail       = detail or {},
            occurred_at  = time.time(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "violation_id": self.violation_id,
            "policy_id":    self.policy_id,
            "rule_id":      self.rule_id,
            "severity":     self.severity,
            "message":      self.message,
            "entity_id":    self.entity_id,
            "detail":       self.detail,
            "occurred_at":  self.occurred_at,
        }


@dataclass
class GovernancePolicy:
    """
    A named set of validation rules applied to a research entity dict.

    Rules are stored as config dicts; the ``check_fn`` is injected at runtime
    via ``PolicyValidator.register_check``.
    """
    policy_id:   str
    name:        str
    policy_type: PolicyType
    rules:       list[dict[str, Any]]   # [{rule_id, description, check_fn_name, severity}]
    enabled:     bool
    version:     str
    created_at:  float

    @classmethod
    def create(
        cls,
        name:        str,
        policy_type: PolicyType,
        rules:       list[dict[str, Any]],
        *,
        policy_id:  Optional[str] = None,
        version:    str           = "1.0.0",
        enabled:    bool          = True,
    ) -> "GovernancePolicy":
        return cls(
            policy_id   = policy_id or f"gp_{uuid.uuid4().hex[:10]}",
            name        = name,
            policy_type = policy_type,
            rules       = rules,
            enabled     = enabled,
            version     = version,
            created_at  = time.time(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id":   self.policy_id,
            "name":        self.name,
            "policy_type": self.policy_type.value,
            "rules":       self.rules,
            "enabled":     self.enabled,
            "version":     self.version,
            "created_at":  self.created_at,
        }


class PolicyValidator:
    """
    Runs registered policies against entity dicts.

    Check functions are registered separately from policy definitions so
    that policies remain plain data (JSON-serialisable).
    """

    def __init__(self) -> None:
        self._policies:  dict[str, GovernancePolicy]       = {}
        self._check_fns: dict[str, Callable[[dict], bool]] = {}

    def register_policy(self, policy: GovernancePolicy) -> None:
        self._policies[policy.policy_id] = policy

    def register_check(self, fn_name: str, fn: Callable[[dict], bool]) -> None:
        """Register a named boolean check function."""
        self._check_fns[fn_name] = fn

    def get_policy(self, policy_id: str) -> GovernancePolicy:
        pol = self._policies.get(policy_id)
        if pol is None:
            raise PolicyNotFoundError(f"Policy '{policy_id}' not found")
        return pol

    def validate(
        self,
        entity: dict[str, Any],
        policy_id: str,
    ) -> list[PolicyViolation]:
        pol = self.get_policy(policy_id)
        if not pol.enabled:
            return []
        violations: list[PolicyViolation] = []
        for rule in pol.rules:
            fn_name = rule.get("check_fn_name", "")
            fn      = self._check_fns.get(fn_name)
            if fn is None:
                continue
            try:
                passed = fn(entity)
            except Exception as exc:
                passed = False
            if not passed:
                violations.append(PolicyViolation.create(
                    policy_id = pol.policy_id,
                    rule_id   = rule.get("rule_id", "unknown"),
                    severity  = rule.get("severity", "medium"),
                    message   = rule.get("description", f"Rule {rule.get('rule_id')} failed"),
                    entity_id = entity.get("entity_id") or entity.get("project_id"),
                    detail    = {"rule": rule},
                ))
        return violations

    def validate_all(self, entity: dict[str, Any]) -> list[PolicyViolation]:
        violations: list[PolicyViolation] = []
        for policy_id in self._policies:
            violations.extend(self.validate(entity, policy_id))
        return violations

    def all_policies(self) -> list[GovernancePolicy]:
        return list(self._policies.values())

    def stats(self) -> dict[str, Any]:
        return {
            "policies":  len(self._policies),
            "check_fns": len(self._check_fns),
        }
