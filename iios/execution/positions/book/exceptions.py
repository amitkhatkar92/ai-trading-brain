"""iios/execution/positions/book/exceptions.py
==================================================
Exception hierarchy for the IIOS Position Book.

Error Codes
-----------
PB3-000  PositionBookError               — base
PB3-001  PositionBookNotRunningError     — book not started
PB3-002  BookEntryNotFoundError          — position not in book
PB3-003  DuplicateBookEntryError         — position already in book
PB3-004  PositionBookValidationError     — consistency check failed
PB3-005  PositionBookCapacityError       — book at max capacity
PB3-006  PositionBookIndexError          — index operation failed
PB3-007  PositionBookSnapshotError       — snapshot generation failed
PB3-008  PositionBookQueryError          — query operation failed
PB3-009  PositionBookStateError          — book in unexpected state

C6 Execution Intelligence — Phase 3, Module 3
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from iios.common.errors.exceptions import IIOSError

from .constants import IndexType


class PositionBookError(IIOSError):
    """Base for all Position Book errors."""
    DEFAULT_CODE = "PB3-000"


class PositionBookNotRunningError(PositionBookError):
    """The Position Book has not been started."""
    DEFAULT_CODE = "PB3-001"

    def __init__(
        self,
        *,
        code:           str = "PB3-001",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            "PositionBook is not running",
            code=code, context=context, correlation_id=correlation_id,
        )


class BookEntryNotFoundError(PositionBookError):
    """No book entry found for the given position identifier."""
    DEFAULT_CODE = "PB3-002"

    def __init__(
        self,
        position_id: str,
        *,
        code:           str = "PB3-002",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Position '{position_id}' is not in the book",
            code=code,
            context=context or {"position_id": position_id},
            correlation_id=correlation_id,
        )
        self.position_id = position_id


class DuplicateBookEntryError(PositionBookError):
    """A position with this ID is already in the book."""
    DEFAULT_CODE = "PB3-003"

    def __init__(
        self,
        position_id: str,
        *,
        code:           str = "PB3-003",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Position '{position_id}' is already in the book",
            code=code,
            context=context or {"position_id": position_id},
            correlation_id=correlation_id,
        )
        self.position_id = position_id


class PositionBookValidationError(PositionBookError):
    """A book consistency or identifier validation check failed."""
    DEFAULT_CODE = "PB3-004"

    def __init__(
        self,
        message: str,
        *,
        errors:         tuple = (),
        code:           str = "PB3-004",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            message,
            code=code, context=context, correlation_id=correlation_id,
        )
        self.errors = errors


class PositionBookCapacityError(PositionBookError):
    """The book has reached its maximum position capacity."""
    DEFAULT_CODE = "PB3-005"

    def __init__(
        self,
        capacity: int,
        *,
        code:           str = "PB3-005",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"PositionBook is at maximum capacity ({capacity})",
            code=code,
            context=context or {"capacity": capacity},
            correlation_id=correlation_id,
        )
        self.capacity = capacity


class PositionBookIndexError(PositionBookError):
    """An index operation failed due to inconsistency."""
    DEFAULT_CODE = "PB3-006"

    def __init__(
        self,
        message: str,
        *,
        index_type: Optional[IndexType] = None,
        code:           str = "PB3-006",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            message,
            code=code,
            context=context or {"index_type": index_type.value if index_type else ""},
            correlation_id=correlation_id,
        )
        self.index_type = index_type


class PositionBookSnapshotError(PositionBookError):
    """A snapshot generation or retrieval operation failed."""
    DEFAULT_CODE = "PB3-007"

    def __init__(
        self,
        message: str,
        *,
        code:           str = "PB3-007",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context, correlation_id=correlation_id)


class PositionBookQueryError(PositionBookError):
    """A query operation failed or was invalid."""
    DEFAULT_CODE = "PB3-008"

    def __init__(
        self,
        message: str,
        *,
        code:           str = "PB3-008",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context, correlation_id=correlation_id)


class PositionBookStateError(PositionBookError):
    """The book is in an unexpected or inconsistent state."""
    DEFAULT_CODE = "PB3-009"

    def __init__(
        self,
        message: str,
        *,
        code:           str = "PB3-009",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context, correlation_id=correlation_id)
