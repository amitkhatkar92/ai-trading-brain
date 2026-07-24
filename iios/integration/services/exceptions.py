"""
exceptions.py — iios.integration.services
-------------------------------------------
Exception hierarchy for the Integration Services Framework.

Error code prefix: ISF

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Optional

from iios.common.errors.exceptions import IIOSError


class IntegrationServiceError(IIOSError):
    """ISF-000 — Base exception for all Integration Services errors."""
    error_code = "ISF-000"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)


class ServiceNotReadyError(IntegrationServiceError):
    """ISF-001 — Services engine is not started."""
    error_code = "ISF-001"

    def __init__(
        self, message: str = "Integration services engine not ready",
        *, code: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code)


class ConnectorNotFoundError(IntegrationServiceError):
    """ISF-002 — Connector not found in registry."""
    error_code = "ISF-002"

    def __init__(self, connector_id: str, *, code: Optional[str] = None) -> None:
        super().__init__(f"Connector not found: {connector_id!r}", code=code)
        self.connector_id = connector_id


class ConnectorExecutionError(IntegrationServiceError):
    """ISF-003 — Connector execution failed."""
    error_code = "ISF-003"

    def __init__(
        self, message: str, *, connector_id: Optional[str] = None,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code)
        self.connector_id = connector_id


class AdapterNotFoundError(IntegrationServiceError):
    """ISF-004 — Adapter not found in registry."""
    error_code = "ISF-004"

    def __init__(self, adapter_id: str, *, code: Optional[str] = None) -> None:
        super().__init__(f"Adapter not found: {adapter_id!r}", code=code)
        self.adapter_id = adapter_id


class AdapterExecutionError(IntegrationServiceError):
    """ISF-005 — Adapter execution failed."""
    error_code = "ISF-005"

    def __init__(
        self, message: str, *, adapter_id: Optional[str] = None,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code)
        self.adapter_id = adapter_id


class ProtocolExecutionError(IntegrationServiceError):
    """ISF-006 — Protocol execution failed."""
    error_code = "ISF-006"

    def __init__(
        self, message: str, *, protocol: Optional[str] = None,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code)
        self.protocol = protocol


class AuthenticationError(IntegrationServiceError):
    """ISF-007 — Authentication failed."""
    error_code = "ISF-007"

    def __init__(
        self, message: str = "Authentication failed",
        *, scheme: Optional[str] = None, code: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code)
        self.scheme = scheme


class AuthorizationError(IntegrationServiceError):
    """ISF-008 — Authorization failed."""
    error_code = "ISF-008"

    def __init__(
        self, message: str = "Authorization failed",
        *, code: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code)


class TransportError(IntegrationServiceError):
    """ISF-009 — Transport layer error."""
    error_code = "ISF-009"

    def __init__(
        self, message: str, *, transport: Optional[str] = None,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code)
        self.transport = transport


class RateLimitExceeded(IntegrationServiceError):
    """ISF-010 — Rate limit exceeded."""
    error_code = "ISF-010"

    def __init__(
        self, message: str = "Rate limit exceeded",
        *, retry_after_ms: int = 0, code: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code)
        self.retry_after_ms = retry_after_ms


class ConnectionPoolExhausted(IntegrationServiceError):
    """ISF-011 — Connection pool has no available connections."""
    error_code = "ISF-011"

    def __init__(
        self, message: str = "Connection pool exhausted",
        *, code: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code)


class ServiceTimeoutError(IntegrationServiceError):
    """ISF-012 — Service call timed out."""
    error_code = "ISF-012"

    def __init__(
        self, message: str = "Service call timed out",
        *, timeout_ms: int = 0, code: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code)
        self.timeout_ms = timeout_ms
