"""iios/execution/positions/book/constants.py
==================================================
Constants, enumerations, and bounds for the IIOS Position Book —
the canonical institutional repository for every managed position.

C6 Execution Intelligence — Phase 3, Module 3
"""
from __future__ import annotations

from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

BOOK_SYSTEM_ID      = "iios:execution:positions:book"
REGISTRY_SYSTEM_ID  = "iios:execution:positions:book:registry"
INDEX_SYSTEM_ID     = "iios:execution:positions:book:index"
FACTORY_SYSTEM_ID   = "iios:execution:positions:book:factory"
VALIDATOR_SYSTEM_ID = "iios:execution:positions:book:validator"

VERSION = "1.0.0"

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_MAX_POSITIONS  = 10_000
DEFAULT_MAX_HISTORY    = 500
DEFAULT_SNAPSHOT_LIMIT = 100
DEFAULT_QUERY_LIMIT    = 1_000

# ── Actor labels ──────────────────────────────────────────────────────────────

ACTOR_BOOK     = "iios:execution:positions:book"
ACTOR_REGISTRY = "iios:execution:positions:book:registry"
ACTOR_SYSTEM   = "iios:system"


# ── Book event types ──────────────────────────────────────────────────────────

class BookEventType(str, Enum):
    """Domain events emitted by the Position Book."""
    POSITION_ADDED     = "POSITION_ADDED"
    POSITION_UPDATED   = "POSITION_UPDATED"
    POSITION_REMOVED   = "POSITION_REMOVED"
    SNAPSHOT_CREATED   = "SNAPSHOT_CREATED"
    SNAPSHOT_PUBLISHED = "SNAPSHOT_PUBLISHED"
    BOOK_VALIDATED     = "BOOK_VALIDATED"


# ── Index types ───────────────────────────────────────────────────────────────

class IndexType(str, Enum):
    """The 11 indexes maintained by the Position Book."""
    POSITION_ID     = "POSITION_ID"
    PORTFOLIO_ID    = "PORTFOLIO_ID"
    STRATEGY_ID     = "STRATEGY_ID"
    DECISION_ID     = "DECISION_ID"
    EXECUTION_ID    = "EXECUTION_ID"
    WORKFLOW_ID     = "WORKFLOW_ID"
    INSTRUMENT      = "INSTRUMENT"
    EXCHANGE        = "EXCHANGE"
    PRODUCT         = "PRODUCT"
    DIRECTION       = "DIRECTION"
    LIFECYCLE_STATE = "LIFECYCLE_STATE"


# ── Book operation types ──────────────────────────────────────────────────────

class BookOperationType(str, Enum):
    """Types of operations performed on the Position Book."""
    ADD      = "ADD"
    UPDATE   = "UPDATE"
    REMOVE   = "REMOVE"
    QUERY    = "QUERY"
    SNAPSHOT = "SNAPSHOT"
    VALIDATE = "VALIDATE"


# ── Validation severity ───────────────────────────────────────────────────────

class ValidationSeverity(str, Enum):
    """Severity of a book validation finding."""
    ERROR   = "ERROR"
    WARNING = "WARNING"
    INFO    = "INFO"
