"""iios/decision_governance/governance_exceptions.py"""
from __future__ import annotations


class GovernanceEngineError(Exception):
    """Base exception for all Decision Governance & Audit Engine errors."""

    code: str = "GA-000"

    def __init__(self, message: str = "", code: str | None = None) -> None:
        self.code = code or self.__class__.code
        super().__init__(f"[{self.code}] {message}" if message else f"[{self.code}]")


# ── Governance ────────────────────────────────────────────────────────────────
class GovernanceError(GovernanceEngineError):
    code = "GA-010"


class GovernanceNotFoundError(GovernanceError):
    code = "GA-011"

    def __init__(self, governance_id: str = "") -> None:
        super().__init__(f"Governance result not found: {governance_id!r}")


class GovernanceAlreadyExistsError(GovernanceError):
    code = "GA-012"

    def __init__(self, governance_id: str = "") -> None:
        super().__init__(f"Governance result already exists: {governance_id!r}")


class GovernanceFailedError(GovernanceError):
    code = "GA-013"


# ── Approval ──────────────────────────────────────────────────────────────────
class ApprovalError(GovernanceEngineError):
    code = "GA-020"


class ApprovalNotFoundError(ApprovalError):
    code = "GA-021"

    def __init__(self, approval_id: str = "") -> None:
        super().__init__(f"Approval result not found: {approval_id!r}")


class ApprovalAlreadyExistsError(ApprovalError):
    code = "GA-022"

    def __init__(self, approval_id: str = "") -> None:
        super().__init__(f"Approval already exists: {approval_id!r}")


class ApprovalDeniedError(ApprovalError):
    code = "GA-023"

    def __init__(self, reason: str = "") -> None:
        super().__init__(f"Approval denied: {reason}")


class ApprovalExpiredError(ApprovalError):
    code = "GA-024"

    def __init__(self, approval_id: str = "") -> None:
        super().__init__(f"Approval expired: {approval_id!r}")


class ApprovalEscalatedError(ApprovalError):
    code = "GA-025"

    def __init__(self, reason: str = "") -> None:
        super().__init__(f"Approval escalated: {reason}")


class ApprovalWorkflowError(ApprovalError):
    code = "GA-026"


# ── Audit ─────────────────────────────────────────────────────────────────────
class AuditError(GovernanceEngineError):
    code = "GA-030"


class AuditNotFoundError(AuditError):
    code = "GA-031"

    def __init__(self, event_id: str = "") -> None:
        super().__init__(f"Audit event not found: {event_id!r}")


class AuditAlreadyExistsError(AuditError):
    code = "GA-032"

    def __init__(self, event_id: str = "") -> None:
        super().__init__(f"Audit event already exists: {event_id!r}")


class AuditReplayError(AuditError):
    code = "GA-033"

    def __init__(self, decision_id: str = "") -> None:
        super().__init__(f"Cannot replay audit for decision: {decision_id!r}")


# ── Policy ────────────────────────────────────────────────────────────────────
class PolicyError(GovernanceEngineError):
    code = "GA-040"


class PolicyNotFoundError(PolicyError):
    code = "GA-041"

    def __init__(self, policy_id: str = "") -> None:
        super().__init__(f"Policy not found: {policy_id!r}")


class PolicyAlreadyExistsError(PolicyError):
    code = "GA-042"

    def __init__(self, policy_id: str = "") -> None:
        super().__init__(f"Policy already exists: {policy_id!r}")


class PolicyViolationError(PolicyError):
    code = "GA-043"

    def __init__(self, policy_id: str = "", message: str = "") -> None:
        super().__init__(f"Policy {policy_id!r} violated: {message}")


class PolicyInvalidError(PolicyError):
    code = "GA-044"


class PolicyExecutionError(PolicyError):
    code = "GA-045"


# ── Engine Lifecycle ──────────────────────────────────────────────────────────
class EngineLifecycleError(GovernanceEngineError):
    code = "GA-050"


class EngineNotInitializedError(EngineLifecycleError):
    code = "GA-051"

    def __init__(self) -> None:
        super().__init__("DecisionGovernanceEngine is not initialized. Call initialize() first.")


class EngineAlreadyRunningError(EngineLifecycleError):
    code = "GA-052"

    def __init__(self) -> None:
        super().__init__("DecisionGovernanceEngine is already running.")


# ── Registry ──────────────────────────────────────────────────────────────────
class RegistryError(GovernanceEngineError):
    code = "GA-060"


class RegistryOverflowError(RegistryError):
    code = "GA-061"

    def __init__(self, limit: int) -> None:
        super().__init__(f"Registry capacity limit {limit} reached")


# ── Certification ─────────────────────────────────────────────────────────────
class CertificationError(GovernanceEngineError):
    code = "GA-070"


class CertificationNotFoundError(CertificationError):
    code = "GA-071"

    def __init__(self, cert_id: str = "") -> None:
        super().__init__(f"Certificate not found: {cert_id!r}")


class CertificationExpiredError(CertificationError):
    code = "GA-072"

    def __init__(self, cert_id: str = "") -> None:
        super().__init__(f"Certificate expired: {cert_id!r}")


class CertificationRevokedError(CertificationError):
    code = "GA-073"

    def __init__(self, cert_id: str = "") -> None:
        super().__init__(f"Certificate revoked: {cert_id!r}")


# ── Compliance ────────────────────────────────────────────────────────────────
class ComplianceError(GovernanceEngineError):
    code = "GA-080"


class ComplianceViolationError(ComplianceError):
    code = "GA-081"

    def __init__(self, rule: str = "") -> None:
        super().__init__(f"Compliance violation: {rule}")
