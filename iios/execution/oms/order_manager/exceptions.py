"""iios/execution/oms/order_manager/exceptions.py
==================================================
Exception hierarchy for the IIOS Order Manager.

All exceptions inherit from IIOSError.

Error Codes
-----------
OMS-000  OrderManagerError           — base
OMS-001  OrderRegistrationError      — registration failure
OMS-002  OrderNotFoundError          — order_id not in manager
OMS-003  DuplicateOrderError         — duplicate order_id
OMS-004  OrderManagerCapacityError   — registry full
OMS-005  OrderManagerNotRunning      — manager not started
OMS-006  OrderManagerStateError      — invalid OMS state transition
OMS-007  OrderValidationError        — validation failure
OMS-008  OrderOwnershipError         — ownership constraint violated
OMS-009  OrderParentError            — parent-child integrity violation
OMS-010  OrderGroupError             — group integrity violation
OMS-011  OrderAlreadyTerminalError   — operation on terminal order

C6 Execution Intelligence — Phase 2, Module 1
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from iios.common.errors.exceptions import IIOSError


class OrderManagerError(IIOSError):
    """Base for all Order Manager errors."""
    DEFAULT_CODE = "OMS-000"


class OrderRegistrationError(OrderManagerError):
    """Order registration failed."""
    DEFAULT_CODE = "OMS-001"


class OrderNotFoundError(OrderManagerError):
    """No managed order registered under the given order_id."""
    DEFAULT_CODE = "OMS-002"

    def __init__(
        self,
        order_id: str,
        *,
        code:           str = "OMS-002",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"ManagedOrder not found: '{order_id}'",
            code=code,
            context=context,
            correlation_id=correlation_id,
        )
        self.order_id = order_id


class DuplicateOrderError(OrderManagerError):
    """A managed order with this ID already exists."""
    DEFAULT_CODE = "OMS-003"

    def __init__(
        self,
        order_id: str,
        *,
        code:           str = "OMS-003",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"ManagedOrder already registered: '{order_id}'",
            code=code,
            context=context,
            correlation_id=correlation_id,
        )
        self.order_id = order_id


class OrderManagerCapacityError(OrderManagerError):
    """Registry has reached maximum managed order capacity."""
    DEFAULT_CODE = "OMS-004"


class OrderManagerNotRunning(OrderManagerError):
    """Order Manager was not started before use."""
    DEFAULT_CODE = "OMS-005"


class OrderManagerStateError(OrderManagerError):
    """Invalid OMS-level state transition."""
    DEFAULT_CODE = "OMS-006"

    def __init__(
        self,
        order_id:   str,
        from_state: str,
        to_state:   str,
        *,
        code:           str = "OMS-006",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Invalid OMS transition for '{order_id}': {from_state} → {to_state}",
            code=code,
            context=context,
            correlation_id=correlation_id,
        )
        self.order_id   = order_id
        self.from_state = from_state
        self.to_state   = to_state


class OrderValidationError(OrderManagerError):
    """Order Manager validation failed."""
    DEFAULT_CODE = "OMS-007"

    def __init__(
        self,
        message:        str,
        *,
        code:           str = "OMS-007",
        errors:         tuple[str, ...] = (),
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context,
                         correlation_id=correlation_id)
        self.errors = errors


class OrderOwnershipError(OrderManagerError):
    """Ownership constraint violated."""
    DEFAULT_CODE = "OMS-008"


class OrderParentError(OrderManagerError):
    """Parent-child integrity violation."""
    DEFAULT_CODE = "OMS-009"


class OrderGroupError(OrderManagerError):
    """Order group integrity violation."""
    DEFAULT_CODE = "OMS-010"


class OrderAlreadyTerminalError(OrderManagerError):
    """Operation attempted on an already-terminal managed order."""
    DEFAULT_CODE = "OMS-011"

    def __init__(
        self,
        order_id: str,
        state:    str,
        *,
        code:           str = "OMS-011",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"ManagedOrder '{order_id}' is already terminal (state={state})",
            code=code,
            context=context,
            correlation_id=correlation_id,
        )
        self.order_id = order_id
        self.state    = state
