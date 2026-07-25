"""
exceptions.py — iios.workflow.policies
----------------------------------------
Exception hierarchy for the Workflow Governance Policy Framework.

Error code prefix: WGP

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 3
"""
from __future__ import annotations

from typing import List, Optional

from iios.common.errors.exceptions import IIOSError


class WorkflowPolicyError(IIOSError):
    """WGP-000 — Base exception for all governance policy errors."""
    error_code = "WGP-000"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)


class WorkflowPolicyNotFoundError(WorkflowPolicyError):
    """WGP-001 — Policy not found in registry."""
    error_code = "WGP-001"

    def __init__(
        self,
        policy_id: str = "",
        *,
        code: Optional[str] = None,
    ) -> None:
        msg = f"Policy not found: {policy_id!r}" if policy_id else "Policy not found"
        super().__init__(msg, code=code or self.error_code)
        self.policy_id = policy_id


class WorkflowPolicyValidationError(WorkflowPolicyError):
    """WGP-002 — Policy configuration validation failed."""
    error_code = "WGP-002"

    def __init__(
        self,
        message: str,
        *,
        issues: Optional[List[str]] = None,
        code:   Optional[str]       = None,
    ) -> None:
        super().__init__(message, code=code or self.error_code)
        self.issues: List[str] = issues or []


class WorkflowPolicyEvaluationError(WorkflowPolicyError):
    """WGP-003 — Policy evaluation failed."""
    error_code = "WGP-003"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)


class WorkflowPolicyConflictError(WorkflowPolicyError):
    """WGP-004 — Conflicting policies cannot be resolved."""
    error_code = "WGP-004"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)


class WorkflowGovernanceDecisionError(WorkflowPolicyError):
    """WGP-005 — Governance decision generation failed."""
    error_code = "WGP-005"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)


class WorkflowPolicyChainError(WorkflowPolicyError):
    """WGP-006 — Policy chain execution failed."""
    error_code = "WGP-006"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)


class WorkflowPolicyRegistryError(WorkflowPolicyError):
    """WGP-007 — Policy registry operation failed."""
    error_code = "WGP-007"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)


class WorkflowPolicyAuditError(WorkflowPolicyError):
    """WGP-008 — Audit trail generation failed."""
    error_code = "WGP-008"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)


class WorkflowPolicyEngineError(WorkflowPolicyError):
    """WGP-009 — Policy engine operation failed."""
    error_code = "WGP-009"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)


class WorkflowEmergencyStopError(WorkflowPolicyError):
    """WGP-010 — Emergency stop triggered by a critical governance policy."""
    error_code = "WGP-010"

    def __init__(
        self,
        message: str         = "Emergency stop triggered",
        *,
        policy_id: str       = "",
        code:      Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code or self.error_code)
        self.policy_id = policy_id
