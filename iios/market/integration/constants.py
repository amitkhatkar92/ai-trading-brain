"""
constants.py — iios.market.integration
========================================
Enumerations, system identifiers, actor constants, and numeric defaults
for the Market Integration subsystem.

C12 Market Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

from enum import Enum
from typing import FrozenSet

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
INTEGRATION_SYSTEM_ID: str = "iios:market:integration"
ENGINE_SYSTEM_ID:      str = "iios:market:integration:engine"
MANAGER_SYSTEM_ID:     str = "iios:market:integration:manager"
REGISTRY_SYSTEM_ID:    str = "iios:market:integration:registry"
VALIDATION_SYSTEM_ID:  str = "iios:market:integration:validation"
HEALTH_SYSTEM_ID:      str = "iios:market:integration:health"
COMPONENT_SYSTEM_ID:   str = "iios:market:integration:components"

# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------
VERSION:        str = "1.0.0"
SCHEMA_VERSION: str = "1.0"
MODEL_VERSION:  str = "1.0.0"

# ---------------------------------------------------------------------------
# Actor constants
# ---------------------------------------------------------------------------
ACTOR_INTEGRATION: str = "iios:market:integration"
ACTOR_ENGINE:      str = "iios:market:integration:engine"
ACTOR_MANAGER:     str = "iios:market:integration:manager"
ACTOR_SYSTEM:      str = "iios:system"
ACTOR_OPERATOR:    str = "operator"

# ---------------------------------------------------------------------------
# Component names (keys used in MarketComponentRegistry)
# ---------------------------------------------------------------------------
COMPONENT_LIFECYCLE:       str = "market_lifecycle"
COMPONENT_ENGINE:          str = "market_engine"
COMPONENT_POLICY_ENGINE:   str = "market_policy_engine"
COMPONENT_ANALYTICS_ENGINE: str = "market_analytics_engine"
COMPONENT_SNAPSHOT_REGISTRY: str = "market_snapshot_registry"
COMPONENT_SNAPSHOT_STORE:  str = "market_snapshot_store"
COMPONENT_SNAPSHOT_CACHE:  str = "market_snapshot_cache"
COMPONENT_SNAPSHOT_HISTORY: str = "market_snapshot_history"

# ---------------------------------------------------------------------------
# Numeric defaults
# ---------------------------------------------------------------------------
DEFAULT_MAX_REGISTRY:   int   = 10_000
DEFAULT_MAX_HISTORY:    int   = 1_000
DEFAULT_CACHE_TTL_S:    float = 300.0
DEFAULT_MAX_CACHE:      int   = 500
DEFAULT_QUERY_LIMIT:    int   = 100

# ---------------------------------------------------------------------------
# IntegrationRequestType
# ---------------------------------------------------------------------------
class IntegrationRequestType(str, Enum):
    """Supported market integration request types."""
    MARKET_OVERVIEW          = "market_overview"
    MARKET_REGIME_ANALYSIS   = "market_regime_analysis"
    SECTOR_ANALYSIS          = "sector_analysis"
    BREADTH_ANALYSIS         = "breadth_analysis"
    VOLATILITY_ANALYSIS      = "volatility_analysis"
    LIQUIDITY_ANALYSIS       = "liquidity_analysis"
    CORRELATION_ANALYSIS     = "correlation_analysis"
    FORECAST_REQUEST         = "forecast_request"
    MARKET_SNAPSHOT_REQUEST  = "market_snapshot_request"
    MARKET_HISTORY_REQUEST   = "market_history_request"


# ---------------------------------------------------------------------------
# IntegrationStatus
# ---------------------------------------------------------------------------
class IntegrationStatus(str, Enum):
    """Integration request processing status."""
    PENDING    = "pending"
    PROCESSING = "processing"
    COMPLETED  = "completed"
    FAILED     = "failed"
    REJECTED   = "rejected"


# ---------------------------------------------------------------------------
# IntegrationEventType
# ---------------------------------------------------------------------------
class IntegrationEventType(str, Enum):
    """Integration domain event types."""
    MARKET_INTEGRATION_STARTED  = "market_integration_started"
    MARKET_REQUEST_RECEIVED     = "market_request_received"
    MARKET_VALIDATED            = "market_validated"
    MARKET_SNAPSHOT_PUBLISHED   = "market_snapshot_published"
    MARKET_COMPLETED            = "market_completed"
    MARKET_FAILED               = "market_failed"
    MARKET_INTEGRATION_STOPPED  = "market_integration_stopped"


# ---------------------------------------------------------------------------
# IntegrationValidationCode
# ---------------------------------------------------------------------------
class IntegrationValidationCode(str, Enum):
    """Codes for integration-level validation checks."""
    API_CONSISTENCY         = "api_consistency"
    LIFECYCLE_CONSISTENCY   = "lifecycle_consistency"
    SUBSYSTEM_AVAILABILITY  = "subsystem_availability"
    SNAPSHOT_INTEGRITY      = "snapshot_integrity"
    INPUT_VALIDATION        = "input_validation"
    RESPONSE_VALIDATION     = "response_validation"


# ---------------------------------------------------------------------------
# ComponentStatus
# ---------------------------------------------------------------------------
class ComponentStatus(str, Enum):
    """Status of a registered subsystem component."""
    AVAILABLE   = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED    = "degraded"
    UNKNOWN     = "unknown"


# ---------------------------------------------------------------------------
# IntegrationPriority
# ---------------------------------------------------------------------------
class IntegrationPriority(str, Enum):
    """Processing priority for integration requests."""
    CRITICAL = "critical"
    HIGH     = "high"
    NORMAL   = "normal"
    LOW      = "low"
    BATCH    = "batch"


# ---------------------------------------------------------------------------
# Sets
# ---------------------------------------------------------------------------
TERMINAL_STATUSES: FrozenSet[IntegrationStatus] = frozenset({
    IntegrationStatus.COMPLETED,
    IntegrationStatus.FAILED,
    IntegrationStatus.REJECTED,
})

SUCCESSFUL_STATUSES: FrozenSet[IntegrationStatus] = frozenset({
    IntegrationStatus.COMPLETED,
})
