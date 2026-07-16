"""iios/execution/oms/order_book/exceptions.py
==================================================
Exception hierarchy for the IIOS Order Book.

All exceptions inherit from IIOSError.

Error Codes
-----------
OB-000  OrderBookError           — base
OB-001  OrderBookEntryError      — entry-level error
OB-002  OrderEntryNotFoundError  — entry not in book
OB-003  DuplicateEntryError      — duplicate order_id
OB-004  OrderBookCapacityError   — book full
OB-005  OrderBookNotRunning      — book not started
OB-006  OrderBookValidationError — validation failure
OB-007  OrderBookIndexError      — index inconsistency
OB-008  OrderBookSnapshotError   — snapshot error
OB-009  OrderBookQueryError      — query error
OB-010  OrderBookHistoryError    — history error

C6 Execution Intelligence — Phase 2, Module 2
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from iios.common.errors.exceptions import IIOSError


class OrderBookError(IIOSError):
    """Base for all Order Book errors."""
    DEFAULT_CODE = "OB-000"


class OrderBookEntryError(OrderBookError):
    """Entry-level error."""
    DEFAULT_CODE = "OB-001"


class OrderEntryNotFoundError(OrderBookError):
    """No entry registered for the given order_id."""
    DEFAULT_CODE = "OB-002"

    def __init__(
        self,
        order_id: str,
        *,
        code:           str = "OB-002",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Order entry not found: '{order_id}'",
            code=code,
            context=context,
            correlation_id=correlation_id,
        )
        self.order_id = order_id


class DuplicateEntryError(OrderBookError):
    """An entry with this order_id already exists."""
    DEFAULT_CODE = "OB-003"

    def __init__(
        self,
        order_id: str,
        *,
        code:           str = "OB-003",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Order entry already in book: '{order_id}'",
            code=code,
            context=context,
            correlation_id=correlation_id,
        )
        self.order_id = order_id


class OrderBookCapacityError(OrderBookError):
    """Book has reached maximum capacity."""
    DEFAULT_CODE = "OB-004"


class OrderBookNotRunning(OrderBookError):
    """Order Book was not started before use."""
    DEFAULT_CODE = "OB-005"


class OrderBookValidationError(OrderBookError):
    """Validation failure."""
    DEFAULT_CODE = "OB-006"

    def __init__(
        self,
        message:        str,
        *,
        code:           str = "OB-006",
        errors:         tuple[str, ...] = (),
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context,
                         correlation_id=correlation_id)
        self.errors = errors


class OrderBookIndexError(OrderBookError):
    """Index inconsistency detected."""
    DEFAULT_CODE = "OB-007"


class OrderBookSnapshotError(OrderBookError):
    """Snapshot operation error."""
    DEFAULT_CODE = "OB-008"


class OrderBookQueryError(OrderBookError):
    """Query operation error."""
    DEFAULT_CODE = "OB-009"


class OrderBookHistoryError(OrderBookError):
    """History operation error."""
    DEFAULT_CODE = "OB-010"
