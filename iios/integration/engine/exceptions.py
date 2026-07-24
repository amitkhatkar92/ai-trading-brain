"""
exceptions.py — iios.integration.engine
-----------------------------------------
Exception hierarchy for the Integration Engine.

Error code prefix: IEN

C15 Enterprise Integration & Connectivity — Phase 1, Module 2
"""
from __future__ import annotations

from typing import List, Optional

from iios.common.errors.exceptions import IIOSError


class IntegrationEngineError(IIOSError):
    """IEN-000 — Base exception for all Integration Engine errors."""
    error_code = "IEN-000"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)


class IntegrationEngineNotReadyError(IntegrationEngineError):
    """IEN-001 — Engine is not in a state to accept requests."""
    error_code = "IEN-001"

    def __init__(
        self,
        message: str = "Integration engine is not ready",
        *,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code)


class ConnectorNotFoundError(IntegrationEngineError):
    """IEN-002 — No registered connector matches the requested type."""
    error_code = "IEN-002"

    def __init__(
        self,
        connector_id: str,
        *,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(
            f"Connector not found: {connector_id!r}",
            code=code,
        )
        self.connector_id = connector_id


class AdapterNotFoundError(IntegrationEngineError):
    """IEN-003 — No registered adapter matches the requested type."""
    error_code = "IEN-003"

    def __init__(
        self,
        adapter_id: str,
        *,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(
            f"Adapter not found: {adapter_id!r}",
            code=code,
        )
        self.adapter_id = adapter_id


class ProtocolNotRegisteredError(IntegrationEngineError):
    """IEN-004 — No registered protocol matches the requested protocol type."""
    error_code = "IEN-004"

    def __init__(
        self,
        protocol_type: str,
        *,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(
            f"Protocol not registered: {protocol_type!r}",
            code=code,
        )
        self.protocol_type = protocol_type


class IntegrationRequestValidationError(IntegrationEngineError):
    """IEN-005 — Integration request failed one or more validation checks."""
    error_code = "IEN-005"

    def __init__(
        self,
        message: str,
        *,
        failed_checks: Optional[List[str]] = None,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code)
        self.failed_checks = failed_checks or []


class IntegrationDispatchError(IntegrationEngineError):
    """IEN-006 — Error occurred during integration dispatch."""
    error_code = "IEN-006"

    def __init__(
        self,
        message: str,
        *,
        request_id: Optional[str] = None,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code)
        self.request_id = request_id


class IntegrationSessionError(IntegrationEngineError):
    """IEN-007 — Error creating or managing an integration session."""
    error_code = "IEN-007"


class ConnectorRegistrationError(IntegrationEngineError):
    """IEN-008 — Connector could not be registered."""
    error_code = "IEN-008"


class AdapterRegistrationError(IntegrationEngineError):
    """IEN-009 — Adapter could not be registered."""
    error_code = "IEN-009"
