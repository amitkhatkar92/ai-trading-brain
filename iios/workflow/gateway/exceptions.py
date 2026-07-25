"""
exceptions.py — iios.workflow.gateway
--------------------------------------
Exception hierarchy for the Enterprise Workflow Gateway.

Error codes: WGW-000 through WGW-011

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 6
"""
from __future__ import annotations

from typing import List

from iios.common.errors.exceptions import IIOSError


class WorkflowGatewayError(IIOSError):
    """Base exception for all Workflow Gateway errors."""
    error_code = "WGW-000"

    def __init__(self, message: str, *, code: str = "") -> None:
        super().__init__(message, code=code or self.error_code)


class WorkflowGatewayNotInitializedError(WorkflowGatewayError):
    """Gateway has not been initialized."""
    error_code = "WGW-001"

    def __init__(self, message: str = "Workflow Gateway is not initialized") -> None:
        super().__init__(message)


class WorkflowGatewayNotRunningError(WorkflowGatewayError):
    """Gateway is not in a running state."""
    error_code = "WGW-002"

    def __init__(self, message: str = "Workflow Gateway is not running") -> None:
        super().__init__(message)


class WorkflowGatewayValidationError(WorkflowGatewayError):
    """Gateway request or response validation failed."""
    error_code = "WGW-003"

    def __init__(self, message: str, *, issues: List[str] = None) -> None:
        super().__init__(message)
        self.issues: List[str] = list(issues or [])


class WorkflowGatewayRequestError(WorkflowGatewayError):
    """Invalid or malformed gateway request."""
    error_code = "WGW-004"


class WorkflowGatewayResponseError(WorkflowGatewayError):
    """Gateway response could not be constructed."""
    error_code = "WGW-005"


class WorkflowGatewayRoutingError(WorkflowGatewayError):
    """Gateway could not route the request."""
    error_code = "WGW-006"


class WorkflowGatewayDispatchError(WorkflowGatewayError):
    """Gateway dispatch to a subsystem failed."""
    error_code = "WGW-007"


class WorkflowGatewayComponentError(WorkflowGatewayError):
    """A required integrated component is unavailable or misconfigured."""
    error_code = "WGW-008"

    def __init__(self, message: str, *, component: str = "") -> None:
        super().__init__(message)
        self.component = component


class WorkflowGatewayHistoryError(WorkflowGatewayError):
    """Gateway history operation failed."""
    error_code = "WGW-009"


class WorkflowGatewayStatisticsError(WorkflowGatewayError):
    """Gateway statistics operation failed."""
    error_code = "WGW-010"


class WorkflowGatewayTimeoutError(WorkflowGatewayError):
    """Gateway request exceeded the allowed time budget."""
    error_code = "WGW-011"

    def __init__(self, message: str = "Workflow Gateway request timed out") -> None:
        super().__init__(message)
