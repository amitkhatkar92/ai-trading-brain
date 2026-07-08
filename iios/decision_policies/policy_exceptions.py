"""
iios/decision_policies/policy_exceptions.py
===========================================
Full exception hierarchy for the Decision Policy & Rule Engine.
Error code prefix: PE-
"""
from __future__ import annotations


class PolicyEngineError(Exception):
    """PE-000 — Base exception for the policy engine."""
    code: str = "PE-000"

    def __init__(self, message: str, code: str | None = None) -> None:
        self.code = code or self.__class__.code
        super().__init__(f"[{self.code}] {message}")


# ── Policy ────────────────────────────────────────────────────────────────────

class PolicyError(PolicyEngineError):
    code = "PE-010"


class PolicyNotFoundError(PolicyError):
    code = "PE-011"
    def __init__(self, policy_id: str) -> None:
        super().__init__(f"Policy not found: {policy_id!r}", self.code)


class PolicyAlreadyExistsError(PolicyError):
    code = "PE-012"
    def __init__(self, policy_id: str) -> None:
        super().__init__(f"Policy already exists: {policy_id!r}", self.code)


class PolicyDisabledError(PolicyError):
    code = "PE-013"
    def __init__(self, policy_id: str) -> None:
        super().__init__(f"Policy is disabled: {policy_id!r}", self.code)


# ── Rules ─────────────────────────────────────────────────────────────────────

class RuleError(PolicyEngineError):
    code = "PE-020"


class RuleNotFoundError(RuleError):
    code = "PE-021"
    def __init__(self, rule_id: str) -> None:
        super().__init__(f"Rule not found: {rule_id!r}", self.code)


class RuleExecutionError(RuleError):
    code = "PE-022"
    def __init__(self, rule_id: str, reason: str) -> None:
        super().__init__(f"Rule {rule_id!r} execution failed: {reason}", self.code)


class RuleDependencyError(RuleError):
    code = "PE-023"
    def __init__(self, rule_id: str, dep_id: str) -> None:
        super().__init__(f"Rule {rule_id!r} missing dependency: {dep_id!r}", self.code)


class CircularRuleDependencyError(RuleError):
    code = "PE-024"
    def __init__(self, rule_id: str) -> None:
        super().__init__(f"Circular dependency detected for rule: {rule_id!r}", self.code)


class RuleAlreadyExistsError(RuleError):
    code = "PE-025"
    def __init__(self, rule_id: str) -> None:
        super().__init__(f"Rule already exists: {rule_id!r}", self.code)


# ── Constraints ───────────────────────────────────────────────────────────────

class ConstraintError(PolicyEngineError):
    code = "PE-030"


class ConstraintViolationError(ConstraintError):
    code = "PE-031"
    def __init__(self, constraint_id: str, reason: str) -> None:
        super().__init__(f"Constraint {constraint_id!r} violated: {reason}", self.code)


class ConstraintNotFoundError(ConstraintError):
    code = "PE-032"
    def __init__(self, constraint_id: str) -> None:
        super().__init__(f"Constraint not found: {constraint_id!r}", self.code)


class ConstraintAlreadyExistsError(ConstraintError):
    code = "PE-033"
    def __init__(self, constraint_id: str) -> None:
        super().__init__(f"Constraint already exists: {constraint_id!r}", self.code)


# ── Compliance ────────────────────────────────────────────────────────────────

class ComplianceError(PolicyEngineError):
    code = "PE-040"


class CompliancePolicyViolationError(ComplianceError):
    code = "PE-041"
    def __init__(self, policy_id: str, reason: str) -> None:
        super().__init__(f"Compliance policy {policy_id!r} violated: {reason}", self.code)


class CompliancePolicyNotFoundError(ComplianceError):
    code = "PE-042"
    def __init__(self, policy_id: str) -> None:
        super().__init__(f"Compliance policy not found: {policy_id!r}", self.code)


# ── Evaluation ────────────────────────────────────────────────────────────────

class EvaluationError(PolicyEngineError):
    code = "PE-050"


class EvaluationFailedError(EvaluationError):
    code = "PE-051"


class PolicyConflictError(EvaluationError):
    code = "PE-052"
    def __init__(self, policy_a: str, policy_b: str) -> None:
        super().__init__(f"Policy conflict: {policy_a!r} vs {policy_b!r}", self.code)


class NoApplicablePoliciesError(EvaluationError):
    code = "PE-053"
    def __init__(self, source_id: str) -> None:
        super().__init__(f"No applicable policies for source: {source_id!r}", self.code)


# ── Registry ──────────────────────────────────────────────────────────────────

class RegistryError(PolicyEngineError):
    code = "PE-060"


class RegistryOverflowError(RegistryError):
    code = "PE-061"
    def __init__(self, limit: int) -> None:
        super().__init__(f"Registry limit exceeded: {limit}", self.code)


# ── Engine lifecycle ──────────────────────────────────────────────────────────

class EngineLifecycleError(PolicyEngineError):
    code = "PE-070"


class EngineNotInitializedError(EngineLifecycleError):
    code = "PE-071"
    def __init__(self) -> None:
        super().__init__("Policy engine is not initialized", self.code)


class EngineAlreadyRunningError(EngineLifecycleError):
    code = "PE-072"
    def __init__(self) -> None:
        super().__init__("Policy engine is already running", self.code)


# ── Override ──────────────────────────────────────────────────────────────────

class OverrideError(PolicyEngineError):
    code = "PE-080"


class InvalidOverrideError(OverrideError):
    code = "PE-081"


class UnauthorizedOverrideError(OverrideError):
    code = "PE-082"
    def __init__(self, requester: str) -> None:
        super().__init__(f"Unauthorized override by: {requester!r}", self.code)
