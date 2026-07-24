"""
exceptions.py — iios.knowledge.policies
-----------------------------------------
Typed exception hierarchy for the Knowledge Governance Policy Framework.

Error code prefix: KGP (Knowledge Governance Policy)

C14 Enterprise Knowledge Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class KnowledgeGovernanceError(IIOSError):
    """Base for all Knowledge Governance Policy errors."""
    error_code = "KGP-000"

    def __init__(self, message: str = "", code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


# ---------------------------------------------------------------------------
# Specific errors
# ---------------------------------------------------------------------------


class GovernanceNotRunningError(KnowledgeGovernanceError):
    """Raised when an operation requires the governance engine to be running."""
    error_code = "KGP-001"

    def __init__(self, message: str = "Knowledge Governance Engine is not running") -> None:
        super().__init__(message)


class GovernanceValidationError(KnowledgeGovernanceError):
    """Raised when governance-level structural validation fails."""
    error_code = "KGP-002"


class PolicyLoadError(KnowledgeGovernanceError):
    """Raised when a policy cannot be loaded or registered."""
    error_code = "KGP-003"

    def __init__(
        self,
        message:   str = "",
        policy_id: str = "",
        code:      str | None = None,
    ) -> None:
        super().__init__(message, code=code)
        self.policy_id = policy_id


class PolicyEvaluationError(KnowledgeGovernanceError):
    """Raised when policy evaluation fails unexpectedly."""
    error_code = "KGP-004"

    def __init__(
        self,
        message:   str = "",
        policy_id: str = "",
        code:      str | None = None,
    ) -> None:
        super().__init__(message, code=code)
        self.policy_id = policy_id


class PolicyConflictError(KnowledgeGovernanceError):
    """Raised when irreconcilable policy conflicts are detected."""
    error_code = "KGP-005"


class PolicyNotFoundError(KnowledgeGovernanceError):
    """Raised when a requested policy does not exist in the registry."""
    error_code = "KGP-006"

    def __init__(
        self,
        message:   str = "",
        policy_id: str = "",
        code:      str | None = None,
    ) -> None:
        super().__init__(message or f"Policy not found: {policy_id!r}", code=code)
        self.policy_id = policy_id


class GovernanceCapacityError(KnowledgeGovernanceError):
    """Raised when registry or audit capacity is exceeded."""
    error_code = "KGP-007"

    def __init__(
        self,
        message: str = "",
        limit:   int = 0,
        code:    str | None = None,
    ) -> None:
        super().__init__(message or f"Capacity limit reached: {limit}", code=code)
        self.limit = limit


class AuditError(KnowledgeGovernanceError):
    """Raised when audit recording fails."""
    error_code = "KGP-008"


class PolicyChainError(KnowledgeGovernanceError):
    """Raised when a policy chain operation fails."""
    error_code = "KGP-009"

    def __init__(
        self,
        message:  str = "",
        chain_id: str = "",
        code:     str | None = None,
    ) -> None:
        super().__init__(message, code=code)
        self.chain_id = chain_id
