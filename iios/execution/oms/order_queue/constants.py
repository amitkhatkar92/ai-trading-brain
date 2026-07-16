"""iios/execution/oms/order_queue/constants.py
==================================================
Constants, enumerations, and bounds for the IIOS Order Queue.

C6 Execution Intelligence — Phase 2, Module 4
"""
from __future__ import annotations

from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

QUEUE_SYSTEM_ID     = "iios:execution:oms:order_queue"
REGISTRY_SYSTEM_ID  = "iios:execution:oms:order_queue:registry"
FACTORY_SYSTEM_ID   = "iios:execution:oms:order_queue:factory"
VALIDATOR_SYSTEM_ID = "iios:execution:oms:order_queue:validator"

VERSION = "1.0.0"

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_MAX_QUEUE_SIZE   = 10_000
DEFAULT_MAX_HISTORY      = 5_000
DEFAULT_TTL_SEC          = 300.0    # 5 minutes
DEFAULT_RETRY_DELAY_SEC  = 5.0      # base for exponential back-off
DEFAULT_MAX_RETRIES      = 3

# ── Actor labels ──────────────────────────────────────────────────────────────

ACTOR_SYSTEM    = "iios:system"
ACTOR_QUEUE     = "iios:execution:oms:order_queue"
ACTOR_SCHEDULER = "iios:execution:oms:order_queue:scheduler"
ACTOR_VALIDATOR = "iios:execution:oms:order_queue:validator"


# ── Enumerations ──────────────────────────────────────────────────────────────

class QueueEntryState(str, Enum):
    """Lifecycle state of a QueueEntry."""
    QUEUED           = "QUEUED"
    WAITING          = "WAITING"          # scheduled — not yet ready
    READY            = "READY"            # eligible for dispatch
    DISPATCH_PENDING = "DISPATCH_PENDING" # dequeued, dispatch in flight
    DISPATCHED       = "DISPATCHED"       # terminal — successfully dispatched
    SUSPENDED        = "SUSPENDED"        # manually paused
    RETRY_PENDING    = "RETRY_PENDING"    # awaiting retry delay
    FAILED           = "FAILED"           # terminal — exhausted retries
    EXPIRED          = "EXPIRED"          # terminal — TTL exceeded
    REMOVED          = "REMOVED"          # terminal — explicitly removed


TERMINAL_ENTRY_STATES = frozenset({
    QueueEntryState.DISPATCHED,
    QueueEntryState.FAILED,
    QueueEntryState.EXPIRED,
    QueueEntryState.REMOVED,
})

ACTIVE_ENTRY_STATES = frozenset({
    QueueEntryState.QUEUED,
    QueueEntryState.WAITING,
    QueueEntryState.READY,
    QueueEntryState.DISPATCH_PENDING,
    QueueEntryState.SUSPENDED,
    QueueEntryState.RETRY_PENDING,
})

DISPATCHABLE_STATES = frozenset({QueueEntryState.READY})

# Valid state transitions
VALID_ENTRY_TRANSITIONS: dict[QueueEntryState, frozenset[QueueEntryState]] = {
    QueueEntryState.QUEUED: frozenset({
        QueueEntryState.WAITING,
        QueueEntryState.READY,
        QueueEntryState.SUSPENDED,
        QueueEntryState.EXPIRED,
        QueueEntryState.FAILED,
    }),
    QueueEntryState.WAITING: frozenset({
        QueueEntryState.READY,
        QueueEntryState.SUSPENDED,
        QueueEntryState.EXPIRED,
        QueueEntryState.FAILED,
    }),
    QueueEntryState.READY: frozenset({
        QueueEntryState.WAITING,
        QueueEntryState.DISPATCH_PENDING,
        QueueEntryState.SUSPENDED,
        QueueEntryState.EXPIRED,
        QueueEntryState.FAILED,
    }),
    QueueEntryState.DISPATCH_PENDING: frozenset({
        QueueEntryState.DISPATCHED,
        QueueEntryState.RETRY_PENDING,
        QueueEntryState.FAILED,
    }),
    QueueEntryState.DISPATCHED:      frozenset(),
    QueueEntryState.SUSPENDED: frozenset({
        QueueEntryState.WAITING,
        QueueEntryState.READY,
        QueueEntryState.REMOVED,
    }),
    QueueEntryState.RETRY_PENDING: frozenset({
        QueueEntryState.READY,
        QueueEntryState.FAILED,
        QueueEntryState.EXPIRED,
    }),
    QueueEntryState.FAILED:  frozenset(),
    QueueEntryState.EXPIRED: frozenset(),
    QueueEntryState.REMOVED: frozenset(),
}


class QueuePriorityLevel(int, Enum):
    """Priority level — lower integer = higher dispatch priority."""
    CRITICAL   = 0
    HIGH       = 1
    NORMAL     = 2
    LOW        = 3
    BACKGROUND = 4


class QueuePolicyType(str, Enum):
    """Named queue scheduling policies."""
    FIFO         = "FIFO"
    PRIORITY     = "PRIORITY"
    SCHEDULED    = "SCHEDULED"
    DELAYED      = "DELAYED"
    RECOVERY     = "RECOVERY"
    REPLAY       = "REPLAY"
    PAPER_TRADING = "PAPER_TRADING"
    BACKTEST     = "BACKTEST"


class ExecutionMode(str, Enum):
    """Execution environment for a queued order."""
    LIVE       = "LIVE"
    PAPER      = "PAPER"
    BACKTEST   = "BACKTEST"
    SIMULATION = "SIMULATION"
    RECOVERY   = "RECOVERY"


class QueueEventType(str, Enum):
    """Events emitted by the Order Queue."""
    ORDER_QUEUED      = "ORDER_QUEUED"
    QUEUE_UPDATED     = "QUEUE_UPDATED"
    PRIORITY_CHANGED  = "PRIORITY_CHANGED"
    ORDER_DISPATCHED  = "ORDER_DISPATCHED"
    RETRY_SCHEDULED   = "RETRY_SCHEDULED"
    QUEUE_SUSPENDED   = "QUEUE_SUSPENDED"
    QUEUE_RESUMED     = "QUEUE_RESUMED"
    QUEUE_CLEARED     = "QUEUE_CLEARED"


class QueueValidationCode(str, Enum):
    """Machine-readable validation failure codes."""
    MISSING_ORDER_ID         = "MISSING_ORDER_ID"
    DUPLICATE_ENTRY          = "DUPLICATE_ENTRY"
    INVALID_PRIORITY         = "INVALID_PRIORITY"
    INVALID_SCHEDULE         = "INVALID_SCHEDULE"
    RETRY_LIMIT_EXCEEDED     = "RETRY_LIMIT_EXCEEDED"
    QUEUE_FULL               = "QUEUE_FULL"
    QUEUE_NOT_RUNNING        = "QUEUE_NOT_RUNNING"
    ENTRY_EXPIRED            = "ENTRY_EXPIRED"
    ENTRY_NOT_FOUND          = "ENTRY_NOT_FOUND"
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
