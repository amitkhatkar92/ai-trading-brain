"""
exceptions.py — iios.risk.integration
=========================================
Error hierarchy for the Risk Integration layer.

Error codes use the RI- prefix (Risk Integration):
  RI-000  Base
  RI-001  Engine not running
  RI-002  Request error
  RI-003  Validation error
  RI-004  Component error
  RI-005  Snapshot error
  RI-006  Workflow error
  RI-007  Capacity exceeded
  RI-008  Timeout
  RI-009  Configuration error

C11 Risk Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class RiskIntegrationError(IIOSError):
    """Base exception for all Risk Integration errors."""
    error_code: str = "RI-000"

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


class RiskIntegrationNotRunningError(RiskIntegrationError):
    """Raised when the integration engine is not in the running state."""
    error_code = "RI-001"


class RiskIntegrationRequestError(RiskIntegrationError):
    """Raised when a request is malformed or cannot be processed."""
    error_code = "RI-002"


class RiskIntegrationValidationError(RiskIntegrationError):
    """Raised when integration validation fails."""
    error_code = "RI-003"


class RiskIntegrationComponentError(RiskIntegrationError):
    """Raised when a required subsystem component is unavailable."""
    error_code = "RI-004"


class RiskIntegrationSnapshotError(RiskIntegrationError):
    """Raised when snapshot publication fails."""
    error_code = "RI-005"


class RiskIntegrationWorkflowError(RiskIntegrationError):
    """Raised when the integration workflow encounters an unrecoverable error."""
    error_code = "RI-006"


class RiskIntegrationCapacityError(RiskIntegrationError):
    """Raised when integration capacity is exceeded."""
    error_code = "RI-007"


class RiskIntegrationTimeoutError(RiskIntegrationError):
    """Raised when an integration request exceeds its timeout."""
    error_code = "RI-008"


class RiskIntegrationConfigurationError(RiskIntegrationError):
    """Raised when integration configuration is invalid."""
    error_code = "RI-009"
