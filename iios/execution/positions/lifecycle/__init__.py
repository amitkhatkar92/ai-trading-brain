"""iios/execution/positions/lifecycle/__init__.py
==================================================
Public API for the IIOS Position Lifecycle layer.

C6 Execution Intelligence — Phase 3, Module 1
"""
from __future__ import annotations

# ── Constants & enumerations ──────────────────────────────────────────────────
from .constants import (
    ACTIVE_STATES,
    ACTOR_FACTORY,
    ACTOR_LIFECYCLE,
    ACTOR_REGISTRY,
    ACTOR_SYSTEM,
    CLOSED_STATES,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_POSITIONS,
    DEFAULT_SEARCH_LIMIT,
    FACTORY_SYSTEM_ID,
    LIFECYCLE_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    SUSPENDED_STATES,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    VALIDATOR_SYSTEM_ID,
    VERSION,
    PositionDirection,
    PositionEventType,
    PositionProduct,
    PositionState,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .exceptions import (
    DuplicatePositionError,
    InvalidTransitionError,
    PositionLifecycleError,
    PositionNotFoundError,
    PositionNotRunningError,
    PositionRegistryCapacityError,
    PositionStateError,
    PositionValidationError,
)

# ── Domain model ──────────────────────────────────────────────────────────────
from .position import Position
from .position_context import PositionContext, make_context
from .position_event import (
    PositionEvent,
    make_position_archived,
    make_position_closed,
    make_position_created,
    make_position_opened,
    make_position_partially_closed,
    make_position_recovered,
    make_position_updated,
)
from .position_history import PositionHistory
from .position_metadata import PositionMetadata
from .position_state import PositionStateRecord
from .position_statistics import PositionStatistics
from .position_transition import PositionTransition, make_transition
from .position_validation import PositionValidator, ValidationResult

# ── Services ──────────────────────────────────────────────────────────────────
from .position_factory import PositionFactory
from .position_registry import PositionRegistry

__all__ = [
    # constants
    "LIFECYCLE_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    "VALIDATOR_SYSTEM_ID",
    "ACTOR_SYSTEM",
    "ACTOR_LIFECYCLE",
    "ACTOR_REGISTRY",
    "ACTOR_FACTORY",
    "VERSION",
    "DEFAULT_MAX_POSITIONS",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_SEARCH_LIMIT",
    "VALID_TRANSITIONS",
    "TERMINAL_STATES",
    "ACTIVE_STATES",
    "SUSPENDED_STATES",
    "CLOSED_STATES",
    # enums
    "PositionState",
    "PositionDirection",
    "PositionProduct",
    "PositionEventType",
    # exceptions
    "PositionLifecycleError",
    "InvalidTransitionError",
    "PositionNotFoundError",
    "DuplicatePositionError",
    "PositionValidationError",
    "PositionRegistryCapacityError",
    "PositionNotRunningError",
    "PositionStateError",
    # domain model
    "Position",
    "PositionStateRecord",
    "PositionTransition",
    "PositionEvent",
    "PositionHistory",
    "PositionStatistics",
    "PositionContext",
    "PositionMetadata",
    "ValidationResult",
    # factories / helpers
    "make_transition",
    "make_context",
    "make_position_created",
    "make_position_opened",
    "make_position_updated",
    "make_position_partially_closed",
    "make_position_closed",
    "make_position_recovered",
    "make_position_archived",
    # services
    "PositionValidator",
    "PositionFactory",
    "PositionRegistry",
]
