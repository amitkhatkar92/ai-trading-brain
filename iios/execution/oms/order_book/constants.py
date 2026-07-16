"""iios/execution/oms/order_book/constants.py
==================================================
Constants, enumerations, and bounds for the IIOS Order Book.

C6 Execution Intelligence — Phase 2, Module 2
"""
from __future__ import annotations

from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

BOOK_SYSTEM_ID      = "iios:execution:oms:order_book"
REGISTRY_SYSTEM_ID  = "iios:execution:oms:order_book:registry"
FACTORY_SYSTEM_ID   = "iios:execution:oms:order_book:factory"
VALIDATOR_SYSTEM_ID = "iios:execution:oms:order_book:validator"
INDEX_SYSTEM_ID     = "iios:execution:oms:order_book:index"

VERSION = "1.0.0"

# ── Actor labels ──────────────────────────────────────────────────────────────

ACTOR_SYSTEM    = "iios:system"
ACTOR_BOOK      = "iios:execution:oms:order_book"
ACTOR_REGISTRY  = "iios:execution:oms:order_book:registry"
ACTOR_FACTORY   = "iios:execution:oms:order_book:factory"
ACTOR_USER      = "iios:user"

# ── Capacity defaults ─────────────────────────────────────────────────────────

DEFAULT_MAX_ENTRIES       = 1_000_000
DEFAULT_MAX_HISTORY       = 500
DEFAULT_MAX_SNAPSHOT_AGE  = 3_600.0     # seconds; entries older than this may be evicted

# ── Enumerations ──────────────────────────────────────────────────────────────


class BookEntryStatus(str, Enum):
    """
    OMS order book status — a simplified view of M1 OrderState
    used for indexing and querying.
    """
    ACTIVE    = "ACTIVE"      # Order is live and may change
    COMPLETED = "COMPLETED"   # Order reached FILLED terminal state
    CANCELLED = "CANCELLED"   # Order was cancelled
    REJECTED  = "REJECTED"    # Order was rejected
    EXPIRED   = "EXPIRED"     # Order expired
    FAILED    = "FAILED"      # Order failed
    UNKNOWN   = "UNKNOWN"


# M1 OrderState → BookEntryStatus mapping
ORDER_STATE_TO_BOOK_STATUS: dict[str, BookEntryStatus] = {
    "CREATED":             BookEntryStatus.ACTIVE,
    "VALIDATED":           BookEntryStatus.ACTIVE,
    "PENDING_SUBMISSION":  BookEntryStatus.ACTIVE,
    "SUBMITTED":           BookEntryStatus.ACTIVE,
    "ACKNOWLEDGED":        BookEntryStatus.ACTIVE,
    "PARTIALLY_FILLED":    BookEntryStatus.ACTIVE,
    "FILLED":              BookEntryStatus.COMPLETED,
    "CANCEL_PENDING":      BookEntryStatus.ACTIVE,
    "CANCELLED":           BookEntryStatus.CANCELLED,
    "REJECTED":            BookEntryStatus.REJECTED,
    "EXPIRED":             BookEntryStatus.EXPIRED,
    "FAILED":              BookEntryStatus.FAILED,
    "RECOVERING":          BookEntryStatus.ACTIVE,
    "RECOVERED":           BookEntryStatus.ACTIVE,
}

# Terminal book statuses
TERMINAL_BOOK_STATUSES = frozenset({
    BookEntryStatus.COMPLETED,
    BookEntryStatus.CANCELLED,
    BookEntryStatus.REJECTED,
    BookEntryStatus.EXPIRED,
    BookEntryStatus.FAILED,
})


class BookEventType(str, Enum):
    """Events emitted by the Order Book."""
    ORDER_ADDED      = "ORDER_ADDED"
    ORDER_UPDATED    = "ORDER_UPDATED"
    ORDER_REMOVED    = "ORDER_REMOVED"
    SNAPSHOT_CREATED = "SNAPSHOT_CREATED"
    SNAPSHOT_PUBLISHED = "SNAPSHOT_PUBLISHED"
    BOOK_VALIDATED   = "BOOK_VALIDATED"


class BookValidationCode(str, Enum):
    """Machine-readable validation failure codes."""
    MISSING_ORDER_ID    = "MISSING_ORDER_ID"
    DUPLICATE_ORDER_ID  = "DUPLICATE_ORDER_ID"
    INVALID_STATUS      = "INVALID_STATUS"
    BROKEN_INDEX        = "BROKEN_INDEX"
    SNAPSHOT_INCONSISTENT = "SNAPSHOT_INCONSISTENT"
    CAPACITY_EXCEEDED   = "CAPACITY_EXCEEDED"
    BOOK_NOT_RUNNING    = "BOOK_NOT_RUNNING"
    ENTRY_NOT_FOUND     = "ENTRY_NOT_FOUND"


class QuerySortField(str, Enum):
    """Fields available for query sorting."""
    ADDED_AT    = "ADDED_AT"
    UPDATED_AT  = "UPDATED_AT"
    ORDER_ID    = "ORDER_ID"
    STATUS      = "STATUS"
    INSTRUMENT  = "INSTRUMENT"
