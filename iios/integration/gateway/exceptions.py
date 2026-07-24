"""
exceptions.py — iios.integration.gateway
------------------------------------------
Exception hierarchy for the Enterprise Integration Gateway.

Error code prefix: IGW

    IGW-000  IntegrationGatewayError      base
    IGW-001  GatewayNotReadyError         gateway not in ACTIVE state
    IGW-002  GatewayRequestValidationError request failed validation
    IGW-003  GatewayWorkflowError         workflow execution failed
    IGW-004  GatewayComponentError        required component unavailable
    IGW-005  GatewayLifecycleError        lifecycle coordination failed
    IGW-006  GatewayEngineError           engine coordination failed
    IGW-007  GatewayGovernanceError       governance coordination failed
    IGW-008  GatewayServicesError         services coordination failed
    IGW-009  GatewaySnapshotError         snapshot coordination failed
    IGW-010  GatewayCapacityError         gateway at capacity

C15 Enterprise Integration & Connectivity — Phase 1, Module 6
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class IntegrationGatewayError(IIOSError):
    """Base exception for all Enterprise Integration Gateway errors. (IGW-000)"""
    error_code = "IGW-000"

    def __init__(self, message: str = "Integration Gateway error", *, code: str = "") -> None:
        super().__init__(message, code=code or self.error_code)


class GatewayNotReadyError(IntegrationGatewayError):
    """Gateway is not in ACTIVE state. (IGW-001)"""
    error_code = "IGW-001"

    def __init__(self, message: str = "Gateway is not ready", *, code: str = "") -> None:
        super().__init__(message, code=code or self.error_code)


class GatewayRequestValidationError(IntegrationGatewayError):
    """Gateway request failed validation. (IGW-002)"""
    error_code = "IGW-002"

    def __init__(self, message: str = "Request validation failed", *, code: str = "") -> None:
        super().__init__(message, code=code or self.error_code)


class GatewayWorkflowError(IntegrationGatewayError):
    """Gateway workflow execution failed. (IGW-003)"""
    error_code = "IGW-003"

    def __init__(self, message: str = "Gateway workflow error", *, code: str = "") -> None:
        super().__init__(message, code=code or self.error_code)


class GatewayComponentError(IntegrationGatewayError):
    """Required gateway component is unavailable. (IGW-004)"""
    error_code = "IGW-004"

    def __init__(
        self,
        component: str = "",
        message: str = "",
        *,
        code: str = "",
    ) -> None:
        msg = message or (
            f"Component unavailable: {component!r}" if component else "Component unavailable"
        )
        super().__init__(msg, code=code or self.error_code)


class GatewayLifecycleError(IntegrationGatewayError):
    """Lifecycle coordination failed. (IGW-005)"""
    error_code = "IGW-005"

    def __init__(self, message: str = "Lifecycle coordination failed", *, code: str = "") -> None:
        super().__init__(message, code=code or self.error_code)


class GatewayEngineError(IntegrationGatewayError):
    """Engine coordination failed. (IGW-006)"""
    error_code = "IGW-006"

    def __init__(self, message: str = "Engine coordination failed", *, code: str = "") -> None:
        super().__init__(message, code=code or self.error_code)


class GatewayGovernanceError(IntegrationGatewayError):
    """Governance coordination failed. (IGW-007)"""
    error_code = "IGW-007"

    def __init__(self, message: str = "Governance coordination failed", *, code: str = "") -> None:
        super().__init__(message, code=code or self.error_code)


class GatewayServicesError(IntegrationGatewayError):
    """Services coordination failed. (IGW-008)"""
    error_code = "IGW-008"

    def __init__(self, message: str = "Services coordination failed", *, code: str = "") -> None:
        super().__init__(message, code=code or self.error_code)


class GatewaySnapshotError(IntegrationGatewayError):
    """Snapshot coordination failed. (IGW-009)"""
    error_code = "IGW-009"

    def __init__(self, message: str = "Snapshot coordination failed", *, code: str = "") -> None:
        super().__init__(message, code=code or self.error_code)


class GatewayCapacityError(IntegrationGatewayError):
    """Gateway has reached its active-request capacity. (IGW-010)"""
    error_code = "IGW-010"

    def __init__(self, message: str = "Gateway capacity exceeded", *, code: str = "") -> None:
        super().__init__(message, code=code or self.error_code)
