"""
exceptions.py — iios.integration.policies
-------------------------------------------
Exception hierarchy for the Integration Governance Policy Framework.

Error code prefix: IPG

C15 Enterprise Integration & Connectivity — Phase 1, Module 3
"""
from __future__ import annotations

from typing import List, Optional

from iios.common.errors.exceptions import IIOSError


class IntegrationPolicyError(IIOSError):
    """IPG-000 — Base exception for all Policy Framework errors."""
    error_code = "IPG-000"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)


class PolicyEngineNotReadyError(IntegrationPolicyError):
    """IPG-001 — Policy engine is not started or is stopped."""
    error_code = "IPG-001"

    def __init__(
        self,
        message: str = "Policy engine is not ready",
        *,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code)


class PolicyNotFoundError(IntegrationPolicyError):
    """IPG-002 — Named policy not found in the registry."""
    error_code = "IPG-002"

    def __init__(self, policy_id: str, *, code: Optional[str] = None) -> None:
        super().__init__(f"Policy not found: {policy_id!r}", code=code)
        self.policy_id = policy_id


class PolicyRuleError(IntegrationPolicyError):
    """IPG-003 — A policy rule is invalid or inconsistent."""
    error_code = "IPG-003"

    def __init__(
        self,
        rule_id: str,
        reason:  str = "",
        *,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(f"Policy rule error [{rule_id!r}]: {reason}", code=code)
        self.rule_id = rule_id


class PolicyConditionError(IntegrationPolicyError):
    """IPG-004 — A policy condition is invalid."""
    error_code = "IPG-004"

    def __init__(
        self,
        condition_id: str,
        reason:       str = "",
        *,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(
            f"Policy condition error [{condition_id!r}]: {reason}", code=code
        )
        self.condition_id = condition_id


class PolicyValidationError(IntegrationPolicyError):
    """IPG-005 — Policy configuration failed validation."""
    error_code = "IPG-005"

    def __init__(
        self,
        message:       str,
        *,
        failed_checks: Optional[List[str]] = None,
        code:          Optional[str]       = None,
    ) -> None:
        super().__init__(message, code=code)
        self.failed_checks: List[str] = failed_checks or []


class PolicyConflictError(IntegrationPolicyError):
    """IPG-006 — Unresolvable conflict between governance policies."""
    error_code = "IPG-006"

    def __init__(
        self,
        message:    str,
        *,
        policy_ids: Optional[List[str]] = None,
        code:       Optional[str]       = None,
    ) -> None:
        super().__init__(message, code=code)
        self.policy_ids: List[str] = policy_ids or []


class PolicyEvaluationError(IntegrationPolicyError):
    """IPG-007 — Policy evaluation failed unexpectedly."""
    error_code = "IPG-007"

    def __init__(
        self,
        message:    str,
        *,
        request_id: Optional[str] = None,
        code:       Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code)
        self.request_id = request_id


class PolicyRegistrationError(IntegrationPolicyError):
    """IPG-008 — Policy could not be registered (e.g. registry at capacity)."""
    error_code = "IPG-008"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code)


class PolicyChainError(IntegrationPolicyError):
    """IPG-009 — Error in policy chain construction or execution."""
    error_code = "IPG-009"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code)
