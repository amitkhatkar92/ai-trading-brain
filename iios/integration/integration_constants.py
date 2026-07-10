"""iios/integration/integration_constants.py

All enumerations and module-level constants for the Data Integration Layer.
"""
from __future__ import annotations

from enum import Enum


# ── Provider ──────────────────────────────────────────────────────────────────

class ProviderStatus(str, Enum):
    ACTIVE       = "active"
    INACTIVE     = "inactive"
    DEGRADED     = "degraded"
    FAILED       = "failed"
    INITIALIZING = "initializing"
    SHUTTING_DOWN = "shutting_down"
    UNKNOWN      = "unknown"


class ProviderPriority(int, Enum):
    """Lower value = higher priority."""
    CRITICAL = 1
    HIGH     = 2
    NORMAL   = 3
    LOW      = 4
    FALLBACK = 5


# ── Data ──────────────────────────────────────────────────────────────────────

class DataCategory(str, Enum):
    MARKET_DATA   = "market_data"
    FUNDAMENTAL   = "fundamental"
    NEWS          = "news"
    MACRO         = "macro"
    ALTERNATIVE   = "alternative"
    REFERENCE     = "reference"
    SENTIMENT     = "sentiment"
    RISK          = "risk"
    CORPORATE     = "corporate"
    DERIVATIVE    = "derivative"


class DataFrequency(str, Enum):
    TICK    = "tick"
    SECOND  = "second"
    MINUTE  = "minute"
    HOUR    = "hour"
    DAILY   = "daily"
    WEEKLY  = "weekly"
    MONTHLY = "monthly"
    ANNUAL  = "annual"
    ON_DEMAND = "on_demand"


class DataQualityLevel(str, Enum):
    HIGH   = "high"
    MEDIUM = "medium"
    LOW    = "low"
    UNKNOWN = "unknown"


# ── Pipeline ──────────────────────────────────────────────────────────────────

class PipelineStageType(str, Enum):
    EXTRACT    = "extract"
    VALIDATE   = "validate"
    NORMALIZE  = "normalize"
    TRANSFORM  = "transform"
    ENRICH     = "enrich"
    CACHE      = "cache"
    PUBLISH    = "publish"


class PipelineStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"
    PARTIAL   = "partial"


class PipelineStageStatus(str, Enum):
    SKIPPED   = "skipped"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"


# ── Integration events ────────────────────────────────────────────────────────

class IntegrationEventType(str, Enum):
    PROVIDER_REGISTERED    = "provider_registered"
    PROVIDER_DEREGISTERED  = "provider_deregistered"
    PROVIDER_ACTIVATED     = "provider_activated"
    PROVIDER_DEACTIVATED   = "provider_deactivated"
    PROVIDER_HEALTH_CHANGED = "provider_health_changed"
    PROVIDER_FAILED        = "provider_failed"
    PROVIDER_RECOVERED     = "provider_recovered"
    FETCH_STARTED          = "fetch_started"
    FETCH_COMPLETED        = "fetch_completed"
    FETCH_FAILED           = "fetch_failed"
    PIPELINE_STARTED       = "pipeline_started"
    PIPELINE_COMPLETED     = "pipeline_completed"
    PIPELINE_FAILED        = "pipeline_failed"
    CACHE_HIT              = "cache_hit"
    CACHE_MISS             = "cache_miss"
    VALIDATION_FAILED      = "validation_failed"
    NORMALIZATION_FAILED   = "normalization_failed"
    ENGINE_STARTED         = "engine_started"
    ENGINE_STOPPED         = "engine_stopped"


# ── Circuit breaker ───────────────────────────────────────────────────────────

class CircuitBreakerState(str, Enum):
    CLOSED    = "closed"      # Normal operation
    OPEN      = "open"        # Provider blocked
    HALF_OPEN = "half_open"   # Testing recovery


# ── Validation ────────────────────────────────────────────────────────────────

class ValidationSeverity(str, Enum):
    ERROR   = "error"
    WARNING = "warning"
    INFO    = "info"


class ValidationStatus(str, Enum):
    PASSED  = "passed"
    FAILED  = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"


# ── Cache ─────────────────────────────────────────────────────────────────────

class CacheStrategy(str, Enum):
    TTL           = "ttl"
    LRU           = "lru"
    NO_CACHE      = "no_cache"
    WRITE_THROUGH = "write_through"


# ── Normalization ─────────────────────────────────────────────────────────────

class NormalizationStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED  = "failed"
    SKIPPED = "skipped"


# ── Health ────────────────────────────────────────────────────────────────────

class HealthStatus(str, Enum):
    HEALTHY   = "healthy"
    DEGRADED  = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN   = "unknown"


# ── Integration engine ────────────────────────────────────────────────────────

class IntegrationEngineStatus(str, Enum):
    STOPPED      = "stopped"
    INITIALIZING = "initializing"
    RUNNING      = "running"
    DEGRADED     = "degraded"
    STOPPING     = "stopping"
    ERROR        = "error"


# ── Module metadata ───────────────────────────────────────────────────────────

INTEGRATION_ENGINE_VERSION   = "1.0.0"
INTEGRATION_ENGINE_SYSTEM_ID = "iios:integration:engine"
INTEGRATION_ERROR_PREFIX     = "DI"

# Timeouts and limits
DEFAULT_PROVIDER_TIMEOUT_SEC      = 30.0
DEFAULT_FETCH_TIMEOUT_SEC         = 15.0
DEFAULT_HEALTH_CHECK_INTERVAL_SEC = 60.0
DEFAULT_HEALTH_CHECK_TIMEOUT_SEC  = 5.0
DEFAULT_MAX_PROVIDERS             = 500
DEFAULT_MAX_RECORDS_PER_RESPONSE  = 100_000
DEFAULT_RETRY_ATTEMPTS            = 3
DEFAULT_RETRY_BACKOFF_SEC         = 1.0
DEFAULT_RETRY_MAX_BACKOFF_SEC     = 30.0
DEFAULT_CIRCUIT_BREAKER_THRESHOLD = 5       # failures before open
DEFAULT_CIRCUIT_BREAKER_RESET_SEC = 60.0
DEFAULT_CACHE_TTL_SEC             = 300.0   # 5 minutes
DEFAULT_CACHE_MAX_ENTRIES         = 10_000

# Quality thresholds
DEFAULT_MIN_QUALITY_SCORE         = 0.6
DEFAULT_HIGH_LATENCY_WARNING_MS   = 2_000.0
DEFAULT_HIGH_LATENCY_CRITICAL_MS  = 10_000.0
DEFAULT_MAX_FAILURE_RATE          = 0.10    # 10%
DEFAULT_MIN_AVAILABILITY_PCT      = 0.95    # 95%

# Schema versioning
CANONICAL_SCHEMA_VERSION = "1.0"
