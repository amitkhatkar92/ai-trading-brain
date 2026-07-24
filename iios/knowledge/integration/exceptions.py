"""
exceptions.py — iios.knowledge.integration
-------------------------------------------
Exception hierarchy for the Knowledge Integration module.

Error code prefix: KIN

C14 Enterprise Knowledge Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

from typing import List, Optional

from iios.common.errors.exceptions import IIOSError


class KnowledgeIntegrationError(IIOSError):
    """KIN-000 — Base exception for all Knowledge Integration errors."""
    error_code = "KIN-000"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)


class IntegrationRequestError(KnowledgeIntegrationError):
    """KIN-001 — Malformed or incomplete integration request."""
    error_code = "KIN-001"


class IntegrationValidationError(KnowledgeIntegrationError):
    """KIN-002 — Integration validation failed."""
    error_code = "KIN-002"

    def __init__(
        self,
        message: str,
        *,
        failed_checks: Optional[List[str]] = None,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code)
        self.failed_checks: List[str] = failed_checks or []


class IntegrationExecutionError(KnowledgeIntegrationError):
    """KIN-003 — Error during integration workflow execution."""
    error_code = "KIN-003"


class IntegrationComponentError(KnowledgeIntegrationError):
    """KIN-004 — A required subsystem component failed or is unavailable."""
    error_code = "KIN-004"

    def __init__(
        self,
        message: str,
        *,
        component: Optional[str] = None,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code)
        self.component: Optional[str] = component


class IntegrationTimeoutError(KnowledgeIntegrationError):
    """KIN-005 — Integration operation timed out."""
    error_code = "KIN-005"

    def __init__(
        self,
        message: str,
        *,
        timeout_ms: Optional[int] = None,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code)
        self.timeout_ms: Optional[int] = timeout_ms


class IntegrationStateError(KnowledgeIntegrationError):
    """KIN-006 — Operation not valid in the current integration state."""
    error_code = "KIN-006"

    def __init__(
        self,
        message: str,
        *,
        current_state: Optional[str] = None,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code)
        self.current_state: Optional[str] = current_state


class IntegrationCapacityError(KnowledgeIntegrationError):
    """KIN-007 — Integration storage or request capacity exceeded."""
    error_code = "KIN-007"

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        limit: Optional[int] = None,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message or f"Integration capacity limit reached: {limit}", code=code)
        self.limit: Optional[int] = limit


class IntegrationSnapshotError(KnowledgeIntegrationError):
    """KIN-008 — Error generating or validating the Knowledge Snapshot."""
    error_code = "KIN-008"
