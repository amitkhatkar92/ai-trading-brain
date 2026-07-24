"""
integration_policy_validator.py — iios.integration.policies
-------------------------------------------------------------
IntegrationPolicyValidator — validates policy configuration
before registration and before evaluation.

Performs 7 checks covering name, type, domain, priority,
rule count, condition count, and rule action completeness.

C15 Enterprise Integration & Connectivity — Phase 1, Module 3
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .constants import DEFAULT_MAX_CONDITIONS_PER_RULE, DEFAULT_MAX_RULES_PER_POLICY
from .exceptions import PolicyValidationError
from .integration_policy import IntegrationPolicy


@dataclass(frozen=True)
class PolicyValidationResult:
    """Result of a single validation check."""
    check:   str
    passed:  bool
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {"check": self.check, "passed": self.passed, "message": self.message}


@dataclass(frozen=True)
class PolicyValidationReport:
    """Aggregated validation report for one policy."""
    policy_id:    str
    policy_name:  str
    results:      Tuple[PolicyValidationResult, ...]
    passed:       bool
    validated_at: str

    @property
    def failed_checks(self) -> List[str]:
        return [r.check for r in self.results if not r.passed]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id":     self.policy_id,
            "policy_name":   self.policy_name,
            "results":       [r.to_dict() for r in self.results],
            "passed":        self.passed,
            "failed_checks": self.failed_checks,
            "validated_at":  self.validated_at,
        }


class IntegrationPolicyValidator:
    """
    Validates that a governance policy is well-formed and complete.

    7 checks:
    1. policy_has_name
    2. policy_has_type
    3. policy_has_domain
    4. policy_has_priority
    5. rule_count_within_limits
    6. condition_count_within_limits
    7. rules_have_actions
    """

    def validate(self, policy: IntegrationPolicy) -> PolicyValidationReport:
        results: List[PolicyValidationResult] = [
            self._check_has_name(policy),
            self._check_has_type(policy),
            self._check_has_domain(policy),
            self._check_has_priority(policy),
            self._check_rule_count(policy),
            self._check_condition_count(policy),
            self._check_rules_have_actions(policy),
        ]
        passed = all(r.passed for r in results)
        return PolicyValidationReport(
            policy_id    = policy.policy_id,
            policy_name  = policy.name,
            results      = tuple(results),
            passed       = passed,
            validated_at = datetime.now(timezone.utc).isoformat(),
        )

    def validate_or_raise(self, policy: IntegrationPolicy) -> PolicyValidationReport:
        """Validate a policy and raise PolicyValidationError on failure."""
        report = self.validate(policy)
        if not report.passed:
            raise PolicyValidationError(
                f"Policy '{policy.name}' failed validation",
                failed_checks=report.failed_checks,
            )
        return report

    # ── individual checks ─────────────────────────────────────────────

    @staticmethod
    def _check_has_name(p: IntegrationPolicy) -> PolicyValidationResult:
        passed = bool(p.name and p.name.strip())
        return PolicyValidationResult(
            "policy_has_name",
            passed,
            "Policy has a non-empty name" if passed else "Policy name is empty",
        )

    @staticmethod
    def _check_has_type(p: IntegrationPolicy) -> PolicyValidationResult:
        passed = p.policy_type is not None
        return PolicyValidationResult(
            "policy_has_type",
            passed,
            "Policy type is set" if passed else "Policy type is missing",
        )

    @staticmethod
    def _check_has_domain(p: IntegrationPolicy) -> PolicyValidationResult:
        passed = p.domain is not None
        return PolicyValidationResult(
            "policy_has_domain",
            passed,
            "Policy domain is set" if passed else "Policy domain is missing",
        )

    @staticmethod
    def _check_has_priority(p: IntegrationPolicy) -> PolicyValidationResult:
        passed = p.priority is not None
        return PolicyValidationResult(
            "policy_has_priority",
            passed,
            "Policy priority is set" if passed else "Policy priority is missing",
        )

    @staticmethod
    def _check_rule_count(p: IntegrationPolicy) -> PolicyValidationResult:
        count  = len(p.rules)
        passed = count <= DEFAULT_MAX_RULES_PER_POLICY
        return PolicyValidationResult(
            "rule_count_within_limits",
            passed,
            f"Rule count {count} within limit" if passed
            else f"Rule count {count} exceeds limit {DEFAULT_MAX_RULES_PER_POLICY}",
        )

    @staticmethod
    def _check_condition_count(p: IntegrationPolicy) -> PolicyValidationResult:
        for rule in p.rules:
            if len(rule.conditions) > DEFAULT_MAX_CONDITIONS_PER_RULE:
                return PolicyValidationResult(
                    "condition_count_within_limits",
                    False,
                    f"Rule '{rule.name}' has {len(rule.conditions)} conditions "
                    f"(limit {DEFAULT_MAX_CONDITIONS_PER_RULE})",
                )
        return PolicyValidationResult(
            "condition_count_within_limits",
            True,
            "All rules are within the condition count limit",
        )

    @staticmethod
    def _check_rules_have_actions(p: IntegrationPolicy) -> PolicyValidationResult:
        for rule in p.rules:
            if rule.action is None:
                return PolicyValidationResult(
                    "rules_have_actions",
                    False,
                    f"Rule '{rule.name}' has no action defined",
                )
        return PolicyValidationResult(
            "rules_have_actions",
            True,
            "All rules have actions",
        )
