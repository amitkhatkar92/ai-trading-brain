"""iios/execution/oms/order_queue/exceptions.py
==================================================
Exception hierarchy for the IIOS Order Queue.

Error Codes
-----------
QE-000  QueueError                  — base
QE-001  QueueEntryError             — general entry problem
QE-002  DuplicateQueueEntryError    — order already queued
QE-003  QueueEntryNotFoundError     — entry not in registry
QE-004  QueueCapacityError          — queue at max size
QE-005  QueueNotRunning             — queue not started
QE-006  QueueValidationError        — request validation failure
QE-007  QueuePolicyError            — policy evaluation failure
QE-008  QueueSchedulerError         — scheduler failure
QE-009  QueueEntryExpiredError      — entry TTL exceeded
QE-010  QueueEntryStateError        — invalid state transition

C6 Execution Intelligence — Phase 2, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from iios.common.errors.exceptions import IIOSError


class QueueError(IIOSError):
    """Base for all Order Queue errors."""
    DEFAULT_CODE = "QE-000"


class QueueEntryError(QueueError):
    """General queue entry problem."""
    DEFAULT_CODE = "QE-001"


class DuplicateQueueEntryError(QueueError):
    """Order is already present in the queue."""
    DEFAULT_CODE = "QE-002"

    def __init__(
        self,
        order_id: str,
        *,
        code:           str = "QE-002",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Order '{order_id}' is already in the queue",
            code=code,
            context=context,
            correlation_id=correlation_id,
        )
        self.order_id = order_id


class QueueEntryNotFoundError(QueueError):
    """No queue entry found for the given ID."""
    DEFAULT_CODE = "QE-003"

    def __init__(
        self,
        entry_id: str,
        *,
        code:           str = "QE-003",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Queue entry '{entry_id}' not found",
            code=code,
            context=context,
            correlation_id=correlation_id,
        )
        self.entry_id = entry_id


class QueueCapacityError(QueueError):
    """Queue has reached maximum capacity."""
    DEFAULT_CODE = "QE-004"


class QueueNotRunning(QueueError):
    """OrderQueue was not started before use."""
    DEFAULT_CODE = "QE-005"


class QueueValidationError(QueueError):
    """Enqueue request validation failed."""
    DEFAULT_CODE = "QE-006"

    def __init__(
        self,
        message: str,
        *,
        code:           str = "QE-006",
        errors:         tuple[str, ...] = (),
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context,
                         correlation_id=correlation_id)
        self.errors = errors


class QueuePolicyError(QueueError):
    """Policy evaluation failure."""
    DEFAULT_CODE = "QE-007"


class QueueSchedulerError(QueueError):
    """Scheduler operation failure."""
    DEFAULT_CODE = "QE-008"


class QueueEntryExpiredError(QueueError):
    """Queue entry TTL has been exceeded."""
    DEFAULT_CODE = "QE-009"

    def __init__(
        self,
        entry_id: str,
        order_id: str = "",
        *,
        code:           str = "QE-009",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Queue entry '{entry_id}' (order='{order_id}') has expired",
            code=code,
            context=context,
            correlation_id=correlation_id,
        )
        self.entry_id = entry_id
        self.order_id = order_id


class QueueEntryStateError(QueueError):
    """Invalid state transition attempted."""
    DEFAULT_CODE = "QE-010"

    def __init__(
        self,
        entry_id:     str,
        from_state:   str,
        to_state:     str,
        *,
        code:           str = "QE-010",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Cannot transition entry '{entry_id}' from {from_state} → {to_state}",
            code=code,
            context=context,
            correlation_id=correlation_id,
        )
        self.entry_id   = entry_id
        self.from_state = from_state
        self.to_state   = to_state
