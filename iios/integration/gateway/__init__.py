"""
__init__.py — iios.integration.gateway
-----------------------------------------
Public API for the Enterprise Integration Gateway.

C15 Enterprise Integration & Connectivity — Phase 1, Module 6

The Enterprise Integration Gateway is the ONLY public entry point for
the Enterprise Integration & Connectivity subsystem.  External components
MUST NOT directly access Lifecycle, Engine, Policies, Services, or
Snapshot — all communication occurs through this package.
"""
from __future__ import annotations

# ── constants & enumerations ─────────────────────────────────────────────────
from .constants import (
    ACTOR_GATEWAY,
    ACTOR_MANAGER,
    ACTOR_SYSTEM,
    BUILD_VERSION,
    COMPONENT_ID_PREFIX,
    CONTEXT_ID_PREFIX,
    DEFAULT_CACHE_TTL_SECONDS,
    DEFAULT_GATEWAY_ID,
    DEFAULT_MAX_ACTIVE_REQUESTS,
    DEFAULT_MAX_GATEWAYS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_REGISTRY_SIZE,
    DEFAULT_REQUEST_TIMEOUT_MS,
    ENTRY_ID_PREFIX,
    EVENT_ID_PREFIX,
    FRAMEWORK_VERSION,
    GATEWAY_ID_PREFIX,
    GATEWAY_SYSTEM_ID,
    GATEWAY_VERSION,
    MANAGER_SYSTEM_ID,
    OPERATION_REQUIRED_COMPONENTS,
    REQUEST_ID_PREFIX,
    RESPONSE_ID_PREFIX,
    VALIDATION_CHECK_ORDER,
    GatewayComponentType,
    GatewayEventType,
    GatewayOperationType,
    GatewayResponseStatus,
    GatewayState,
    GatewayValidationCheck,
    GatewayWorkflowStep,
)

# ── exceptions ────────────────────────────────────────────────────────────────
from .exceptions import (
    GatewayCapacityError,
    GatewayComponentError,
    GatewayEngineError,
    GatewayGovernanceError,
    GatewayLifecycleError,
    GatewayNotReadyError,
    GatewayRequestValidationError,
    GatewayServicesError,
    GatewaySnapshotError,
    GatewayWorkflowError,
    IntegrationGatewayError,
)

# ── request / response / context ─────────────────────────────────────────────
from .integration_gateway_request  import IntegrationGatewayRequest
from .integration_gateway_response import IntegrationGatewayResponse
from .integration_gateway_context  import IntegrationGatewayContext

# ── events ────────────────────────────────────────────────────────────────────
from .integration_gateway_events import (
    GatewayEvent,
    IntegrationGatewayEventBus,
)

# ── validation ────────────────────────────────────────────────────────────────
from .integration_gateway_validation import (
    GatewayValidationIssue,
    GatewayValidationReport,
    IntegrationGatewayValidation,
)

# ── health ────────────────────────────────────────────────────────────────────
from .integration_gateway_health import (
    GatewayComponentHealth,
    IntegrationGatewayHealth,
    IntegrationHealthSummary,
)

# ── status ────────────────────────────────────────────────────────────────────
from .integration_gateway_status import (
    IntegrationGatewayStatusReport,
    IntegrationGatewayStatusTracker,
)

# ── statistics ────────────────────────────────────────────────────────────────
from .integration_gateway_statistics import (
    IntegrationGatewayStatistics,
    IntegrationStatistics,
)

# ── history ───────────────────────────────────────────────────────────────────
from .integration_gateway_history import (
    GatewayHistoryEntry,
    GatewayHistoryReport,
    IntegrationGatewayHistory,
)

# ── registry ──────────────────────────────────────────────────────────────────
from .integration_gateway_registry import IntegrationGatewayRegistry

# ── router ────────────────────────────────────────────────────────────────────
from .integration_gateway_router import (
    GatewayRouteDecision,
    IntegrationGatewayRouter,
)

# ── dispatcher ────────────────────────────────────────────────────────────────
from .integration_gateway_dispatcher import IntegrationGatewayDispatcher

# ── component registry & factory ─────────────────────────────────────────────
from .integration_component_registry import (
    GatewayComponent,
    IntegrationComponentRegistry,
)
from .integration_component_factory import IntegrationComponentFactory

# ── gateway factory ───────────────────────────────────────────────────────────
from .integration_gateway_factory import IntegrationGatewayFactory

# ── gateway & manager (top-level) ─────────────────────────────────────────────
from .integration_gateway         import IntegrationGateway
from .integration_gateway_manager import IntegrationGatewayManager


__all__: list[str] = [
    # ── enumerations ─────────────────────────────────────────────────
    "GatewayState",
    "GatewayEventType",
    "GatewayOperationType",
    "GatewayValidationCheck",
    "GatewayComponentType",
    "GatewayResponseStatus",
    "GatewayWorkflowStep",
    # ── string constants ─────────────────────────────────────────────
    "GATEWAY_VERSION",
    "FRAMEWORK_VERSION",
    "BUILD_VERSION",
    "GATEWAY_SYSTEM_ID",
    "MANAGER_SYSTEM_ID",
    "DEFAULT_GATEWAY_ID",
    "ACTOR_GATEWAY",
    "ACTOR_MANAGER",
    "ACTOR_SYSTEM",
    "GATEWAY_ID_PREFIX",
    "REQUEST_ID_PREFIX",
    "RESPONSE_ID_PREFIX",
    "CONTEXT_ID_PREFIX",
    "EVENT_ID_PREFIX",
    "ENTRY_ID_PREFIX",
    "COMPONENT_ID_PREFIX",
    # ── numeric constants ────────────────────────────────────────────
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_REGISTRY_SIZE",
    "DEFAULT_MAX_ACTIVE_REQUESTS",
    "DEFAULT_REQUEST_TIMEOUT_MS",
    "DEFAULT_MAX_GATEWAYS",
    "DEFAULT_CACHE_TTL_SECONDS",
    # ── composite constants ──────────────────────────────────────────
    "VALIDATION_CHECK_ORDER",
    "OPERATION_REQUIRED_COMPONENTS",
    # ── exceptions ───────────────────────────────────────────────────
    "IntegrationGatewayError",
    "GatewayNotReadyError",
    "GatewayRequestValidationError",
    "GatewayWorkflowError",
    "GatewayComponentError",
    "GatewayLifecycleError",
    "GatewayEngineError",
    "GatewayGovernanceError",
    "GatewayServicesError",
    "GatewaySnapshotError",
    "GatewayCapacityError",
    # ── request / response / context ─────────────────────────────────
    "IntegrationGatewayRequest",
    "IntegrationGatewayResponse",
    "IntegrationGatewayContext",
    # ── events ───────────────────────────────────────────────────────
    "GatewayEvent",
    "IntegrationGatewayEventBus",
    # ── validation ───────────────────────────────────────────────────
    "GatewayValidationIssue",
    "GatewayValidationReport",
    "IntegrationGatewayValidation",
    # ── health ───────────────────────────────────────────────────────
    "GatewayComponentHealth",
    "IntegrationGatewayHealth",
    "IntegrationHealthSummary",
    # ── status ───────────────────────────────────────────────────────
    "IntegrationGatewayStatusReport",
    "IntegrationGatewayStatusTracker",
    # ── statistics ───────────────────────────────────────────────────
    "IntegrationGatewayStatistics",
    "IntegrationStatistics",
    # ── history ──────────────────────────────────────────────────────
    "GatewayHistoryEntry",
    "GatewayHistoryReport",
    "IntegrationGatewayHistory",
    # ── registry ─────────────────────────────────────────────────────
    "IntegrationGatewayRegistry",
    # ── router ───────────────────────────────────────────────────────
    "GatewayRouteDecision",
    "IntegrationGatewayRouter",
    # ── dispatcher ───────────────────────────────────────────────────
    "IntegrationGatewayDispatcher",
    # ── component registry & factory ─────────────────────────────────
    "GatewayComponent",
    "IntegrationComponentRegistry",
    "IntegrationComponentFactory",
    # ── gateway factory ──────────────────────────────────────────────
    "IntegrationGatewayFactory",
    # ── gateway & manager ────────────────────────────────────────────
    "IntegrationGateway",
    "IntegrationGatewayManager",
]
