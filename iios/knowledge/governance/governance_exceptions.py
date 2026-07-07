"""
iios/knowledge/governance/governance_exceptions.py
===================================================
Exception hierarchy for the Knowledge Governance Engine.
"""

from __future__ import annotations

from ..knowledge_exceptions import KnowledgeError

__all__ = [
    "GovernanceError",
    "ApprovalError",
    "ApprovalNotFoundError",
    "ApprovalAlreadyExistsError",
    "ApprovalRejectedError",
    "PolicyError",
    "PolicyNotFoundError",
    "PolicyAlreadyExistsError",
    "PolicyViolationError",
    "CertificationError",
    "CertificationNotFoundError",
    "CertificationExpiredError",
    "GovernanceAuditError",
    "KnowledgeGovernorError",
]


class GovernanceError(KnowledgeError):
    """Base for all governance engine errors."""
    def __init__(self, message: str, code: str = "GE-000") -> None:
        super().__init__(message, code=code)


class ApprovalError(GovernanceError):
    """General approval workflow error."""
    def __init__(self, message: str, code: str = "GE-100") -> None:
        super().__init__(message, code=code)


class ApprovalNotFoundError(ApprovalError):
    """Requested governance record does not exist."""
    def __init__(self, message: str, code: str = "GE-101") -> None:
        super().__init__(message, code=code)


class ApprovalAlreadyExistsError(ApprovalError):
    """An active governance record already exists for this item."""
    def __init__(self, message: str, code: str = "GE-102") -> None:
        super().__init__(message, code=code)


class ApprovalRejectedError(ApprovalError):
    """Knowledge was rejected by governance and cannot enter the knowledge base."""
    def __init__(self, message: str, reason: str = "",
                 code: str = "GE-103") -> None:
        super().__init__(message, code=code)
        self.reason = reason


class PolicyError(GovernanceError):
    """General policy management error."""
    def __init__(self, message: str, code: str = "GE-200") -> None:
        super().__init__(message, code=code)


class PolicyNotFoundError(PolicyError):
    """Requested policy does not exist."""
    def __init__(self, message: str, code: str = "GE-201") -> None:
        super().__init__(message, code=code)


class PolicyAlreadyExistsError(PolicyError):
    """Policy with this ID already exists."""
    def __init__(self, message: str, code: str = "GE-202") -> None:
        super().__init__(message, code=code)


class PolicyViolationError(PolicyError):
    """A governance policy was violated."""
    def __init__(self, message: str, policy_id: str = "",
                 code: str = "GE-203") -> None:
        super().__init__(message, code=code)
        self.policy_id = policy_id


class CertificationError(GovernanceError):
    """General certification error."""
    def __init__(self, message: str, code: str = "GE-300") -> None:
        super().__init__(message, code=code)


class CertificationNotFoundError(CertificationError):
    """No certification found for the requested knowledge item."""
    def __init__(self, message: str, code: str = "GE-301") -> None:
        super().__init__(message, code=code)


class CertificationExpiredError(CertificationError):
    """The certification for this knowledge item has expired."""
    def __init__(self, message: str, code: str = "GE-302") -> None:
        super().__init__(message, code=code)


class GovernanceAuditError(GovernanceError):
    """Governance audit log error."""
    def __init__(self, message: str, code: str = "GE-400") -> None:
        super().__init__(message, code=code)


class KnowledgeGovernorError(GovernanceError):
    """High-level knowledge governor error."""
    def __init__(self, message: str, code: str = "GE-900") -> None:
        super().__init__(message, code=code)
