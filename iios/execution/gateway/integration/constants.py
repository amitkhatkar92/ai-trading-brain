"""iios/execution/gateway/integration/constants.py
==================================================
Constants, enumerations, and defaults for the
Execution Gateway Integration Layer.

C6 Execution Intelligence — Phase 5, Module 6
"""
from __future__ import annotations

from enum import Enum

# ── System IDs ────────────────────────────────────────────────────────────────

INTEGRATION_SYSTEM_ID           = "iios:execution:gateway:integration"
INTEGRATION_MANAGER_SYSTEM_ID   = "iios:execution:gateway:integration:manager"
INTEGRATION_REGISTRY_SYSTEM_ID  = "iios:execution:gateway:integration:registry"
INTEGRATION_COMPONENT_REGISTRY_SYSTEM_ID = (
    "iios:execution:gateway:integration:component-registry"
)

VERSION        = "1.0.0"
SCHEMA_VERSION = "1.0"

# ── Actors ────────────────────────────────────────────────────────────────────

ACTOR_INTEGRATION_ENGINE  = "integration:engine"
ACTOR_INTEGRATION_MANAGER = "integration:manager"
ACTOR_INTEGRATION_SYSTEM  = "integration:system"

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_MAX_REQUESTS = 5_000
DEFAULT_MAX_HISTORY  = 2_000

# ── Enumerations ──────────────────────────────────────────────────────────────


class IntegrationRequestStatus(str, Enum):
    """Lifecycle status of a GatewayIntegrationRequest."""
    PENDING     = "PENDING"
    VALIDATING  = "VALIDATING"
    ROUTING     = "ROUTING"
    DISPATCHING = "DISPATCHING"
    COMPLETED   = "COMPLETED"
    FAILED      = "FAILED"
    CANCELLED   = "CANCELLED"


class IntegrationOutcome(str, Enum):
    """High-level outcome of a completed integration request."""
    SUCCESS          = "SUCCESS"
    ROUTING_FAILED   = "ROUTING_FAILED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    COMPONENT_ERROR  = "COMPONENT_ERROR"
    ENGINE_ERROR     = "ENGINE_ERROR"
    UNKNOWN          = "UNKNOWN"


class IntegrationEventType(str, Enum):
    """Domain event types emitted by the integration layer."""
    SUBSYSTEM_INITIALIZED     = "SUBSYSTEM_INITIALIZED"
    SUBSYSTEM_STARTED         = "SUBSYSTEM_STARTED"
    SUBSYSTEM_STOPPED         = "SUBSYSTEM_STOPPED"
    GATEWAY_REQUEST_RECEIVED  = "GATEWAY_REQUEST_RECEIVED"
    GATEWAY_REQUEST_VALIDATED = "GATEWAY_REQUEST_VALIDATED"
    GATEWAY_REQUEST_ROUTED    = "GATEWAY_REQUEST_ROUTED"
    GATEWAY_REQUEST_COMPLETED = "GATEWAY_REQUEST_COMPLETED"
    GATEWAY_REQUEST_FAILED    = "GATEWAY_REQUEST_FAILED"
    SNAPSHOT_PUBLISHED        = "SNAPSHOT_PUBLISHED"
    VALIDATION_COMPLETED      = "VALIDATION_COMPLETED"
    HEALTH_UPDATED            = "HEALTH_UPDATED"


class ComponentType(str, Enum):
    """The five integrated gateway components."""
    LIFECYCLE      = "LIFECYCLE"
    ENGINE         = "ENGINE"
    BROKER_LAYER   = "BROKER_LAYER"
    ROUTING_ENGINE = "ROUTING_ENGINE"
    SNAPSHOT_STORE = "SNAPSHOT_STORE"


class ComponentHealth(str, Enum):
    """Health state of a single gateway component."""
    HEALTHY  = "HEALTHY"
    DEGRADED = "DEGRADED"
    OFFLINE  = "OFFLINE"
    UNKNOWN  = "UNKNOWN"


# ── Frozensets ────────────────────────────────────────────────────────────────

TERMINAL_REQUEST_STATUSES: frozenset = frozenset({
    IntegrationRequestStatus.COMPLETED,
    IntegrationRequestStatus.FAILED,
    IntegrationRequestStatus.CANCELLED,
})

ACTIVE_REQUEST_STATUSES: frozenset = frozenset(
    s for s in IntegrationRequestStatus if s not in TERMINAL_REQUEST_STATUSES
)

HEALTHY_COMPONENT_HEALTHS: frozenset = frozenset({
    ComponentHealth.HEALTHY,
})
