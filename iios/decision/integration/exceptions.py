"""
exceptions.py — iios.decision.integration
==========================================
Exception hierarchy for the Decision Integration subsystem.

Error code convention: DI-000 (base) through DI-009.

C9 Decision Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

from typing import Optional, Tuple

from iios.common.errors.exceptions import IIOSError


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class DecisionIntegrationError(IIOSError):
    """Base exception for all Decision Integration errors (DI-000)."""
    DEFAULT_CODE = "DI-000"
    error_code   = "DI-000"

    def __init__(self, message: str, **kwargs) -> None:
        super().__init__(message, code=self.error_code, **kwargs)


# ---------------------------------------------------------------------------
# Specific errors DI-001 through DI-009
# ---------------------------------------------------------------------------

class IntegrationNotRunningError(DecisionIntegrationError):
    """Integration engine is not running (DI-001)."""
    DEFAULT_CODE = "DI-001"
    error_code   = "DI-001"

    def __init__(self, message: str = "Decision integration engine is not running") -> None:
        super().__init__(message)


class IntegrationRequestError(DecisionIntegrationError):
    """Malformed or invalid integration request (DI-002)."""
    DEFAULT_CODE = "DI-002"
    error_code   = "DI-002"


class IntegrationValidationError(DecisionIntegrationError):
    """One or more validation checks failed (DI-003)."""
    DEFAULT_CODE  = "DI-003"
    error_code    = "DI-003"

    def __init__(
        self,
        message:       str,
        failed_checks: Tuple[str, ...] = (),
        **kwargs,
    ) -> None:
        super().__init__(message, **kwargs)
        self.failed_checks: Tuple[str, ...] = tuple(failed_checks)


class ComponentNotFoundError(DecisionIntegrationError):
    """A required component is not registered (DI-004)."""
    DEFAULT_CODE = "DI-004"
    error_code   = "DI-004"

    def __init__(self, component_id: str) -> None:
        super().__init__(f"Component not found: {component_id!r}")
        self.component_id: str = component_id


class ComponentNotReadyError(DecisionIntegrationError):
    """A required component is registered but not running/healthy (DI-005)."""
    DEFAULT_CODE = "DI-005"
    error_code   = "DI-005"

    def __init__(self, component_id: str, reason: str = "") -> None:
        msg = f"Component not ready: {component_id!r}"
        if reason:
            msg = f"{msg} — {reason}"
        super().__init__(msg)
        self.component_id: str = component_id


class IntegrationTimeoutError(DecisionIntegrationError):
    """An integration request exceeded its deadline (DI-006)."""
    DEFAULT_CODE = "DI-006"
    error_code   = "DI-006"


class IntegrationWorkflowError(DecisionIntegrationError):
    """The integration workflow encountered an unrecoverable error (DI-007)."""
    DEFAULT_CODE = "DI-007"
    error_code   = "DI-007"


class DuplicateIntegrationError(DecisionIntegrationError):
    """A request with this ID is already in flight (DI-008)."""
    DEFAULT_CODE      = "DI-008"
    error_code        = "DI-008"

    def __init__(self, integration_id: str) -> None:
        super().__init__(f"Duplicate integration request: {integration_id!r}")
        self.integration_id: str = integration_id


class IntegrationConfigurationError(DecisionIntegrationError):
    """Integration engine is misconfigured (DI-009)."""
    DEFAULT_CODE = "DI-009"
    error_code   = "DI-009"
