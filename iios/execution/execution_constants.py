"""iios/execution/execution_constants.py"""
from __future__ import annotations

from enum import Enum


class ExecutionStatus(str, Enum):
    CREATED   = "created"
    PLANNED   = "planned"
    VALIDATED = "validated"
    APPROVED  = "approved"
    QUEUED    = "queued"
    EXECUTING = "executing"
    PAUSED    = "paused"
    RESUMED   = "resumed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED    = "failed"
    ARCHIVED  = "archived"


class ExecutionMode(str, Enum):
    IMMEDIATE  = "immediate"
    SCHEDULED  = "scheduled"
    BATCH      = "batch"
    SIMULATION = "simulation"
    PAPER      = "paper"
    LIVE       = "live"


class ExecutionType(str, Enum):
    BUY       = "buy"
    SELL      = "sell"
    SHORT     = "short"
    COVER     = "cover"
    REBALANCE = "rebalance"
    HEDGE     = "hedge"
    ROLLOVER  = "rollover"
    CUSTOM    = "custom"
    UNKNOWN   = "unknown"


class ExecutionPriority(str, Enum):
    CRITICAL   = "critical"
    HIGH       = "high"
    NORMAL     = "normal"
    LOW        = "low"
    BACKGROUND = "background"


class WorkflowStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"


class WorkflowStepStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    SKIPPED   = "skipped"
    FAILED    = "failed"


class ExecutionEventType(str, Enum):
    CREATED        = "created"
    PLANNED        = "planned"
    VALIDATED      = "validated"
    APPROVED       = "approved"
    QUEUED         = "queued"
    STARTED        = "started"
    PAUSED         = "paused"
    RESUMED        = "resumed"
    COMPLETED      = "completed"
    CANCELLED      = "cancelled"
    FAILED         = "failed"
    ARCHIVED       = "archived"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED    = "step_failed"
    RETRIED        = "retried"


class TimeInForce(str, Enum):
    DAY = "DAY"
    GTC = "GTC"    # Good Till Cancelled
    IOC = "IOC"    # Immediate or Cancel
    FOK = "FOK"    # Fill or Kill


# ── Engine metadata ───────────────────────────────────────────────────────────

EXECUTION_ENGINE_VERSION   = "1.0.0"
EXECUTION_ENGINE_SYSTEM_ID = "iios:execution:engine"

# ── Capacity ──────────────────────────────────────────────────────────────────

DEFAULT_MAX_SESSIONS        = 10_000
DEFAULT_MAX_HISTORY         = 50_000
DEFAULT_SESSION_TTL_SEC     = 86_400.0     # 24 hours
DEFAULT_MAX_RETRIES         = 3
DEFAULT_WORKER_THREADS      = 4
DEFAULT_QUEUE_SIZE          = 1_000

# ── Validation thresholds ─────────────────────────────────────────────────────

MIN_QUANTITY                = 0.0001
MAX_QUANTITY                = 1_000_000.0
MAX_PRICE                   = 1_000_000_000.0

# ── Valid status transitions ──────────────────────────────────────────────────

VALID_TRANSITIONS: dict[ExecutionStatus, list[ExecutionStatus]] = {
    ExecutionStatus.CREATED:   [ExecutionStatus.PLANNED,   ExecutionStatus.CANCELLED],
    ExecutionStatus.PLANNED:   [ExecutionStatus.VALIDATED, ExecutionStatus.CANCELLED],
    ExecutionStatus.VALIDATED: [ExecutionStatus.APPROVED,  ExecutionStatus.CANCELLED],
    ExecutionStatus.APPROVED:  [ExecutionStatus.QUEUED,    ExecutionStatus.CANCELLED],
    ExecutionStatus.QUEUED:    [ExecutionStatus.EXECUTING, ExecutionStatus.CANCELLED],
    ExecutionStatus.EXECUTING: [ExecutionStatus.PAUSED,    ExecutionStatus.COMPLETED,
                                ExecutionStatus.FAILED,    ExecutionStatus.CANCELLED],
    ExecutionStatus.PAUSED:    [ExecutionStatus.RESUMED,   ExecutionStatus.CANCELLED],
    ExecutionStatus.RESUMED:   [ExecutionStatus.EXECUTING, ExecutionStatus.COMPLETED,
                                ExecutionStatus.FAILED,    ExecutionStatus.CANCELLED],
    ExecutionStatus.COMPLETED: [ExecutionStatus.ARCHIVED],
    ExecutionStatus.FAILED:    [ExecutionStatus.ARCHIVED],
    ExecutionStatus.CANCELLED: [ExecutionStatus.ARCHIVED],
    ExecutionStatus.ARCHIVED:  [],
}

TERMINAL_STATUSES = frozenset({
    ExecutionStatus.COMPLETED,
    ExecutionStatus.CANCELLED,
    ExecutionStatus.FAILED,
    ExecutionStatus.ARCHIVED,
})

ACTIVE_STATUSES = frozenset({
    ExecutionStatus.CREATED,
    ExecutionStatus.PLANNED,
    ExecutionStatus.VALIDATED,
    ExecutionStatus.APPROVED,
    ExecutionStatus.QUEUED,
    ExecutionStatus.EXECUTING,
    ExecutionStatus.PAUSED,
    ExecutionStatus.RESUMED,
})
