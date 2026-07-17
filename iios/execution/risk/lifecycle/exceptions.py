"""iios/execution/risk/lifecycle/exceptions.py
==================================================
Exception hierarchy for the IIOS Execution Risk Lifecycle layer.

Error Codes
-----------
ERL-000  ExecutionRiskLifecycleError   — base
ERL-001  InvalidRiskTransitionError    — state transition not allowed
ERL-002  RiskNotFoundError             — risk_id does not exist
ERL-003  DuplicateRiskError            — risk_id already registered
ERL-004  RiskValidationError           — field or invariant violation
ERL-005  RiskRegistryCapacityError     — registry at max capacity
ERL-006  RiskRegistryNotRunningError   — registry is not started
ERL-007  RiskStateError                — risk is in an unexpected state

C6 Execution Intelligence — Phase 4, Module 1
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from iios.common.errors.exceptions import IIOSError

from .constants import RiskState


class ExecutionRiskLifecycleError(IIOSError):
    """Base for all Execution Risk Lifecycle errors."""
    DEFAULT_CODE = "ERL-000"


class InvalidRiskTransitionError(ExecutionRiskLifecycleError):
    """The requested state transition is not permitted by the state machine."""
    DEFAULT_CODE = "ERL-001"

    def __init__(
        self,
        risk_id:    str,
        from_state: RiskState,
        to_state:   RiskState,
        *,
        code:           str = "ERL-001",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Transition '{from_state.value}' → '{to_state.value}' is not allowed "
            f"for risk evaluation '{risk_id}'",
            code=code,
            context=context or {
                "risk_id": risk_id,
                "from":    from_state.value,
                "to":      to_state.value,
            },
            correlation_id=correlation_id,
        )
        self.risk_id    = risk_id
        self.from_state = from_state
        self.to_state   = to_state


class RiskNotFoundError(ExecutionRiskLifecycleError):
    """No risk evaluation found for the given identifier."""
    DEFAULT_CODE = "ERL-002"

    def __init__(
        self,
        risk_id: str,
        *,
        code:           str = "ERL-002",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Risk evaluation '{risk_id}' not found",
            code=code,
            context=context or {"risk_id": risk_id},
            correlation_id=correlation_id,
        )
        self.risk_id = risk_id


class DuplicateRiskError(ExecutionRiskLifecycleError):
    """A risk evaluation with this ID is already registered."""
    DEFAULT_CODE = "ERL-003"

    def __init__(
        self,
        risk_id: str,
        *,
        code:           str = "ERL-003",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Risk evaluation '{risk_id}' is already registered",
            code=code,
            context=context or {"risk_id": risk_id},
            correlation_id=correlation_id,
        )
        self.risk_id = risk_id


class RiskValidationError(ExecutionRiskLifecycleError):
    """A field or invariant validation failed."""
    DEFAULT_CODE = "ERL-004"

    def __init__(
        self,
        message: str,
        *,
        code:           str = "ERL-004",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            message,
            code=code,
            context=context,
            correlation_id=correlation_id,
        )


class RiskRegistryCapacityError(ExecutionRiskLifecycleError):
    """The registry has reached its maximum capacity."""
    DEFAULT_CODE = "ERL-005"

    def __init__(
        self,
        max_capacity: int,
        *,
        code:           str = "ERL-005",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"RiskRegistry is at maximum capacity ({max_capacity})",
            code=code,
            context=context or {"max_capacity": max_capacity},
            correlation_id=correlation_id,
        )
        self.max_capacity = max_capacity


class RiskRegistryNotRunningError(ExecutionRiskLifecycleError):
    """The registry has not been started."""
    DEFAULT_CODE = "ERL-006"

    def __init__(
        self,
        *,
        code:           str = "ERL-006",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            "RiskRegistry is not running; call start() before use",
            code=code,
            context=context,
            correlation_id=correlation_id,
        )


class RiskStateError(ExecutionRiskLifecycleError):
    """A risk evaluation is in an unexpected state."""
    DEFAULT_CODE = "ERL-007"

    def __init__(
        self,
        risk_id:        str,
        expected_state: RiskState,
        actual_state:   RiskState,
        *,
        code:           str = "ERL-007",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Risk evaluation '{risk_id}' is in state '{actual_state.value}'; "
            f"expected '{expected_state.value}'",
            code=code,
            context=context or {
                "risk_id":        risk_id,
                "expected_state": expected_state.value,
                "actual_state":   actual_state.value,
            },
            correlation_id=correlation_id,
        )
        self.risk_id        = risk_id
        self.expected_state = expected_state
        self.actual_state   = actual_state
