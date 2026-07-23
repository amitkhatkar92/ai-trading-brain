"""
constants.py — iios.risk.snapshot
====================================
Enumerations, identifiers, and defaults for the Risk Snapshot Framework.

C11 Risk Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet, Tuple

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
SNAPSHOT_SYSTEM_ID:  str = "iios:risk:snapshot"
BUILDER_SYSTEM_ID:   str = "iios:risk:snapshot:builder"
REGISTRY_SYSTEM_ID:  str = "iios:risk:snapshot:registry"
STORE_SYSTEM_ID:     str = "iios:risk:snapshot:store"
CACHE_SYSTEM_ID:     str = "iios:risk:snapshot:cache"
FACTORY_SYSTEM_ID:   str = "iios:risk:snapshot:factory"
HISTORY_SYSTEM_ID:   str = "iios:risk:snapshot:history"
BUNDLE_SYSTEM_ID:    str = "iios:risk:snapshot:bundle"

# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------
VERSION:        str = "1.0.0"
SCHEMA_VERSION: str = "1.0"

# ---------------------------------------------------------------------------
# Actors
# ---------------------------------------------------------------------------
ACTOR_SNAPSHOT_BUILDER:  str = "iios:risk:snapshot:builder"
ACTOR_SNAPSHOT_FACTORY:  str = "iios:risk:snapshot:factory"
ACTOR_SNAPSHOT_REGISTRY: str = "iios:risk:snapshot:registry"
ACTOR_SYSTEM:            str = "iios:system"
ACTOR_OPERATOR:          str = "operator"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_MAX_SNAPSHOTS:   int   = 50_000
DEFAULT_MAX_HISTORY:     int   = 1_000
DEFAULT_MAX_BUNDLE_SIZE: int   = 500
DEFAULT_CACHE_TTL_S:     float = 300.0   # 5 minutes
DEFAULT_CACHE_MAX_SIZE:  int   = 1_000
DEFAULT_SNAPSHOT_TIMEOUT_S: float = 30.0

# Snapshot size estimate — average bytes per snapshot for budget checks
AVG_SNAPSHOT_SIZE_BYTES: int = 8_192

# ---------------------------------------------------------------------------
# SnapshotStatus
# ---------------------------------------------------------------------------
class SnapshotStatus(str, Enum):
    """Lifecycle state of a risk snapshot."""
    BUILDING     = "building"
    PUBLISHED    = "published"
    INVALIDATED  = "invalidated"
    SUPERSEDED   = "superseded"
    ARCHIVED     = "archived"
    FAILED       = "failed"


# ---------------------------------------------------------------------------
# RiskScope
# ---------------------------------------------------------------------------
class RiskScope(str, Enum):
    """Scope of the risk assessment captured in the snapshot."""
    TRADE      = "trade"
    STRATEGY   = "strategy"
    PORTFOLIO  = "portfolio"
    ACCOUNT    = "account"
    ENTERPRISE = "enterprise"


# ---------------------------------------------------------------------------
# RiskType
# ---------------------------------------------------------------------------
class RiskType(str, Enum):
    """Dominant risk type captured in the snapshot."""
    MARKET         = "market"
    CREDIT         = "credit"
    LIQUIDITY      = "liquidity"
    OPERATIONAL    = "operational"
    INFRASTRUCTURE = "infrastructure"
    COUNTERPARTY   = "counterparty"
    CONCENTRATION  = "concentration"
    MODEL          = "model"
    COMPOSITE      = "composite"
    ENTERPRISE     = "enterprise"


# ---------------------------------------------------------------------------
# RiskPriority
# ---------------------------------------------------------------------------
class RiskPriority(str, Enum):
    """Processing priority for the risk snapshot."""
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"


# ---------------------------------------------------------------------------
# RiskLevel
# ---------------------------------------------------------------------------
class RiskLevel(str, Enum):
    """Categorical risk severity level."""
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"
    MINIMAL  = "minimal"


# ---------------------------------------------------------------------------
# RiskRating
# ---------------------------------------------------------------------------
class RiskRating(str, Enum):
    """Enterprise risk rating (best → worst)."""
    EXCELLENT = "excellent"   # score ≤ 20
    GOOD      = "good"        # score ≤ 40
    FAIR      = "fair"        # score ≤ 60
    POOR      = "poor"        # score ≤ 80
    CRITICAL  = "critical"    # score > 80


# ---------------------------------------------------------------------------
# RiskTrend
# ---------------------------------------------------------------------------
class RiskTrend(str, Enum):
    """Directional trend of the risk score."""
    IMPROVING  = "improving"
    STABLE     = "stable"
    WORSENING  = "worsening"
    VOLATILE   = "volatile"
    UNKNOWN    = "unknown"


# ---------------------------------------------------------------------------
# IntegrityStatus
# ---------------------------------------------------------------------------
class IntegrityStatus(str, Enum):
    """Snapshot integrity / validation state."""
    VALID    = "valid"
    INVALID  = "invalid"
    DEGRADED = "degraded"
    UNKNOWN  = "unknown"


# ---------------------------------------------------------------------------
# SnapshotEventType — 10 domain events
# ---------------------------------------------------------------------------
class SnapshotEventType(str, Enum):
    """Domain events emitted by the snapshot framework."""
    SNAPSHOT_BUILT      = "snapshot_built"
    SNAPSHOT_PUBLISHED  = "snapshot_published"
    SNAPSHOT_VALIDATED  = "snapshot_validated"
    SNAPSHOT_SUPERSEDED = "snapshot_superseded"
    SNAPSHOT_ARCHIVED   = "snapshot_archived"
    SNAPSHOT_FAILED     = "snapshot_failed"
    SNAPSHOT_RETRIEVED  = "snapshot_retrieved"
    SNAPSHOT_EXPIRED    = "snapshot_expired"
    SNAPSHOT_BUNDLED    = "snapshot_bundled"
    SNAPSHOT_STORED     = "snapshot_stored"


# ---------------------------------------------------------------------------
# SnapshotValidationCode
# ---------------------------------------------------------------------------
class SnapshotValidationCode(str, Enum):
    """Validation check identifiers for snapshot integrity."""
    IDENTIFIER_CONSISTENT  = "identifier_consistent"
    VERSION_CONSISTENT     = "version_consistent"
    ASSESSMENT_CONSISTENT  = "assessment_consistent"
    POLICY_CONSISTENT      = "policy_consistent"
    METRIC_CONSISTENT      = "metric_consistent"
    SNAPSHOT_COMPLETE      = "snapshot_complete"
    METADATA_INTEGRITY     = "metadata_integrity"
    AUDIT_COMPLETE         = "audit_complete"
    HEALTH_CONSISTENT      = "health_consistent"


# ---------------------------------------------------------------------------
# Risk score to rating mapping thresholds
# ---------------------------------------------------------------------------
RISK_SCORE_EXCELLENT: float = 20.0
RISK_SCORE_GOOD:      float = 40.0
RISK_SCORE_FAIR:      float = 60.0
RISK_SCORE_POOR:      float = 80.0

RISK_SCORE_MINIMAL:   float = 20.0
RISK_SCORE_LOW:       float = 40.0
RISK_SCORE_MEDIUM:    float = 60.0
RISK_SCORE_HIGH:      float = 80.0

# Risk score to rating lookup (upper bound → RiskRating)
SCORE_TO_RATING: Tuple[tuple, ...] = (
    (RISK_SCORE_EXCELLENT, RiskRating.EXCELLENT),
    (RISK_SCORE_GOOD,      RiskRating.GOOD),
    (RISK_SCORE_FAIR,      RiskRating.FAIR),
    (RISK_SCORE_POOR,      RiskRating.POOR),
    (float("inf"),         RiskRating.CRITICAL),
)

# Risk score to level lookup (upper bound → RiskLevel)
SCORE_TO_LEVEL: Tuple[tuple, ...] = (
    (RISK_SCORE_MINIMAL, RiskLevel.MINIMAL),
    (RISK_SCORE_LOW,     RiskLevel.LOW),
    (RISK_SCORE_MEDIUM,  RiskLevel.MEDIUM),
    (RISK_SCORE_HIGH,    RiskLevel.HIGH),
    (float("inf"),       RiskLevel.CRITICAL),
)

# Priority mapping from RiskLevel
LEVEL_TO_PRIORITY: Dict[RiskLevel, RiskPriority] = {
    RiskLevel.CRITICAL: RiskPriority.CRITICAL,
    RiskLevel.HIGH:     RiskPriority.HIGH,
    RiskLevel.MEDIUM:   RiskPriority.MEDIUM,
    RiskLevel.LOW:      RiskPriority.LOW,
    RiskLevel.MINIMAL:  RiskPriority.LOW,
}

# Domains included in the assessment summary section
ASSESSMENT_DOMAINS: FrozenSet[str] = frozenset({
    "market_risk",
    "portfolio_risk",
    "position_risk",
    "credit_risk",
    "liquidity_risk",
    "operational_risk",
    "infrastructure_risk",
    "counterparty_risk",
    "concentration",
    "exposure",
})
