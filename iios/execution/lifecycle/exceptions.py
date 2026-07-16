"""iios/execution/lifecycle/exceptions.py
==================================================
Order Lifecycle exception hierarchy.

All exceptions inherit from IIOSError so they integrate
with the platform ErrorManager and are distinguishable
from third-party exceptions in catch-all handlers.

Error code prefix: EL  (Execution Lifecycle)
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from iios.common.errors.exceptions import IIOSError


class OrderLifecycleError(IIOSError):
    """Base class for all order lifecycle errors."""
    DEFAULT_CODE = "EL-000"


class InvalidTransitionError(OrderLifecycleError):
    """
    Raised when a requested state transition is not permitted
    by the canonical state machine transition table.
    """
    DEFAULT_CODE = "EL-001"

    def __init__(
        self,
        from_state: str,
        to_state:   str,
        order_id:   str = "",
        *,
        code:           str = "",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        message = (
            f"Invalid transition: {from_state!r} → {to_state!r}"
            + (f" (order_id={order_id!r})" if order_id else "")
        )
        super().__init__(
            message,
            code           = code or self.DEFAULT_CODE,
            context        = context or {"from_state": from_state, "to_state": to_state,
                                         "order_id": order_id},
            correlation_id = correlation_id,
        )
        self.from_state = from_state
        self.to_state   = to_state
        self.order_id   = order_id


class OrderNotFoundError(OrderLifecycleError):
    """Raised when a requested order does not exist in the registry."""
    DEFAULT_CODE = "EL-002"


class OrderValidationError(OrderLifecycleError):
    """Raised when an order fails structural or business validation."""
    DEFAULT_CODE = "EL-003"


class DuplicateOrderError(OrderLifecycleError):
    """Raised when registering an order_id that is already present."""
    DEFAULT_CODE = "EL-004"


class RegistryCapacityError(OrderLifecycleError):
    """Raised when the registry has reached its maximum order capacity."""
    DEFAULT_CODE = "EL-005"


class OrderTerminalError(OrderLifecycleError):
    """
    Raised when a transition is attempted on an order in a
    terminal state (e.g. FILLED has no outgoing transitions).
    """
    DEFAULT_CODE = "EL-006"


class InvalidFillError(OrderLifecycleError):
    """
    Raised when a fill event is inconsistent with the order's
    current state or quantities (e.g. overfill, zero quantity,
    non-positive price).
    """
    DEFAULT_CODE = "EL-007"


class RegistryNotRunningError(OrderLifecycleError):
    """Raised when the OrderRegistry is accessed before start()."""
    DEFAULT_CODE = "EL-008"
