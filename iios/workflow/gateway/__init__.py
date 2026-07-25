"""
iios.workflow.gateway — C16 M6: Enterprise Workflow Gateway

THE ONLY public entry point for Enterprise Workflow & Process Orchestration.

External IIOS modules MUST NOT directly access M1-M5 internals.
All communication MUST occur through WorkflowGateway.

Public API:
    gateway = WorkflowGateway()
    gateway.initialize()
    gateway.start()

    response = gateway.submit(request)
    response = gateway.query(workflow_id)
    response = gateway.cancel(workflow_id)
    response = gateway.retry(workflow_id)
    result   = gateway.validate(request)
    health   = gateway.health()
    status   = gateway.status()
    stats    = gateway.statistics()
    snap     = gateway.snapshot(workflow_id)
    records  = gateway.history()

    gateway.stop()
    gateway.restart()
"""
from .constants import (
    ACTOR_COMPONENT,
    ACTOR_DISPATCHER,
    ACTOR_GATEWAY,
    ACTOR_MANAGER,
    ACTOR_ROUTER,
    BUILD_VERSION,
    DEFAULT_ENTERPRISE_ID,
    DEFAULT_ENVIRONMENT,
    DEFAULT_GATEWAY_ID,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_REGISTRY,
    DEFAULT_PRIORITY,
    DEFAULT_TIMEOUT_MS,
    FRAMEWORK_VERSION,
    GATEWAY_VERSION,
    PREFIX_CONTEXT,
    PREFIX_EVENT,
    PREFIX_GATEWAY,
    PREFIX_RECORD,
    PREFIX_REQUEST,
    PREFIX_RESPONSE,
    VERSION,
    ComponentStatus,
    ComponentType,
    GatewayEventType,
    GatewayHealthStatus,
    GatewayRequestType,
    GatewayResponseStatus,
    GatewayState,
)
from .exceptions import (
    WorkflowGatewayComponentError,
    WorkflowGatewayDispatchError,
    WorkflowGatewayError,
    WorkflowGatewayHistoryError,
    WorkflowGatewayNotInitializedError,
    WorkflowGatewayNotRunningError,
    WorkflowGatewayRequestError,
    WorkflowGatewayResponseError,
    WorkflowGatewayRoutingError,
    WorkflowGatewayStatisticsError,
    WorkflowGatewayTimeoutError,
    WorkflowGatewayValidationError,
)
from .workflow_gateway_context import WorkflowGatewayContext
from .workflow_gateway_dispatcher import WorkflowGatewayDispatcher
from .workflow_gateway_events import WorkflowGatewayEvent, WorkflowGatewayEventBus
from .workflow_gateway_factory import WorkflowGatewayFactory
from .workflow_gateway_health import WorkflowGatewayHealth, WorkflowHealthSummary
from .workflow_gateway_history import WorkflowGatewayHistory, WorkflowGatewayHistoryRecord
from .workflow_gateway_manager import WorkflowGatewayManager
from .workflow_gateway_registry import WorkflowGatewayRegistry
from .workflow_gateway_request import WorkflowGatewayRequest
from .workflow_gateway_response import WorkflowGatewayResponse
from .workflow_gateway_router import WorkflowGatewayRouter
from .workflow_gateway_statistics import WorkflowGatewayStatistics, WorkflowStatistics
from .workflow_gateway_status import WorkflowGatewayStatus, WorkflowStatus
from .workflow_gateway_validation import GatewayValidationResult, WorkflowGatewayValidation
from .workflow_component_factory import WorkflowComponentFactory
from .workflow_component_registry import ComponentRecord, WorkflowComponentRegistry
from .workflow_gateway import WorkflowGateway

__all__ = [
    # ── Main public class ──────────────────────────────────────────────────────
    "WorkflowGateway",
    # ── Constants & enums ──────────────────────────────────────────────────────
    "VERSION",
    "BUILD_VERSION",
    "GATEWAY_VERSION",
    "FRAMEWORK_VERSION",
    "DEFAULT_GATEWAY_ID",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_REGISTRY",
    "DEFAULT_TIMEOUT_MS",
    "DEFAULT_PRIORITY",
    "DEFAULT_ENTERPRISE_ID",
    "DEFAULT_ENVIRONMENT",
    "PREFIX_GATEWAY",
    "PREFIX_REQUEST",
    "PREFIX_RESPONSE",
    "PREFIX_EVENT",
    "PREFIX_CONTEXT",
    "PREFIX_RECORD",
    "ACTOR_GATEWAY",
    "ACTOR_ROUTER",
    "ACTOR_DISPATCHER",
    "ACTOR_MANAGER",
    "ACTOR_COMPONENT",
    "GatewayState",
    "GatewayEventType",
    "GatewayRequestType",
    "GatewayResponseStatus",
    "GatewayHealthStatus",
    "ComponentType",
    "ComponentStatus",
    # ── Exceptions ─────────────────────────────────────────────────────────────
    "WorkflowGatewayError",
    "WorkflowGatewayNotInitializedError",
    "WorkflowGatewayNotRunningError",
    "WorkflowGatewayValidationError",
    "WorkflowGatewayRequestError",
    "WorkflowGatewayResponseError",
    "WorkflowGatewayRoutingError",
    "WorkflowGatewayDispatchError",
    "WorkflowGatewayComponentError",
    "WorkflowGatewayHistoryError",
    "WorkflowGatewayStatisticsError",
    "WorkflowGatewayTimeoutError",
    # ── Domain objects ──────────────────────────────────────────────────────────
    "WorkflowGatewayRequest",
    "WorkflowGatewayResponse",
    "WorkflowGatewayContext",
    "WorkflowGatewayEvent",
    "WorkflowGatewayHistoryRecord",
    "WorkflowStatistics",
    "WorkflowStatus",
    "WorkflowHealthSummary",
    "GatewayValidationResult",
    "ComponentRecord",
    # ── Services ───────────────────────────────────────────────────────────────
    "WorkflowGatewayValidation",
    "WorkflowGatewayRouter",
    "WorkflowGatewayDispatcher",
    "WorkflowGatewayRegistry",
    "WorkflowGatewayHistory",
    "WorkflowGatewayStatistics",
    "WorkflowGatewayEventBus",
    "WorkflowGatewayHealth",
    "WorkflowGatewayStatus",
    "WorkflowGatewayManager",
    "WorkflowComponentRegistry",
    "WorkflowComponentFactory",
    "WorkflowGatewayFactory",
]
