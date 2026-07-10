"""iios/integration/history/history_constants.py

All enumerations and module-level constants for the Historical Data & Replay
Framework.
"""
from __future__ import annotations

from enum import Enum, IntEnum


# ── Data type catalogue ────────────────────────────────────────────────────────

class HistoricalDataType(str, Enum):
    """Broad category of historical data stored in a dataset."""
    MARKET_DATA   = "market_data"
    NEWS          = "news"
    ALTERNATIVE   = "alternative"
    MACRO         = "macro"
    FUNDAMENTAL   = "fundamental"
    OBSERVATION   = "observation"
    KNOWLEDGE     = "knowledge"
    DECISION      = "decision"
    EXECUTION     = "execution"
    PORTFOLIO     = "portfolio"
    STRATEGY      = "strategy"
    AUDIT         = "audit"
    CUSTOM        = "custom"


# ── Storage ────────────────────────────────────────────────────────────────────

class DataFormat(str, Enum):
    RAW        = "raw"
    COMPRESSED = "compressed"
    DELTA      = "delta"       # differential record vs previous
    SNAPSHOT   = "snapshot"    # full point-in-time copy


class CompressionType(str, Enum):
    NONE  = "none"
    ZLIB  = "zlib"
    GZIP  = "gzip"


class PartitionStrategy(str, Enum):
    BY_DATE   = "by_date"
    BY_SYMBOL = "by_symbol"
    BY_TYPE   = "by_type"
    BY_SIZE   = "by_size"
    NONE      = "none"


class DatasetStatus(str, Enum):
    ACTIVE   = "active"
    ARCHIVED = "archived"
    LOADING  = "loading"
    SAVING   = "saving"
    ERROR    = "error"


class StorageStatus(str, Enum):
    AVAILABLE = "available"
    LOADING   = "loading"
    SAVING    = "saving"
    ARCHIVED  = "archived"
    ERROR     = "error"


# ── Replay ─────────────────────────────────────────────────────────────────────

class ReplayMode(str, Enum):
    FORWARD  = "forward"
    REVERSE  = "reverse"
    SEEK     = "seek"
    JUMP     = "jump"


class ReplayStatus(str, Enum):
    IDLE      = "idle"
    RUNNING   = "running"
    PAUSED    = "paused"
    STOPPED   = "stopped"
    COMPLETED = "completed"
    ERROR     = "error"


class ReplayType(str, Enum):
    MARKET      = "market"
    NEWS        = "news"
    OBSERVATION = "observation"
    KNOWLEDGE   = "knowledge"
    DECISION    = "decision"
    EXECUTION   = "execution"
    PORTFOLIO   = "portfolio"
    STRATEGY    = "strategy"
    FULL_SYSTEM = "full_system"
    CUSTOM      = "custom"


# ── Timeline ───────────────────────────────────────────────────────────────────

class TimelineDirection(str, Enum):
    FORWARD  = "forward"
    REVERSE  = "reverse"


class TimelineStatus(str, Enum):
    IDLE     = "idle"
    ACTIVE   = "active"
    PAUSED   = "paused"
    SEEKING  = "seeking"
    STOPPED  = "stopped"


# ── Simulation ─────────────────────────────────────────────────────────────────

class SimulationMode(str, Enum):
    BACKTEST      = "backtest"
    PAPER_TRADING = "paper_trading"
    AI_TRAINING   = "ai_training"
    SCENARIO      = "scenario"
    CUSTOM        = "custom"


class SimulationStatus(str, Enum):
    IDLE      = "idle"
    RUNNING   = "running"
    PAUSED    = "paused"
    COMPLETED = "completed"
    ERROR     = "error"


# ── Query ──────────────────────────────────────────────────────────────────────

class QueryOperator(str, Enum):
    EQ       = "eq"
    NE       = "ne"
    GT       = "gt"
    LT       = "lt"
    GTE      = "gte"
    LTE      = "lte"
    IN       = "in"
    NOT_IN   = "not_in"
    CONTAINS = "contains"
    BETWEEN  = "between"


class SortOrder(str, Enum):
    ASC  = "asc"
    DESC = "desc"


# ── Analytics ──────────────────────────────────────────────────────────────────

class AnalyticsInterval(str, Enum):
    TICK   = "tick"
    SECOND = "second"
    MINUTE = "minute"
    HOUR   = "hour"
    DAY    = "day"
    WEEK   = "week"
    MONTH  = "month"
    YEAR   = "year"


# ── Engine ─────────────────────────────────────────────────────────────────────

class HistoryEngineStatus(str, Enum):
    STOPPED      = "stopped"
    INITIALIZING = "initializing"
    RUNNING      = "running"
    STOPPING     = "stopping"
    ERROR        = "error"


# ── Module metadata ────────────────────────────────────────────────────────────

HISTORY_ENGINE_VERSION    = "1.0.0"
HISTORY_ENGINE_SYSTEM_ID  = "iios:integration:history:engine"
HISTORY_ERROR_PREFIX      = "HD"

# Storage limits
DEFAULT_MAX_DATASETS          = 10_000
DEFAULT_PARTITION_SIZE        = 100_000     # max records per partition
DEFAULT_SNAPSHOT_INTERVAL_SEC = 3_600       # auto-snapshot every hour
DEFAULT_RETENTION_DAYS        = 3_650       # 10 years
DEFAULT_MAX_RECORD_SIZE_BYTES = 1_048_576   # 1 MB per record
DEFAULT_COMPRESSION_LEVEL     = 6

# Replay limits
DEFAULT_REPLAY_SPEED          = 1.0
MAX_REPLAY_SPEED              = 10_000.0
MIN_REPLAY_SPEED              = 0.0001
DEFAULT_REPLAY_BATCH_SIZE     = 1_000
DEFAULT_REPLAY_BUFFER_SIZE    = 50_000

# Query limits
DEFAULT_MAX_QUERY_RESULTS     = 100_000
DEFAULT_QUERY_TIMEOUT_SEC     = 60.0
DEFAULT_PAGE_SIZE             = 1_000

# Cache
DEFAULT_CACHE_TTL_SEC         = 3_600
DEFAULT_CACHE_MAX_RECORDS     = 500_000

# Timeline
DEFAULT_TIMELINE_TICK_MS      = 100         # minimum tick interval
MAX_TIMELINE_EVENTS           = 10_000_000  # events held in one timeline

# Index
DEFAULT_INDEX_GRANULARITY_SEC = 60          # one index entry per minute
