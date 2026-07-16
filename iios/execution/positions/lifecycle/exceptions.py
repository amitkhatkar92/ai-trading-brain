"""iios/execution/positions/lifecycle/exceptions.py
==================================================
Exception hierarchy for the IIOS Position Lifecycle layer.

Error Codes
-----------
PL-000  PositionLifecycleError        — base
PL-001  InvalidTransitionError        — state transition not allowed
PL-002  PositionNotFoundError         — position_id does not exist
PL-003  DuplicatePositionError        — position_id already registered
PL-004  PositionValidationError       — field or invariant violation
PL-005  PositionRegistryCapacityError — registry at max capacity
PL-006  PositionNotRunningError       — registry is not started
PL-007  PositionStateError            — position is in an unexpected state

C6 Execution Intelligence — Phase 3, Module 1
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from iios.common.errors.exceptions import IIOSError

from .constants import PositionState


class PositionLifecycleError(IIOSError):
    """Base for all Position Lifecycle errors."""
    DEFAULT_CODE = "PL-000"


class InvalidTransitionError(PositionLifecycleError):
    """The requested state transition is not permitted by the state machine."""
    DEFAULT_CODE = "PL-001"

    def __init__(
        self,
        position_id: str,
        from_state: PositionState,
        to_state: PositionState,
        *,
        code:           str = "PL-001",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Transition '{from_state.value}' → '{to_state.value}' is not allowed "
            f"for position '{position_id}'",
            code=code,
            context=context or {"position_id": position_id, "from": from_state.value, "to": to_state.value},
            correlation_id=correlation_id,
        )
        self.position_id = position_id
        self.from_state  = from_state
        self.to_state    = to_state


class PositionNotFoundError(PositionLifecycleError):
    """No position found for the given identifier."""
    DEFAULT_CODE = "PL-002"

    def __init__(
        self,
        position_id: str,
        *,
        code:           str = "PL-002",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Position '{position_id}' not found",
            code=code,
            context=context or {"position_id": position_id},
            correlation_id=correlation_id,
        )
        self.position_id = position_id


class DuplicatePositionError(PositionLifecycleError):
    """A position with this ID is already registered."""
    DEFAULT_CODE = "PL-003"

    def __init__(
        self,
        position_id: str,
        *,
        code:           str = "PL-003",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Position '{position_id}' is already registered",
            code=code,
            context=context or {"position_id": position_id},
            correlation_id=correlation_id,
        )
        self.position_id = position_id


class PositionValidationError(PositionLifecycleError):
    """A position field or invariant failed validation."""
    DEFAULT_CODE = "PL-004"

    def __init__(
        self,
        message: str,
        *,
        code:           str = "PL-004",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            message,
            code=code,
            context=context,
            correlation_id=correlation_id,
        )


class PositionRegistryCapacityError(PositionLifecycleError):
    """The registry has reached its maximum number of positions."""
    DEFAULT_CODE = "PL-005"

    def __init__(
        self,
        max_positions: int,
        *,
        code:           str = "PL-005",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Position registry is at capacity ({max_positions})",
            code=code,
            context=context or {"max_positions": max_positions},
            correlation_id=correlation_id,
        )
        self.max_positions = max_positions


class PositionNotRunningError(PositionLifecycleError):
    """The registry is not in the RUNNING state."""
    DEFAULT_CODE = "PL-006"

    def __init__(
        self,
        *,
        code:           str = "PL-006",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            "PositionRegistry is not running",
            code=code,
            context=context,
            correlation_id=correlation_id,
        )


class PositionStateError(PositionLifecycleError):
    """The position is in an unexpected or incompatible state."""
    DEFAULT_CODE = "PL-007"

    def __init__(
        self,
        position_id: str,
        current_state: PositionState,
        message: str = "",
        *,
        code:           str = "PL-007",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        detail = message or f"Position '{position_id}' is in unexpected state '{current_state.value}'"
        super().__init__(
            detail,
            code=code,
            context=context or {"position_id": position_id, "state": current_state.value},
            correlation_id=correlation_id,
        )
        self.position_id    = position_id
        self.current_state  = current_state
