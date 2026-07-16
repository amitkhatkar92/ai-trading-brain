"""iios/execution/positions/book/__init__.py
==================================================
Public API for the IIOS Position Book.

C6 Execution Intelligence — Phase 3, Module 3
"""
from __future__ import annotations

# ── Constants ─────────────────────────────────────────────────────────────────
from .constants import (
    ACTOR_BOOK,
    ACTOR_REGISTRY,
    ACTOR_SYSTEM,
    BOOK_SYSTEM_ID,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_POSITIONS,
    DEFAULT_QUERY_LIMIT,
    DEFAULT_SNAPSHOT_LIMIT,
    FACTORY_SYSTEM_ID,
    INDEX_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    VALIDATOR_SYSTEM_ID,
    VERSION,
    BookEventType,
    BookOperationType,
    IndexType,
    ValidationSeverity,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .exceptions import (
    BookEntryNotFoundError,
    DuplicateBookEntryError,
    PositionBookCapacityError,
    PositionBookError,
    PositionBookIndexError,
    PositionBookNotRunningError,
    PositionBookQueryError,
    PositionBookSnapshotError,
    PositionBookStateError,
    PositionBookValidationError,
)

# ── Value types ───────────────────────────────────────────────────────────────
from .position_book_context import BookContext, make_book_context
from .position_book_events import (
    BookEvent,
    make_book_validated_event,
    make_position_added_event,
    make_position_removed_event,
    make_position_updated_event,
    make_snapshot_created_event,
    make_snapshot_published_event,
)
from .position_book_history import BookHistory, SnapshotHistory
from .position_book_snapshot import (
    BookEntrySnapshot,
    FilteredSnapshot,
    HistoricalSnapshot,
    PositionBookSnapshot,
    make_book_snapshot,
    make_filtered_snapshot,
    make_historical_snapshot,
)
from .position_book_statistics import BookStatistics
from .position_book_validation import (
    BookValidationResult,
    BookValidator,
    ValidationFinding,
)
from .position_entry import BookEntry
from .position_filter import (
    FilterChain,
    PositionPredicate,
    active_filter,
    archived_filter,
    closed_filter,
    decision_filter,
    direction_filter,
    exchange_filter,
    execution_filter,
    instrument_filter,
    long_filter,
    max_quantity_filter,
    min_quantity_filter,
    portfolio_filter,
    product_filter,
    short_filter,
    state_filter,
    strategy_filter,
    workflow_filter,
)
from .position_query import BookQuery, QueryResult, make_query_result

# ── Services ──────────────────────────────────────────────────────────────────
from .position_index import PositionIndex
from .position_book_factory import BookFactory
from .position_book_registry import BookRegistry
from .position_book import PositionBook

__all__ = [
    # constants
    "BOOK_SYSTEM_ID", "REGISTRY_SYSTEM_ID", "INDEX_SYSTEM_ID",
    "FACTORY_SYSTEM_ID", "VALIDATOR_SYSTEM_ID",
    "ACTOR_BOOK", "ACTOR_REGISTRY", "ACTOR_SYSTEM",
    "VERSION",
    "DEFAULT_MAX_POSITIONS", "DEFAULT_MAX_HISTORY",
    "DEFAULT_QUERY_LIMIT", "DEFAULT_SNAPSHOT_LIMIT",
    # enums
    "BookEventType", "BookOperationType", "IndexType", "ValidationSeverity",
    # exceptions
    "PositionBookError", "PositionBookNotRunningError",
    "BookEntryNotFoundError", "DuplicateBookEntryError",
    "PositionBookValidationError", "PositionBookCapacityError",
    "PositionBookIndexError", "PositionBookSnapshotError",
    "PositionBookQueryError", "PositionBookStateError",
    # value types — context
    "BookContext", "make_book_context",
    # value types — events
    "BookEvent",
    "make_position_added_event", "make_position_updated_event",
    "make_position_removed_event",
    "make_snapshot_created_event", "make_snapshot_published_event",
    "make_book_validated_event",
    # value types — history
    "BookHistory", "SnapshotHistory",
    # value types — snapshots
    "BookEntrySnapshot", "PositionBookSnapshot",
    "FilteredSnapshot", "HistoricalSnapshot",
    "make_book_snapshot", "make_filtered_snapshot", "make_historical_snapshot",
    # value types — statistics
    "BookStatistics",
    # value types — validation
    "BookValidationResult", "ValidationFinding", "BookValidator",
    # value types — entry
    "BookEntry",
    # value types — filter
    "PositionPredicate", "FilterChain",
    "active_filter", "closed_filter", "archived_filter", "state_filter",
    "instrument_filter", "exchange_filter", "portfolio_filter",
    "strategy_filter", "decision_filter", "execution_filter", "workflow_filter",
    "direction_filter", "product_filter",
    "min_quantity_filter", "max_quantity_filter",
    "long_filter", "short_filter",
    # value types — query
    "BookQuery", "QueryResult", "make_query_result",
    # services
    "PositionIndex", "BookFactory", "BookRegistry", "PositionBook",
]
