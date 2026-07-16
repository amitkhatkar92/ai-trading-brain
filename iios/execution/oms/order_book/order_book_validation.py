"""iios/execution/oms/order_book/order_book_validation.py
==================================================
OrderBookValidator — stateless validation for Order Book
add, update, and snapshot operations.

C6 Execution Intelligence — Phase 2, Module 2
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from iios.execution.oms.order_book.constants import BookValidationCode
from iios.execution.oms.order_book.order_book_context import OrderAddRequest
from iios.execution.oms.order_book.order_book_entry import OrderBookEntry
from iios.common.logging.logging_manager import get_logger

_log = get_logger(__name__, engine_id="iios:execution:oms:order_book:validator")


@dataclass(frozen=True)
class BookValidationResult:
    """Outcome of a validation pass."""

    passed:   bool
    errors:   tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @classmethod
    def ok(cls, *, warnings: tuple[str, ...] = ()) -> "BookValidationResult":
        return cls(passed=True, errors=(), warnings=warnings)

    @classmethod
    def fail(cls, *errors: str) -> "BookValidationResult":
        return cls(passed=False, errors=errors)

    def __bool__(self) -> bool:
        return self.passed

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed":   self.passed,
            "errors":   list(self.errors),
            "warnings": list(self.warnings),
        }


class OrderBookValidator:
    """
    Stateless validator for Order Book operations.
    Thread-safe (no mutable state).
    """

    def validate_add_request(
        self,
        request:      OrderAddRequest,
        existing_ids: frozenset[str],
    ) -> BookValidationResult:
        """Validate an add request before inserting into the book."""
        errors:   list[str] = []
        warnings: list[str] = []

        if not request.order_id:
            errors.append(
                f"[{BookValidationCode.MISSING_ORDER_ID.value}] "
                "order_id must not be empty"
            )
        elif request.order_id in existing_ids:
            errors.append(
                f"[{BookValidationCode.DUPLICATE_ORDER_ID.value}] "
                f"order_id '{request.order_id}' is already in the book"
            )

        if not request.instrument:
            warnings.append("instrument is empty — indexing by instrument unavailable")

        if errors:
            return BookValidationResult.fail(*errors)
        return BookValidationResult.ok(warnings=tuple(warnings))

    def validate_entry(self, entry: OrderBookEntry) -> BookValidationResult:
        """Validate an OrderBookEntry is self-consistent."""
        errors: list[str] = []
        if not entry.order_id:
            errors.append(
                f"[{BookValidationCode.MISSING_ORDER_ID.value}] "
                "order_id must not be empty"
            )
        if errors:
            return BookValidationResult.fail(*errors)
        return BookValidationResult.ok()

    def validate_index_consistency(
        self,
        entries:    dict[str, OrderBookEntry],
        index_ids:  frozenset[str],
    ) -> BookValidationResult:
        """Check that book entries and an index are consistent."""
        entry_ids = frozenset(entries.keys())
        orphans = index_ids - entry_ids
        if orphans:
            return BookValidationResult.fail(
                f"[{BookValidationCode.BROKEN_INDEX.value}] "
                f"Index contains {len(orphans)} order_id(s) not in the book: "
                f"{sorted(orphans)[:5]}{'...' if len(orphans) > 5 else ''}"
            )
        return BookValidationResult.ok()
