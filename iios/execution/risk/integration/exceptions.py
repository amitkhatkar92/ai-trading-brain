"""iios/execution/risk/integration/exceptions.py
==================================================
Exception hierarchy for the Execution Risk Integration subsystem.

Hierarchy
---------
IIOSError
└── ExecutionRiskIntegrationError     ERI-000  base
    ├── IntegrationNotRunningError    ERI-001
    ├── RequestValidationError        ERI-002
    ├── EvaluationFailedError         ERI-003
    ├── ComponentNotHealthyError      ERI-004
    ├── IntegrationTimeoutError       ERI-005
    ├── ComponentRegistrationError    ERI-006
    ├── ContextValidationError        ERI-007
    └── IntegrationHistoryError       ERI-008

C6 Execution Intelligence — Phase 4, Module 6
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class ExecutionRiskIntegrationError(IIOSError):
    """ERI-000 — Base exception for all integration errors."""
    error_code: str = "ERI-000"


class IntegrationNotRunningError(ExecutionRiskIntegrationError):
    """ERI-001 — Operation requested on a non-running integration engine."""
    error_code: str = "ERI-001"

    def __init__(self) -> None:
        super().__init__(
            "ExecutionRiskIntegrationEngine is not running — call start() first",
            code=self.error_code,
        )


class RequestValidationError(ExecutionRiskIntegrationError):
    """ERI-002 — The submitted ExecutionRiskRequest failed validation."""
    error_code: str = "ERI-002"

    def __init__(self, message: str) -> None:
        super().__init__(message, code=self.error_code)
        self.message = message


class EvaluationFailedError(ExecutionRiskIntegrationError):
    """ERI-003 — An exception occurred during the evaluation workflow."""
    error_code: str = "ERI-003"

    def __init__(self, message: str) -> None:
        super().__init__(message, code=self.error_code)
        self.message = message


class ComponentNotHealthyError(ExecutionRiskIntegrationError):
    """ERI-004 — A required subsystem component is not healthy or not running."""
    error_code: str = "ERI-004"

    def __init__(self, component_type: str) -> None:
        super().__init__(
            f"Component '{component_type}' is not healthy or not running",
            code=self.error_code,
        )
        self.component_type = component_type


class IntegrationTimeoutError(ExecutionRiskIntegrationError):
    """ERI-005 — An evaluation exceeded its permitted time budget."""
    error_code: str = "ERI-005"

    def __init__(self, message: str) -> None:
        super().__init__(message, code=self.error_code)
        self.message = message


class ComponentRegistrationError(ExecutionRiskIntegrationError):
    """ERI-006 — A component could not be registered or is not registered."""
    error_code: str = "ERI-006"

    def __init__(self, message: str) -> None:
        super().__init__(message, code=self.error_code)
        self.message = message


class ContextValidationError(ExecutionRiskIntegrationError):
    """ERI-007 — The supplied ExecutionContext is invalid or inconsistent."""
    error_code: str = "ERI-007"

    def __init__(self, message: str) -> None:
        super().__init__(message, code=self.error_code)
        self.message = message


class IntegrationHistoryError(ExecutionRiskIntegrationError):
    """ERI-008 — An error occurred while accessing integration history."""
    error_code: str = "ERI-008"

    def __init__(self, message: str) -> None:
        super().__init__(message, code=self.error_code)
        self.message = message
