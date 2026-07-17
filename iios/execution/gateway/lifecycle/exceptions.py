"""iios/execution/gateway/lifecycle/exceptions.py
==================================================
Exception hierarchy for the IIOS Execution Gateway Lifecycle layer.

Error Codes
-----------
EGL-000  ExecutionGatewayLifecycleError    — base
EGL-001  InvalidGatewayTransitionError     — transition not permitted
EGL-002  GatewayRequestNotFoundError       — gateway_id not in registry
EGL-003  DuplicateGatewayRequestError      — gateway_id already registered
EGL-004  GatewayValidationError            — field or invariant violation
EGL-005  GatewayRegistryCapacityError      — registry at max capacity
EGL-006  GatewayLifecycleNotRunningError   — lifecycle manager not started
EGL-007  GatewayStateError                 — request is in unexpected state

C6 Execution Intelligence — Phase 5, Module 1
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from iios.common.errors.exceptions import IIOSError

from .constants import GatewayState


class ExecutionGatewayLifecycleError(IIOSError):
    """Base for all Execution Gateway Lifecycle errors."""
    DEFAULT_CODE = "EGL-000"


class InvalidGatewayTransitionError(ExecutionGatewayLifecycleError):
    """The requested state transition is not permitted by the state machine."""
    DEFAULT_CODE = "EGL-001"

    def __init__(
        self,
        gateway_id: str,
        from_state: GatewayState,
        to_state:   GatewayState,
        *,
        code:           str                            = "EGL-001",
        context:        Optional[Dict[str, Any]]       = None,
        correlation_id: str                            = "",
    ) -> None:
        super().__init__(
            f"Transition '{from_state.value}' → '{to_state.value}' is not allowed "
            f"for gateway request '{gateway_id}'",
            code=code,
            context=context or {
                "gateway_id": gateway_id,
                "from":       from_state.value,
                "to":         to_state.value,
            },
            correlation_id=correlation_id,
        )
        self.gateway_id = gateway_id
        self.from_state = from_state
        self.to_state   = to_state


class GatewayRequestNotFoundError(ExecutionGatewayLifecycleError):
    """No gateway request found for the given identifier."""
    DEFAULT_CODE = "EGL-002"

    def __init__(
        self,
        gateway_id: str,
        *,
        code:           str                            = "EGL-002",
        context:        Optional[Dict[str, Any]]       = None,
        correlation_id: str                            = "",
    ) -> None:
        super().__init__(
            f"Gateway request '{gateway_id}' not found",
            code=code,
            context=context or {"gateway_id": gateway_id},
            correlation_id=correlation_id,
        )
        self.gateway_id = gateway_id


class DuplicateGatewayRequestError(ExecutionGatewayLifecycleError):
    """A gateway request with this ID is already registered."""
    DEFAULT_CODE = "EGL-003"

    def __init__(
        self,
        gateway_id: str,
        *,
        code:           str                            = "EGL-003",
        context:        Optional[Dict[str, Any]]       = None,
        correlation_id: str                            = "",
    ) -> None:
        super().__init__(
            f"Gateway request '{gateway_id}' is already registered",
            code=code,
            context=context or {"gateway_id": gateway_id},
            correlation_id=correlation_id,
        )
        self.gateway_id = gateway_id


class GatewayValidationError(ExecutionGatewayLifecycleError):
    """A field or lifecycle invariant has been violated."""
    DEFAULT_CODE = "EGL-004"

    def __init__(
        self,
        message: str,
        *,
        code:           str                            = "EGL-004",
        context:        Optional[Dict[str, Any]]       = None,
        correlation_id: str                            = "",
    ) -> None:
        super().__init__(
            message,
            code=code,
            context=context or {},
            correlation_id=correlation_id,
        )
        self.message = message


class GatewayRegistryCapacityError(ExecutionGatewayLifecycleError):
    """The registry has reached its maximum capacity."""
    DEFAULT_CODE = "EGL-005"

    def __init__(
        self,
        max_capacity: int,
        *,
        code:           str                            = "EGL-005",
        context:        Optional[Dict[str, Any]]       = None,
        correlation_id: str                            = "",
    ) -> None:
        super().__init__(
            f"Gateway registry is at maximum capacity ({max_capacity})",
            code=code,
            context=context or {"max_capacity": max_capacity},
            correlation_id=correlation_id,
        )
        self.max_capacity = max_capacity


class GatewayLifecycleNotRunningError(ExecutionGatewayLifecycleError):
    """The gateway lifecycle manager has not been started."""
    DEFAULT_CODE = "EGL-006"

    def __init__(
        self,
        *,
        code:           str = "EGL-006",
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            "Gateway lifecycle manager is not running. Call start() before use.",
            code=code,
            correlation_id=correlation_id,
        )


class GatewayStateError(ExecutionGatewayLifecycleError):
    """A gateway request is in an unexpected state for the requested operation."""
    DEFAULT_CODE = "EGL-007"

    def __init__(
        self,
        gateway_id:    str,
        current_state: GatewayState,
        message:       str = "",
        *,
        code:           str                            = "EGL-007",
        context:        Optional[Dict[str, Any]]       = None,
        correlation_id: str                            = "",
    ) -> None:
        detail = message or f"Unexpected state '{current_state.value}'"
        super().__init__(
            f"Gateway request '{gateway_id}': {detail}",
            code=code,
            context=context or {
                "gateway_id":    gateway_id,
                "current_state": current_state.value,
            },
            correlation_id=correlation_id,
        )
        self.gateway_id    = gateway_id
        self.current_state = current_state
