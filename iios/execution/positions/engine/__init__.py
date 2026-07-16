"""iios/execution/positions/engine/__init__.py
==================================================
Public API for the IIOS Position Engine.

C6 Execution Intelligence — Phase 3, Module 2
"""
from __future__ import annotations

# ── Constants ─────────────────────────────────────────────────────────────────
from .constants import (
    ACTOR_ENGINE,
    ACTOR_MANAGER,
    ACTOR_SYSTEM,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_POSITIONS,
    DEFAULT_SEARCH_LIMIT,
    ENGINE_SYSTEM_ID,
    FACTORY_SYSTEM_ID,
    MANAGER_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    TERMINAL_ENGINE_STATES,
    VALIDATOR_SYSTEM_ID,
    VERSION,
    EngineEventType,
    EngineState,
    OperationType,
    ValidationCode,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .exceptions import (
    PositionArchiveError,
    PositionCloseError,
    PositionCreationError,
    PositionEngineError,
    PositionEngineNotRunningError,
    PositionEngineStateError,
    PositionEngineValidationError,
    PositionOperationError,
    PositionQueryError,
    PositionSyncError,
    PositionUpdateError,
)

# ── Value types ───────────────────────────────────────────────────────────────
from .position_context import EngineContext, make_engine_context
from .position_events import (
    EngineEvent,
    make_engine_started_event,
    make_engine_stopped_event,
    make_position_archived_event,
    make_position_closed_event,
    make_position_created_event,
    make_position_synchronized_event,
    make_position_updated_event,
)
from .position_history import EngineHistory
from .position_request import (
    ArchivePositionRequest,
    ClosePositionRequest,
    CreatePositionRequest,
    ExecutionSnapshot,
    QueryPositionRequest,
    PositionRequest,
    SyncPositionRequest,
    UpdatePositionRequest,
)
from .position_result import PositionResult, make_failure_result, make_success_result
from .position_snapshot import EngineSnapshot, PositionSummary, make_engine_snapshot
from .position_state import EngineStateRecord
from .position_statistics import EngineStatistics
from .position_validation import EngineValidator, ValidationResult

# ── Services ──────────────────────────────────────────────────────────────────
from .position_factory import EngineFactory
from .position_registry import EngineRegistry
from .position_manager import PositionManager
from .position_engine import PositionEngine

__all__ = [
    # constants
    "ENGINE_SYSTEM_ID", "MANAGER_SYSTEM_ID", "REGISTRY_SYSTEM_ID",
    "FACTORY_SYSTEM_ID", "VALIDATOR_SYSTEM_ID",
    "ACTOR_ENGINE", "ACTOR_MANAGER", "ACTOR_SYSTEM",
    "VERSION", "DEFAULT_MAX_POSITIONS", "DEFAULT_MAX_HISTORY", "DEFAULT_SEARCH_LIMIT",
    "TERMINAL_ENGINE_STATES",
    # enums
    "EngineState", "OperationType", "EngineEventType", "ValidationCode",
    # exceptions
    "PositionEngineError", "PositionEngineNotRunningError",
    "PositionOperationError", "PositionCreationError", "PositionUpdateError",
    "PositionCloseError", "PositionSyncError", "PositionArchiveError",
    "PositionQueryError", "PositionEngineValidationError", "PositionEngineStateError",
    # value types
    "EngineContext", "make_engine_context",
    "EngineEvent",
    "make_position_created_event", "make_position_updated_event",
    "make_position_closed_event", "make_position_synchronized_event",
    "make_position_archived_event",
    "make_engine_started_event", "make_engine_stopped_event",
    "EngineHistory",
    "PositionRequest",
    "CreatePositionRequest", "UpdatePositionRequest", "ClosePositionRequest",
    "SyncPositionRequest", "ArchivePositionRequest", "QueryPositionRequest",
    "ExecutionSnapshot",
    "PositionResult", "make_success_result", "make_failure_result",
    "EngineSnapshot", "PositionSummary", "make_engine_snapshot",
    "EngineStateRecord",
    "EngineStatistics",
    "ValidationResult", "EngineValidator",
    # services
    "EngineFactory", "EngineRegistry", "PositionManager", "PositionEngine",
]
