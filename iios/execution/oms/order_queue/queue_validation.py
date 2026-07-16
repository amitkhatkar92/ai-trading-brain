"""iios/execution/oms/order_queue/queue_validation.py
==================================================
QueueValidator — validates enqueue requests and state transitions.

C6 Execution Intelligence — Phase 2, Module 4
"""
from __future__ import annotations

from iios.execution.oms.order_queue.constants import (
    VALID_ENTRY_TRANSITIONS,
    VALIDATOR_SYSTEM_ID,
    QueueEntryState,
    QueueValidationCode,
)
from iios.execution.oms.order_queue.exceptions import (
    QueueEntryStateError,
    QueueValidationError,
)
from iios.execution.oms.order_queue.queue_context import QueueContext
from iios.execution.oms.order_queue.queue_entry import QueueEntry


class QueueValidator:
    """
    Validates QueueContexts before enqueue and state transitions
    before in-place mutation.
    """

    __slots__ = ("_system_id",)

    def __init__(self) -> None:
        self._system_id = VALIDATOR_SYSTEM_ID

    # ── Enqueue validation ────────────────────────────────────────────────────

    def validate_context(
        self,
        context: QueueContext,
        existing_order_ids: set[str],
        current_size: int,
        max_size: int,
    ) -> None:
        """
        Validate a QueueContext before creating an entry.

        Raises QueueValidationError with all accumulated errors.
        """
        errors: list[str] = []

        if not context.order_id or not context.order_id.strip():
            errors.append(QueueValidationCode.MISSING_ORDER_ID.value)

        if context.order_id in existing_order_ids:
            errors.append(QueueValidationCode.DUPLICATE_ENTRY.value)

        if current_size >= max_size:
            errors.append(QueueValidationCode.QUEUE_FULL.value)

        if context.ttl_sec <= 0:
            errors.append(QueueValidationCode.INVALID_SCHEDULE.value)

        if errors:
            raise QueueValidationError(
                f"Queue context validation failed: {', '.join(errors)}",
                errors=tuple(errors),
                context={"order_id": context.order_id},
            )

    def validate_entry(
        self,
        entry: QueueEntry,
        existing_order_ids: set[str],
        current_size: int,
        max_size: int,
    ) -> None:
        """Validate a pre-built QueueEntry for direct enqueue."""
        errors: list[str] = []

        if not entry.order_id or not entry.order_id.strip():
            errors.append(QueueValidationCode.MISSING_ORDER_ID.value)

        if entry.order_id in existing_order_ids:
            errors.append(QueueValidationCode.DUPLICATE_ENTRY.value)

        if current_size >= max_size:
            errors.append(QueueValidationCode.QUEUE_FULL.value)

        if errors:
            raise QueueValidationError(
                f"QueueEntry validation failed: {', '.join(errors)}",
                errors=tuple(errors),
                context={"order_id": entry.order_id, "entry_id": entry.entry_id},
            )

    # ── State transition validation ───────────────────────────────────────────

    def validate_transition(
        self,
        entry:      QueueEntry,
        new_state:  QueueEntryState,
    ) -> None:
        """
        Validate that a state transition is permitted.

        Raises QueueEntryStateError if the transition is invalid.
        """
        allowed = VALID_ENTRY_TRANSITIONS.get(entry.state, frozenset())
        if new_state not in allowed:
            raise QueueEntryStateError(
                entry_id   = entry.entry_id,
                from_state = entry.state.value,
                to_state   = new_state.value,
                context    = {"order_id": entry.order_id},
            )

    # ── Business rule validation ──────────────────────────────────────────────

    def validate_retry_eligible(self, entry: QueueEntry) -> None:
        """Raise QueueValidationError if the entry cannot be retried."""
        if not entry.can_retry:
            raise QueueValidationError(
                f"Entry '{entry.entry_id}' has exhausted retries "
                f"({entry.retry_count}/{entry.max_retries})",
                errors=(QueueValidationCode.RETRY_LIMIT_EXCEEDED.value,),
                context={"entry_id": entry.entry_id, "order_id": entry.order_id},
            )

    def validate_dispatch_eligible(self, entry: QueueEntry) -> None:
        """Raise QueueValidationError if the entry is not dispatchable."""
        errors: list[str] = []
        if entry.state != QueueEntryState.READY:
            errors.append(QueueValidationCode.INVALID_STATE_TRANSITION.value)
        if entry.is_expired:
            errors.append(QueueValidationCode.ENTRY_EXPIRED.value)
        if errors:
            raise QueueValidationError(
                f"Entry '{entry.entry_id}' is not eligible for dispatch",
                errors=tuple(errors),
                context={"state": entry.state.value, "entry_id": entry.entry_id},
            )
