"""iios/execution/positions/integration/constants.py
==================================================
Constants, system IDs, and enumerations for the
IIOS Position Integration module.

C6 Execution Intelligence — Phase 3, Module 6
"""
from __future__ import annotations

from enum import unique

from iios.investment.workflow.engine_lifecycle import EngineState  # re-export StrEnum base

# ── Use stdlib StrEnum (Python 3.11+) or fall back to a compatible base ──────
try:
    from enum import StrEnum
except ImportError:  # Python < 3.11
    from enum import Enum

    class StrEnum(str, Enum):  # type: ignore[no-redef]
        pass


# ── Version ───────────────────────────────────────────────────────────────────
VERSION = "1.0.0"

# ── System IDs ────────────────────────────────────────────────────────────────
INTEGRATION_SYSTEM_ID = "position-integration-engine-v1"
MANAGER_SYSTEM_ID     = "position-integration-manager-v1"
COMPONENT_REGISTRY_ID = "position-component-registry-v1"
COMPONENT_FACTORY_ID  = "position-component-factory-v1"
VALIDATOR_SYSTEM_ID   = "position-integration-validator-v1"

# ── Actors ────────────────────────────────────────────────────────────────────
ACTOR_INTEGRATION = "position_integration"
ACTOR_MANAGER     = "position_integration_manager"
ACTOR_COMPONENT   = "position_integration_component"
ACTOR_SYSTEM      = "system"

# ── Component names (used as keys throughout the module) ──────────────────────
COMPONENT_ENGINE   = "position_engine"
COMPONENT_BOOK     = "position_book"
COMPONENT_RISK     = "position_risk"
COMPONENT_SNAPSHOT = "position_snapshot"

ALL_COMPONENT_NAMES = frozenset(
    [COMPONENT_ENGINE, COMPONENT_BOOK, COMPONENT_RISK, COMPONENT_SNAPSHOT]
)

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_MAX_POSITIONS     = 10_000
DEFAULT_MAX_HISTORY       = 5_000
DEFAULT_MAX_CACHE_ENTRIES = 10_000


# ── Enumerations ──────────────────────────────────────────────────────────────

@unique
class IntegrationEventType(StrEnum):
    SUBSYSTEM_INITIALIZED = "SUBSYSTEM_INITIALIZED"
    SUBSYSTEM_STARTED     = "SUBSYSTEM_STARTED"
    SUBSYSTEM_STOPPED     = "SUBSYSTEM_STOPPED"
    SNAPSHOT_PUBLISHED    = "SNAPSHOT_PUBLISHED"
    VALIDATION_COMPLETED  = "VALIDATION_COMPLETED"
    COMPONENT_REGISTERED  = "COMPONENT_REGISTERED"
    COMPONENT_FAILED      = "COMPONENT_FAILED"


@unique
class IntegrationOperationType(StrEnum):
    CREATE           = "CREATE"
    UPDATE           = "UPDATE"
    CLOSE            = "CLOSE"
    SYNC             = "SYNC"
    ARCHIVE          = "ARCHIVE"
    QUERY            = "QUERY"
    PUBLISH_SNAPSHOT = "PUBLISH_SNAPSHOT"
    VALIDATE         = "VALIDATE"
    HEALTH           = "HEALTH"
    SNAPSHOT         = "SNAPSHOT"


@unique
class HealthStatus(StrEnum):
    HEALTHY  = "HEALTHY"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"
    UNKNOWN  = "UNKNOWN"
