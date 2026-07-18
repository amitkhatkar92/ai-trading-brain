"""
iios/execution/recovery/integration/exceptions.py
=================================================
Exception hierarchy for the Execution Recovery Integration (C7 M6).

Error codes: RI-000 … RI-009

C7 Execution Recovery & Resilience — Phase 1, Module 6
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class IntegrationError(IIOSError):
    """RI-000: Base exception for all Integration errors."""

    error_code = "RI-000"

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code=self.error_code, **kwargs)


class IntegrationNotRunningError(IntegrationError):
    """RI-001: API called before start() or after stop()."""

    error_code = "RI-001"

    def __init__(self, message: str = "Integration engine is not running"):
        super().__init__(message)


class IntegrationValidationError(IntegrationError):
    """RI-002: Request or context failed validation."""

    error_code = "RI-002"

    def __init__(self, message: str, *, errors: tuple = ()):
        super().__init__(message)
        self.errors: tuple = errors


class IntegrationRequestError(IntegrationError):
    """RI-003: Malformed or incomplete integration request."""

    error_code = "RI-003"

    def __init__(self, message: str, *, request_id: str = ""):
        super().__init__(message)
        self.request_id: str = request_id


class IntegrationSessionError(IntegrationError):
    """RI-004: Recovery session management error."""

    error_code = "RI-004"


class IntegrationComponentError(IntegrationError):
    """RI-005: A wired component is unavailable or failed."""

    error_code = "RI-005"

    def __init__(self, message: str, *, component: str = ""):
        super().__init__(message)
        self.component: str = component


class IntegrationHealthError(IntegrationError):
    """RI-006: Health check failed."""

    error_code = "RI-006"


class IntegrationSnapshotError(IntegrationError):
    """RI-007: Snapshot operation failed."""

    error_code = "RI-007"


class IntegrationHistoryError(IntegrationError):
    """RI-008: History operation failed."""

    error_code = "RI-008"


class IntegrationDuplicateError(IntegrationError):
    """RI-009: A request with the same ID was already submitted."""

    error_code = "RI-009"

    def __init__(self, request_id: str):
        super().__init__(f"Request already processed: {request_id!r}")
        self.request_id: str = request_id
