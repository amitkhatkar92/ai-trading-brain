"""
iios/execution/recovery/policies/recovery_validation.py
=======================================================
PolicyEvaluationValidator — stateless validation for all framework entities.

Validates contexts, requests, policies, strategies, decisions, and checks
cross-policy consistency.

C7 Execution Recovery & Resilience — Phase 1, Module 3
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence


@dataclass
class PolicyValidationResult:
    """Mutable validation result accumulating errors and warnings."""

    is_valid: bool           = True
    errors:   List[str]      = field(default_factory=list)
    warnings: List[str]      = field(default_factory=list)

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def merge(self, other: "PolicyValidationResult") -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.is_valid:
            self.is_valid = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors":   list(self.errors),
            "warnings": list(self.warnings),
        }


class PolicyEvaluationValidator:
    """
    Stateless validator for Recovery Policy Framework entities.

    All methods are pure functions that accept an entity and return a
    PolicyValidationResult.  They never raise exceptions.
    """

    # ── Context ───────────────────────────────────────────────────────────────

    def validate_context(self, context: Any) -> PolicyValidationResult:
        result = PolicyValidationResult()
        if context is None:
            result.add_error("context must not be None")
            return result
        if not getattr(context, "context_id", ""):
            result.add_error("context.context_id is required")
        if not getattr(context, "execution_session_id", ""):
            result.add_error("context.execution_session_id is required")
        if not getattr(context, "subsystem_id", ""):
            result.add_error("context.subsystem_id is required")
        if getattr(context, "failure_category", None) is None:
            result.add_error("context.failure_category is required")
        if getattr(context, "failure_severity", None) is None:
            result.add_error("context.failure_severity is required")
        if not getattr(context, "failure_reason", ""):
            result.add_warning("context.failure_reason is empty")
        availability = getattr(context, "subsystem_availability", 1.0)
        if not 0.0 <= availability <= 1.0:
            result.add_error(
                f"context.subsystem_availability must be 0.0-1.0, got {availability}"
            )
        return result

    # ── Request ───────────────────────────────────────────────────────────────

    def validate_request(self, request: Any) -> PolicyValidationResult:
        result = PolicyValidationResult()
        if request is None:
            result.add_error("request must not be None")
            return result
        if not getattr(request, "request_id", ""):
            result.add_error("request.request_id is required")
        if not getattr(request, "execution_session_id", ""):
            result.add_error("request.execution_session_id is required")
        if not getattr(request, "subsystem_id", ""):
            result.add_error("request.subsystem_id is required")
        if getattr(request, "context", None) is None:
            result.add_error("request.context is required")
        else:
            ctx_result = self.validate_context(request.context)
            result.merge(ctx_result)
        return result

    # ── Policy ────────────────────────────────────────────────────────────────

    def validate_policy(self, policy: Any) -> PolicyValidationResult:
        result = PolicyValidationResult()
        if policy is None:
            result.add_error("policy must not be None")
            return result
        if not getattr(policy, "name", ""):
            result.add_error("policy.name is required")
        if getattr(policy, "priority", None) is None:
            result.add_error("policy.priority is required")
        elif not isinstance(policy.priority, int):
            result.add_error("policy.priority must be an int")
        rules = getattr(policy, "rules", None)
        if rules is not None:
            for rule in rules:
                rule_result = self._validate_rule(rule)
                result.merge(rule_result)
        return result

    def _validate_rule(self, rule: Any) -> PolicyValidationResult:
        result = PolicyValidationResult()
        if not getattr(rule, "rule_id", ""):
            result.add_error("rule.rule_id is required")
        if not getattr(rule, "name", ""):
            result.add_error("rule.name is required")
        confidence = getattr(rule, "confidence_score", None)
        if confidence is not None and not 0.0 <= confidence <= 1.0:
            result.add_error(
                f"rule.confidence_score must be 0.0-1.0, got {confidence}"
            )
        return result

    # ── Strategy ──────────────────────────────────────────────────────────────

    def validate_strategy(self, strategy: Any) -> PolicyValidationResult:
        result = PolicyValidationResult()
        if strategy is None:
            result.add_error("strategy must not be None")
            return result
        if not getattr(strategy, "strategy_id", ""):
            result.add_error("strategy.strategy_id is required")
        if getattr(strategy, "strategy_type", None) is None:
            result.add_error("strategy.strategy_type is required")
        timeout = getattr(strategy, "timeout_ms", -1)
        if timeout < 0:
            result.add_error("strategy.timeout_ms must be >= 0")
        return result

    # ── Decision ──────────────────────────────────────────────────────────────

    def validate_decision(self, decision: Any) -> PolicyValidationResult:
        result = PolicyValidationResult()
        if decision is None:
            result.add_error("decision must not be None")
            return result
        if not getattr(decision, "decision_id", ""):
            result.add_error("decision.decision_id is required")
        if not getattr(decision, "request_id", ""):
            result.add_error("decision.request_id is required")
        confidence = getattr(decision, "confidence_score", None)
        if confidence is not None and not 0.0 <= confidence <= 1.0:
            result.add_error(
                f"decision.confidence_score must be 0.0-1.0, got {confidence}"
            )
        return result

    # ── Cross-policy consistency ──────────────────────────────────────────────

    def validate_policy_consistency(self, policies: Sequence[Any]) -> PolicyValidationResult:
        result = PolicyValidationResult()
        names = [getattr(p, "name", "") for p in policies]

        # Check for duplicate names
        seen: set = set()
        for name in names:
            if name in seen:
                result.add_error(f"Duplicate policy name: {name!r}")
            seen.add(name)

        # At most one fallback policy
        fallback_count = sum(1 for p in policies if getattr(p, "is_fallback", False))
        if fallback_count > 1:
            result.add_warning(
                f"Multiple fallback policies registered ({fallback_count}); "
                "only the lowest-priority one will be used"
            )

        return result
