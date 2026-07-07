"""
iios/observation/collectors/collector_constants.py
==================================================
All enumerations and constants for the IIOS Observation Collection Framework.
"""
from __future__ import annotations

from enum import Enum
from typing import Final

__all__ = [
    "CollectorStatus",
    "CollectorCategory",
    "RetryStrategy",
    "ScheduleType",
    "CircuitBreakerState",
    "ExecutionMode",
    "LifecycleStage",
    # Numeric constants
    "DEFAULT_TIMEOUT_S",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_BACKOFF_BASE_S",
    "DEFAULT_BACKOFF_MAX_S",
    "DEFAULT_POLL_INTERVAL_S",
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_CIRCUIT_FAILURE_THRESHOLD",
    "DEFAULT_CIRCUIT_RECOVERY_S",
    "DEFAULT_RATE_LIMIT_CALLS",
    "DEFAULT_RATE_LIMIT_WINDOW_S",
    "MAX_PARALLEL_COLLECTORS",
    "CHECKPOINT_INTERVAL_S",
    # String constants
    "COLLECTOR_NAMESPACE",
    "SYSTEM_COLLECTOR",
]


class CollectorStatus(str, Enum):
    """Runtime status of a collector instance."""
    IDLE           = "idle"
    INITIALISING   = "initialising"
    CONFIGURED     = "configured"
    AUTHENTICATING = "authenticating"
    CONNECTING     = "connecting"
    COLLECTING     = "collecting"
    PAUSED         = "paused"
    ERROR          = "error"
    STOPPING       = "stopping"
    STOPPED        = "stopped"


class CollectorCategory(str, Enum):
    """Logical category of data a collector acquires."""
    MARKET_DATA  = "market_data"
    NEWS         = "news"
    MACRO        = "macro"
    CORPORATE    = "corporate"
    FINANCIAL    = "financial"
    EXCHANGE     = "exchange"
    BROKER       = "broker"
    ALTERNATIVE  = "alternative"
    SOCIAL       = "social"
    RESEARCH     = "research"
    INTERNAL     = "internal"
    PLUGIN       = "plugin"


class RetryStrategy(str, Enum):
    NONE        = "none"
    FIXED       = "fixed"
    LINEAR      = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI   = "fibonacci"


class ScheduleType(str, Enum):
    MANUAL       = "manual"
    INTERVAL     = "interval"
    CRON         = "cron"
    MARKET_HOURS = "market_hours"
    EVENT        = "event"
    DEPENDENCY   = "dependency"


class CircuitBreakerState(str, Enum):
    CLOSED    = "closed"
    OPEN      = "open"
    HALF_OPEN = "half_open"


class ExecutionMode(str, Enum):
    SYNC   = "sync"
    ASYNC  = "async"
    STREAM = "stream"
    BATCH  = "batch"


class LifecycleStage(str, Enum):
    INITIALISE   = "initialise"
    CONFIGURE    = "configure"
    AUTHENTICATE = "authenticate"
    CONNECT      = "connect"
    COLLECT      = "collect"
    VALIDATE     = "validate"
    NORMALISE    = "normalise"
    PUBLISH      = "publish"
    RETRY        = "retry"
    SHUTDOWN     = "shutdown"
    HEALTH_CHECK = "health_check"


# ── Numeric constants ─────────────────────────────────────────────────────────
DEFAULT_TIMEOUT_S:                  Final[float] = 30.0
DEFAULT_MAX_RETRIES:                Final[int]   = 3
DEFAULT_BACKOFF_BASE_S:             Final[float] = 1.0
DEFAULT_BACKOFF_MAX_S:              Final[float] = 60.0
DEFAULT_POLL_INTERVAL_S:            Final[float] = 60.0
DEFAULT_BATCH_SIZE:                 Final[int]   = 100
DEFAULT_CIRCUIT_FAILURE_THRESHOLD:  Final[int]   = 5
DEFAULT_CIRCUIT_RECOVERY_S:         Final[float] = 30.0
DEFAULT_RATE_LIMIT_CALLS:           Final[int]   = 60
DEFAULT_RATE_LIMIT_WINDOW_S:        Final[float] = 60.0
MAX_PARALLEL_COLLECTORS:            Final[int]   = 32
CHECKPOINT_INTERVAL_S:              Final[float] = 300.0

# ── String constants ──────────────────────────────────────────────────────────
COLLECTOR_NAMESPACE: Final[str] = "iios.collector"
SYSTEM_COLLECTOR:    Final[str] = "iios:collector:system"
