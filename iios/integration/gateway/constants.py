"""
constants.py — iios.integration.gateway
-----------------------------------------
All constants and enumerations for the Enterprise Integration Gateway.

C15 Enterprise Integration & Connectivity — Phase 1, Module 6
"""
from __future__ import annotations

from enum import Enum
from typing import List


# ════════════════════════════════════════════════════════════════════════
# Enumerations
# ════════════════════════════════════════════════════════════════════════


class GatewayState(Enum):
    """Operational lifecycle states of the gateway."""
    IDLE         = "idle"
    INITIALIZING = "initializing"
    ACTIVE       = "active"
    STOPPING     = "stopping"
    STOPPED      = "stopped"
    ERROR        = "error"
    MAINTENANCE  = "maintenance"


class GatewayEventType(Enum):
    """Events emitted by the gateway event bus."""
    GATEWAY_INITIALIZED  = "gateway_initialized"
    GATEWAY_STARTED      = "gateway_started"
    GATEWAY_VALIDATED    = "gateway_validated"
    GATEWAY_EXECUTED     = "gateway_executed"
    SNAPSHOT_PUBLISHED   = "snapshot_published"
    GATEWAY_COMPLETED    = "gateway_completed"
    GATEWAY_FAILED       = "gateway_failed"
    GATEWAY_STOPPED      = "gateway_stopped"


class GatewayOperationType(Enum):
    """Operations that can be submitted to the gateway."""
    SUBMIT     = "submit"
    QUERY      = "query"
    CONNECT    = "connect"
    DISCONNECT = "disconnect"
    VALIDATE   = "validate"
    HEALTH     = "health"
    STATUS     = "status"
    SNAPSHOT   = "snapshot"


class GatewayValidationCheck(Enum):
    """Validation checks run on gateway requests and state."""
    GATEWAY_CONSISTENCY   = "gateway_consistency"
    WORKFLOW_CONSISTENCY  = "workflow_consistency"
    COMPONENT_AVAILABILITY = "component_availability"
    LIFECYCLE_INTEGRITY   = "lifecycle_integrity"
    GOVERNANCE_INTEGRITY  = "governance_integrity"
    SNAPSHOT_INTEGRITY    = "snapshot_integrity"
    RESPONSE_COMPLETENESS = "response_completeness"


class GatewayComponentType(Enum):
    """The five integrated subsystem components."""
    LIFECYCLE  = "lifecycle"
    ENGINE     = "engine"
    POLICIES   = "policies"
    SERVICES   = "services"
    SNAPSHOT   = "snapshot"


class GatewayResponseStatus(Enum):
    """Final status of a gateway response."""
    SUCCESS  = "success"
    FAILED   = "failed"
    PARTIAL  = "partial"
    REJECTED = "rejected"
    PENDING  = "pending"


class GatewayWorkflowStep(Enum):
    """Ordered steps in the gateway execution workflow."""
    REQUEST_RECEIVED       = "request_received"
    REQUEST_VALIDATED      = "request_validated"
    LIFECYCLE_INITIALIZED  = "lifecycle_initialized"
    ENGINE_EXECUTED        = "engine_executed"
    GOVERNANCE_EVALUATED   = "governance_evaluated"
    SERVICES_EXECUTED      = "services_executed"
    SNAPSHOT_GENERATED     = "snapshot_generated"
    SNAPSHOT_VALIDATED     = "snapshot_validated"
    RESPONSE_BUILT         = "response_built"
    COMPLETED              = "completed"


# ════════════════════════════════════════════════════════════════════════
# String constants
# ════════════════════════════════════════════════════════════════════════

GATEWAY_VERSION   = "1.0.0"
FRAMEWORK_VERSION = "1.0.0"
BUILD_VERSION     = "1.0.0"

GATEWAY_SYSTEM_ID = "integration-gateway"
MANAGER_SYSTEM_ID = "gateway-manager"
DEFAULT_GATEWAY_ID = "default-gateway"

ACTOR_GATEWAY  = "gateway"
ACTOR_MANAGER  = "gateway-manager"
ACTOR_SYSTEM   = "system"

# ID prefixes
GATEWAY_ID_PREFIX  = "gw-"
REQUEST_ID_PREFIX  = "gwreq-"
RESPONSE_ID_PREFIX = "gwresp-"
CONTEXT_ID_PREFIX  = "gwctx-"
EVENT_ID_PREFIX    = "gwe-"
ENTRY_ID_PREFIX    = "gwhist-"
COMPONENT_ID_PREFIX = "gwcomp-"

# ════════════════════════════════════════════════════════════════════════
# Numeric defaults
# ════════════════════════════════════════════════════════════════════════

DEFAULT_MAX_HISTORY         = 1_000
DEFAULT_MAX_REGISTRY_SIZE   = 10_000
DEFAULT_MAX_ACTIVE_REQUESTS = 100
DEFAULT_REQUEST_TIMEOUT_MS  = 30_000
DEFAULT_MAX_GATEWAYS        = 50
DEFAULT_CACHE_TTL_SECONDS   = 300.0

# ════════════════════════════════════════════════════════════════════════
# Ordered validation check list
# ════════════════════════════════════════════════════════════════════════

VALIDATION_CHECK_ORDER: List[GatewayValidationCheck] = [
    GatewayValidationCheck.GATEWAY_CONSISTENCY,
    GatewayValidationCheck.WORKFLOW_CONSISTENCY,
    GatewayValidationCheck.COMPONENT_AVAILABILITY,
    GatewayValidationCheck.LIFECYCLE_INTEGRITY,
    GatewayValidationCheck.GOVERNANCE_INTEGRITY,
    GatewayValidationCheck.SNAPSHOT_INTEGRITY,
    GatewayValidationCheck.RESPONSE_COMPLETENESS,
]

# Components required by each operation type
OPERATION_REQUIRED_COMPONENTS = {
    GatewayOperationType.SUBMIT: [
        GatewayComponentType.LIFECYCLE,
        GatewayComponentType.ENGINE,
        GatewayComponentType.POLICIES,
        GatewayComponentType.SERVICES,
        GatewayComponentType.SNAPSHOT,
    ],
    GatewayOperationType.CONNECT: [
        GatewayComponentType.LIFECYCLE,
        GatewayComponentType.ENGINE,
        GatewayComponentType.SERVICES,
    ],
    GatewayOperationType.DISCONNECT: [
        GatewayComponentType.LIFECYCLE,
        GatewayComponentType.SERVICES,
    ],
    GatewayOperationType.VALIDATE: [],
    GatewayOperationType.QUERY: [],
    GatewayOperationType.HEALTH: [],
    GatewayOperationType.STATUS: [],
    GatewayOperationType.SNAPSHOT: [
        GatewayComponentType.SNAPSHOT,
    ],
}
