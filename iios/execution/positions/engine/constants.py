"""iios/execution/positions/engine/constants.py
==================================================
Constants, enumerations, and bounds for the IIOS
Position Engine coordination layer.

C6 Execution Intelligence — Phase 3, Module 2
"""
from __future__ import annotations

from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

ENGINE_SYSTEM_ID    = "iios:execution:positions:engine"
MANAGER_SYSTEM_ID   = "iios:execution:positions:engine:manager"
REGISTRY_SYSTEM_ID  = "iios:execution:positions:engine:registry"
FACTORY_SYSTEM_ID   = "iios:execution:positions:engine:factory"
VALIDATOR_SYSTEM_ID = "iios:execution:positions:engine:validator"

VERSION = "1.0.0"

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_MAX_POSITIONS = 10_000
DEFAULT_MAX_HISTORY   = 5_000
DEFAULT_SEARCH_LIMIT  = 1_000

# ── Actor labels ──────────────────────────────────────────────────────────────

ACTOR_ENGINE  = "iios:execution:positions:engine"
ACTOR_MANAGER = "iios:execution:positions:engine:manager"
ACTOR_SYSTEM  = "iios:system"


# ── Engine operation state ────────────────────────────────────────────────────

class EngineState(str, Enum):
    """
    Transient state of the engine while processing a single operation.

    IDLE          — awaiting the next request
    VALIDATING    — running request validation
    CREATING      — constructing a new position
    UPDATING      — applying field updates to an existing position
    SYNCHRONIZING — synchronizing execution data into a position
    CLOSING       — driving a position to the CLOSED lifecycle state
    COMPLETED     — operation finished successfully
    FAILED        — operation finished with an error
    """
    IDLE          = "IDLE"
    VALIDATING    = "VALIDATING"
    CREATING      = "CREATING"
    UPDATING      = "UPDATING"
    SYNCHRONIZING = "SYNCHRONIZING"
    CLOSING       = "CLOSING"
    COMPLETED     = "COMPLETED"
    FAILED        = "FAILED"


TERMINAL_ENGINE_STATES = frozenset({EngineState.COMPLETED, EngineState.FAILED})


# ── Operation types ───────────────────────────────────────────────────────────

class OperationType(str, Enum):
    """The six position engine operations."""
    CREATE_POSITION  = "CREATE_POSITION"
    UPDATE_POSITION  = "UPDATE_POSITION"
    CLOSE_POSITION   = "CLOSE_POSITION"
    SYNC_POSITION    = "SYNC_POSITION"
    ARCHIVE_POSITION = "ARCHIVE_POSITION"
    QUERY_POSITION   = "QUERY_POSITION"


# ── Engine event types ────────────────────────────────────────────────────────

class EngineEventType(str, Enum):
    """Domain events published by the Position Engine."""
    POSITION_CREATED      = "POSITION_CREATED"
    POSITION_UPDATED      = "POSITION_UPDATED"
    POSITION_CLOSED       = "POSITION_CLOSED"
    POSITION_SYNCHRONIZED = "POSITION_SYNCHRONIZED"
    POSITION_ARCHIVED     = "POSITION_ARCHIVED"
    ENGINE_STARTED        = "ENGINE_STARTED"
    ENGINE_STOPPED        = "ENGINE_STOPPED"


# ── Validation result codes ───────────────────────────────────────────────────

class ValidationCode(str, Enum):
    """Short-code classification for validation failures."""
    IDENTIFIER_MISSING    = "IDENTIFIER_MISSING"
    QUANTITY_INVALID      = "QUANTITY_INVALID"
    PRICE_INVALID         = "PRICE_INVALID"
    STATE_INCOMPATIBLE    = "STATE_INCOMPATIBLE"
    EXECUTION_MISMATCH    = "EXECUTION_MISMATCH"
    SNAPSHOT_INCONSISTENT = "SNAPSHOT_INCONSISTENT"
    OPERATION_REJECTED    = "OPERATION_REJECTED"
