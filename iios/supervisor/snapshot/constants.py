"""
constants.py — iios.supervisor.snapshot
-----------------------------------------
Shared enumerations, constants, and lookup tables for the
AI Supervisor Snapshot.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 5
"""
from __future__ import annotations

from enum import Enum, IntEnum
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------

SUPERVISOR_SNAPSHOT_SYSTEM_ID: str = "iios:supervisor:snapshot"
BUILDER_SYSTEM_ID:             str = "iios:supervisor:snapshot:builder"
VALIDATOR_SYSTEM_ID:           str = "iios:supervisor:snapshot:validator"
FACTORY_SYSTEM_ID:             str = "iios:supervisor:snapshot:factory"
REGISTRY_SYSTEM_ID:            str = "iios:supervisor:snapshot:registry"
STORE_SYSTEM_ID:               str = "iios:supervisor:snapshot:store"
CACHE_SYSTEM_ID:               str = "iios:supervisor:snapshot:cache"
BUNDLE_SYSTEM_ID:              str = "iios:supervisor:snapshot:bundle"

# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

VERSION:          str = "1.0.0"
SCHEMA_VERSION:   str = "1.0"
PLATFORM_VERSION: str = "1.0.0"

# ---------------------------------------------------------------------------
# Actors
# ---------------------------------------------------------------------------

ACTOR_SNAPSHOT_BUILDER:   str = "supervisor_snapshot_builder"
ACTOR_SNAPSHOT_VALIDATOR: str = "supervisor_snapshot_validator"
ACTOR_SNAPSHOT_FACTORY:   str = "supervisor_snapshot_factory"
ACTOR_SYSTEM:             str = "system"
ACTOR_OPERATOR:           str = "operator"

# ---------------------------------------------------------------------------
# Capacity defaults
# ---------------------------------------------------------------------------

DEFAULT_MAX_SNAPSHOTS:   int   = 10_000
DEFAULT_MAX_HISTORY:     int   = 1_000
DEFAULT_CACHE_TTL_S:     float = 300.0   # 5 minutes
DEFAULT_CACHE_MAX_SIZE:  int   = 256
DEFAULT_BUILD_TIMEOUT_S: float = 30.0

# ---------------------------------------------------------------------------
# Health score thresholds
# ---------------------------------------------------------------------------

HEALTH_OPTIMAL_THRESHOLD:  float = 0.90
HEALTH_NORMAL_THRESHOLD:   float = 0.70
HEALTH_DEGRADED_THRESHOLD: float = 0.50
HEALTH_CRITICAL_THRESHOLD: float = 0.30

# ---------------------------------------------------------------------------
# Platform dependency graph (mirrors M4 governance.PLATFORM_DEPENDENCIES)
# ---------------------------------------------------------------------------

PLATFORM_DEPENDENCIES: Dict[str, List[str]] = {
    "execution_intelligence":  ["risk_intelligence", "market_intelligence", "decision_intelligence"],
    "execution_recovery":      ["execution_intelligence", "risk_intelligence"],
    "execution_analytics":     ["execution_intelligence"],
    "decision_intelligence":   ["risk_intelligence", "market_intelligence", "portfolio_intelligence"],
    "portfolio_intelligence":  ["risk_intelligence"],
    "risk_intelligence":       ["market_intelligence"],
    "market_intelligence":     [],
    "platform_infrastructure": [],
    "enterprise_modules":      [
        "execution_intelligence", "risk_intelligence",
        "market_intelligence", "decision_intelligence",
    ],
}

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class SnapshotStatus(str, Enum):
    """Life-cycle status of a supervisor snapshot."""
    PENDING   = "pending"
    BUILDING  = "building"
    VALID     = "valid"
    INVALID   = "invalid"
    PUBLISHED = "published"
    ARCHIVED  = "archived"
    STALE     = "stale"


class SupervisorScope(str, Enum):
    """Scope of the supervisor session."""
    PLATFORM   = "platform"
    ENTERPRISE = "enterprise"
    SUBSYSTEM  = "subsystem"
    DOMAIN     = "domain"
    GLOBAL     = "global"


class SupervisorType(str, Enum):
    """Type of supervisor session."""
    STANDARD   = "standard"
    ENHANCED   = "enhanced"
    EMERGENCY  = "emergency"
    COMPLIANCE = "compliance"
    AUDIT      = "audit"


class SnapshotLifecycleState(str, Enum):
    """Lifecycle state reported in the snapshot."""
    CREATED  = "created"
    STARTING = "starting"
    RUNNING  = "running"
    STOPPING = "stopping"
    STOPPED  = "stopped"
    FAILED   = "failed"
    UNKNOWN  = "unknown"


class SnapshotGovernanceState(str, Enum):
    """Governance state reported in the snapshot."""
    ACTIVE    = "active"
    SUSPENDED = "suspended"
    EMERGENCY = "emergency"
    HALTED    = "halted"
    DEGRADED  = "degraded"
    UNKNOWN   = "unknown"


class SnapshotEnterpriseState(str, Enum):
    """Enterprise operational state reported in the snapshot."""
    OPTIMAL   = "optimal"
    NORMAL    = "normal"
    DEGRADED  = "degraded"
    CRITICAL  = "critical"
    EMERGENCY = "emergency"
    UNKNOWN   = "unknown"


class OperationalStatus(str, Enum):
    """Operational status of the supervisor or platform."""
    OPERATIONAL = "operational"
    DEGRADED    = "degraded"
    IMPAIRED    = "impaired"
    UNAVAILABLE = "unavailable"
    UNKNOWN     = "unknown"


class GovernanceStatus(str, Enum):
    """Governance compliance status."""
    COMPLIANT     = "compliant"
    NON_COMPLIANT = "non_compliant"
    ESCALATED     = "escalated"
    SUSPENDED     = "suspended"
    UNKNOWN       = "unknown"


class PlatformStatus(str, Enum):
    """Overall platform health status."""
    HEALTHY  = "healthy"
    DEGRADED = "degraded"
    IMPAIRED = "impaired"
    CRITICAL = "critical"
    UNKNOWN  = "unknown"


class SubsystemSummaryStatus(str, Enum):
    """Status of an individual subsystem within the snapshot."""
    HEALTHY     = "healthy"
    DEGRADED    = "degraded"
    IMPAIRED    = "impaired"
    CRITICAL    = "critical"
    UNAVAILABLE = "unavailable"
    UNKNOWN     = "unknown"


class AutomationReadiness(str, Enum):
    """Self-healing automation readiness level."""
    READY             = "ready"
    PARTIAL           = "partial"
    REQUIRES_APPROVAL = "requires_approval"
    NOT_READY         = "not_ready"
    UNKNOWN           = "unknown"


class SnapshotEventType(str, Enum):
    """Event types emitted by the Supervisor Snapshot subsystem."""
    SNAPSHOT_STARTED     = "snapshot_started"
    SNAPSHOT_BUILT       = "snapshot_built"
    SNAPSHOT_VALIDATED   = "snapshot_validated"
    SNAPSHOT_PUBLISHED   = "snapshot_published"
    SNAPSHOT_REGISTERED  = "snapshot_registered"
    SNAPSHOT_RETRIEVED   = "snapshot_retrieved"
    SNAPSHOT_INVALIDATED = "snapshot_invalidated"
    SNAPSHOT_CACHED      = "snapshot_cached"
    SNAPSHOT_EXPIRED     = "snapshot_expired"
    SNAPSHOT_ARCHIVED    = "snapshot_archived"
    BUNDLE_CREATED       = "bundle_created"
    STORE_SAVED          = "store_saved"


class SnapshotValidationCode(str, Enum):
    """Validation check identifiers."""
    IDENTIFIER_CONSISTENCY    = "identifier_consistency"
    VERSION_CONSISTENCY       = "version_consistency"
    GOVERNANCE_CONSISTENCY    = "governance_consistency"
    ENTERPRISE_CONSISTENCY    = "enterprise_consistency"
    RECOMMENDATION_CONSISTENCY = "recommendation_consistency"
    SNAPSHOT_COMPLETENESS     = "snapshot_completeness"
    METADATA_INTEGRITY        = "metadata_integrity"
