"""
iios/observation/observation_constants.py
==========================================
All enumerations, numeric limits, and string constants for the
IIOS Observation Engine.

The Observation Layer is the mandatory gateway between the outside
world and IIOS. Every external input must first become an
``Observation`` before it can be promoted to ``Knowledge``.
"""

from __future__ import annotations

from enum import Enum
from typing import Final

__all__ = [
    # Enumerations
    "ObservationType",
    "ObservationStatus",
    "ObservationPriority",
    "ObservationSource",
    "ObservationDomain",
    "ObservationQuality",
    "ValidationOutcome",
    "ClassificationMethod",
    "EnrichmentType",
    "LifecycleEvent",
    "DuplicatePolicy",
    "ConflictResolution",
    "CollectorType",
    "PipelineStage",
    # Numeric constants
    "DEFAULT_CONFIDENCE",
    "MIN_CONFIDENCE",
    "MAX_CONFIDENCE",
    "DEFAULT_TTL_SECONDS",
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "MAX_TAGS",
    "MAX_BATCH_SIZE",
    "MAX_CACHE_SIZE",
    "MAX_OBSERVATIONS_IN_MEMORY",
    "DUPLICATE_WINDOW_SECONDS",
    "STALENESS_THRESHOLD_SECONDS",
    "MAX_ENRICHMENT_ROUNDS",
    "MAX_VALIDATION_ROUNDS",
    # String constants
    "OBSERVATION_NAMESPACE",
    "SYSTEM_OBSERVER",
    "ANONYMOUS_SOURCE",
    "OBSERVATION_SCHEMA_VERSION",
    # Utility enums
    "SortOrder",
]


# ── Observation types ──────────────────────────────────────────────────────────

class ObservationType(str, Enum):
    """Category of raw observation entering IIOS."""

    MARKET_DATA      = "market_data"       # OHLCV, tick, quote, spread
    NEWS             = "news"              # News article, press release
    INDICATOR        = "indicator"         # Technical/fundamental indicator
    SIGNAL           = "signal"            # Trading signal
    ECONOMIC         = "economic"          # Macro economic data point
    CORPORATE_ACTION = "corporate_action"  # Dividend, split, bonus
    SOCIAL           = "social"            # Social media, sentiment
    SYSTEM_EVENT     = "system_event"      # Internal system events
    RISK_METRIC      = "risk_metric"       # Risk/exposure reading
    ORDER_EVENT      = "order_event"       # Order status/execution event
    TRADE_EVENT      = "trade_event"       # Trade confirmation/fill
    PORTFOLIO        = "portfolio"         # Portfolio snapshot
    ALERT            = "alert"             # System or market alert
    RESEARCH         = "research"          # Research note or report
    REGULATORY       = "regulatory"        # Regulatory filing
    WEATHER          = "weather"           # Climate/weather data
    GEOPOLITICAL     = "geopolitical"      # Geopolitical event
    EARNINGS         = "earnings"          # Company earnings data
    CUSTOM           = "custom"            # User-defined type
    UNKNOWN          = "unknown"


# ── Lifecycle status ───────────────────────────────────────────────────────────

class ObservationStatus(str, Enum):
    """Lifecycle state of an observation."""

    CREATED    = "created"     # Just created; not yet submitted to pipeline
    COLLECTED  = "collected"   # Received from a collector; in queue
    VALIDATING = "validating"  # Validator is running
    VALIDATED  = "validated"   # Passed validation
    CLASSIFYING = "classifying" # Classifier is running
    CLASSIFIED  = "classified"  # Classification complete
    ENRICHING  = "enriching"   # Enrichment is running
    ENRICHED   = "enriched"    # Enrichment complete
    ACCEPTED   = "accepted"    # Accepted into IIOS; ready for Knowledge
    REJECTED   = "rejected"    # Failed validation or policy
    ARCHIVED   = "archived"    # Moved to cold storage
    EXPIRED    = "expired"     # TTL elapsed; no longer active
    DELETED    = "deleted"     # Soft-deleted


# ── Priority ───────────────────────────────────────────────────────────────────

class ObservationPriority(int, Enum):
    """Processing priority."""

    CRITICAL = 5
    HIGH     = 4
    MEDIUM   = 3
    LOW      = 2
    MINIMAL  = 1


# ── Source ────────────────────────────────────────────────────────────────────

class ObservationSource(str, Enum):
    """Origin feed / system that produced the observation."""

    DHAN_FEED      = "dhan_feed"
    YFINANCE       = "yfinance"
    NSE_FEED       = "nse_feed"
    BSE_FEED       = "bse_feed"
    ZERODHA        = "zerodha"
    BLOOMBERG      = "bloomberg"
    REUTERS        = "reuters"
    INTERNAL_AGENT = "internal_agent"
    MANUAL_ENTRY   = "manual_entry"
    BACKTEST       = "backtest"
    SIMULATION     = "simulation"
    TELEGRAM       = "telegram"
    WEBHOOK        = "webhook"
    API_CALL       = "api_call"
    FILE_IMPORT    = "file_import"
    SCHEDULER      = "scheduler"
    SYSTEM         = "system"
    UNKNOWN        = "unknown"


# ── Domain ────────────────────────────────────────────────────────────────────

class ObservationDomain(str, Enum):
    """Business domain the observation belongs to."""

    MARKET      = "market"
    TRADING     = "trading"
    RISK        = "risk"
    PORTFOLIO   = "portfolio"
    RESEARCH    = "research"
    OPERATIONS  = "operations"
    COMPLIANCE  = "compliance"
    SYSTEM      = "system"
    GENERAL     = "general"


# ── Quality tier ──────────────────────────────────────────────────────────────

class ObservationQuality(str, Enum):
    """Computed quality tier for an observation."""

    EXCELLENT = "excellent"   # ≥ 0.80
    GOOD      = "good"        # ≥ 0.60
    FAIR      = "fair"        # ≥ 0.40
    POOR      = "poor"        # < 0.40

    @property
    def threshold(self) -> float:
        _t = {"excellent": 0.80, "good": 0.60, "fair": 0.40, "poor": 0.0}
        return _t[self.value]


# ── Validation ────────────────────────────────────────────────────────────────

class ValidationOutcome(str, Enum):
    PASS    = "pass"
    FAIL    = "fail"
    WARNING = "warning"
    SKIP    = "skip"


# ── Classification ────────────────────────────────────────────────────────────

class ClassificationMethod(str, Enum):
    RULE_BASED   = "rule_based"
    ML_MODEL     = "ml_model"
    HEURISTIC    = "heuristic"
    MANUAL       = "manual"
    DERIVED      = "derived"


# ── Enrichment ────────────────────────────────────────────────────────────────

class EnrichmentType(str, Enum):
    METADATA     = "metadata"       # Add/complete metadata
    CONTEXT      = "context"        # Add market/session context
    RELATIONSHIP = "relationship"   # Link to existing knowledge
    NORMALISE    = "normalise"      # Normalise units/format
    SENTIMENT    = "sentiment"      # Add sentiment score
    RISK         = "risk"           # Add risk overlay
    TAGGING      = "tagging"        # Auto-tag
    GEOLOCATION  = "geolocation"    # Add geo context


# ── Lifecycle events ──────────────────────────────────────────────────────────

class LifecycleEvent(str, Enum):
    CREATED      = "obs.created"
    COLLECTED    = "obs.collected"
    VALIDATED    = "obs.validated"
    REJECTED     = "obs.rejected"
    CLASSIFIED   = "obs.classified"
    ENRICHED     = "obs.enriched"
    ACCEPTED     = "obs.accepted"
    ARCHIVED     = "obs.archived"
    EXPIRED      = "obs.expired"
    DELETED      = "obs.deleted"
    UPDATED      = "obs.updated"
    DUPLICATE    = "obs.duplicate"


# ── Duplicate handling ────────────────────────────────────────────────────────

class DuplicatePolicy(str, Enum):
    REJECT      = "reject"      # Drop duplicate, raise error
    SKIP        = "skip"        # Silently skip
    OVERWRITE   = "overwrite"   # Replace existing
    MERGE       = "merge"       # Merge payloads
    VERSION     = "version"     # Create new version


# ── Conflict resolution ───────────────────────────────────────────────────────

class ConflictResolution(str, Enum):
    LATEST_WINS  = "latest_wins"
    HIGHEST_CONF = "highest_confidence"
    MANUAL       = "manual"
    REJECT_BOTH  = "reject_both"


# ── Collector ─────────────────────────────────────────────────────────────────

class CollectorType(str, Enum):
    PUSH     = "push"    # Source pushes data in
    PULL     = "pull"    # Collector polls source
    STREAM   = "stream"  # Continuous stream (WebSocket)
    BATCH    = "batch"   # Periodic bulk collection
    EVENT    = "event"   # Event-driven (callback)
    MANUAL   = "manual"  # Human entry


# ── Pipeline stage ────────────────────────────────────────────────────────────

class PipelineStage(str, Enum):
    INGEST      = "ingest"
    VALIDATE    = "validate"
    CLASSIFY    = "classify"
    ENRICH      = "enrich"
    STORE       = "store"
    PUBLISH     = "publish"


# ── Numeric constants ──────────────────────────────────────────────────────────

DEFAULT_CONFIDENCE:              Final[float] = 0.50
MIN_CONFIDENCE:                  Final[float] = 0.0
MAX_CONFIDENCE:                  Final[float] = 1.0
DEFAULT_TTL_SECONDS:             Final[int]   = 86_400        # 24 hours
DEFAULT_PAGE_SIZE:               Final[int]   = 50
MAX_PAGE_SIZE:                   Final[int]   = 1_000
MAX_TAGS:                        Final[int]   = 20
MAX_BATCH_SIZE:                  Final[int]   = 500
MAX_CACHE_SIZE:                  Final[int]   = 10_000
MAX_OBSERVATIONS_IN_MEMORY:      Final[int]   = 100_000
DUPLICATE_WINDOW_SECONDS:        Final[int]   = 300           # 5 min dedup window
STALENESS_THRESHOLD_SECONDS:     Final[int]   = 3_600         # 1 hour
MAX_ENRICHMENT_ROUNDS:           Final[int]   = 3
MAX_VALIDATION_ROUNDS:           Final[int]   = 2

# ── String constants ───────────────────────────────────────────────────────────

OBSERVATION_NAMESPACE:    Final[str] = "iios.observation"
SYSTEM_OBSERVER:          Final[str] = "iios:system"
ANONYMOUS_SOURCE:         Final[str] = "iios:anonymous"
OBSERVATION_SCHEMA_VERSION: Final[str] = "1.0.0"


# ── Sort order ────────────────────────────────────────────────────────────────

class SortOrder(str, Enum):
    ASC  = "asc"
    DESC = "desc"
