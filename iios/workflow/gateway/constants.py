"""
constants.py — iios.workflow.gateway
-------------------------------------
All enums, prefixes, and defaults for the Enterprise Workflow Gateway.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 6
"""
from __future__ import annotations

from enum import Enum

# ── Version identifiers ────────────────────────────────────────────────────────
VERSION           = "1.0.0"
BUILD_VERSION     = "c16-m6"
GATEWAY_VERSION   = "1.0"
FRAMEWORK_VERSION = "c16-1.0"

# ── ID prefixes ────────────────────────────────────────────────────────────────
PREFIX_GATEWAY  = "wgw-"
PREFIX_REQUEST  = "wgwreq-"
PREFIX_RESPONSE = "wgwres-"
PREFIX_EVENT    = "wgwevt-"
PREFIX_CONTEXT  = "wgwctx-"
PREFIX_RECORD   = "wgwrec-"

# ── Defaults ───────────────────────────────────────────────────────────────────
DEFAULT_GATEWAY_ID       = "enterprise-workflow-gateway"
DEFAULT_MAX_HISTORY      = 10_000
DEFAULT_MAX_REGISTRY     = 50_000
DEFAULT_TIMEOUT_MS       = 30_000.0
DEFAULT_ENVIRONMENT      = "production"
DEFAULT_PRIORITY         = 1
DEFAULT_ENTERPRISE_ID    = "iios"

# ── Actor labels ───────────────────────────────────────────────────────────────
ACTOR_GATEWAY    = "workflow_gateway"
ACTOR_ROUTER     = "workflow_gateway_router"
ACTOR_DISPATCHER = "workflow_gateway_dispatcher"
ACTOR_MANAGER    = "workflow_gateway_manager"
ACTOR_COMPONENT  = "workflow_component"


class GatewayState(str, Enum):
    """Gateway operational state."""
    UNINITIALIZED = "uninitialized"
    INITIALIZED   = "initialized"
    RUNNING       = "running"
    STOPPING      = "stopping"
    STOPPED       = "stopped"
    FAILED        = "failed"


class GatewayEventType(str, Enum):
    """Domain event types emitted by the Enterprise Workflow Gateway."""
    GATEWAY_INITIALIZED = "gateway_initialized"
    GATEWAY_STARTED     = "gateway_started"
    GATEWAY_VALIDATED   = "gateway_validated"
    WORKFLOW_SUBMITTED  = "workflow_submitted"
    WORKFLOW_COMPLETED  = "workflow_completed"
    WORKFLOW_CANCELLED  = "workflow_cancelled"
    WORKFLOW_RETRIED    = "workflow_retried"
    SNAPSHOT_PUBLISHED  = "snapshot_published"
    GATEWAY_STOPPED     = "gateway_stopped"
    GATEWAY_FAILED      = "gateway_failed"


class GatewayRequestType(str, Enum):
    """Type of operation requested through the gateway."""
    SUBMIT   = "submit"
    QUERY    = "query"
    CANCEL   = "cancel"
    RETRY    = "retry"
    VALIDATE = "validate"


class GatewayResponseStatus(str, Enum):
    """Status of a gateway response."""
    SUCCESS  = "success"
    FAILURE  = "failure"
    PARTIAL  = "partial"
    PENDING  = "pending"
    REJECTED = "rejected"


class ComponentType(str, Enum):
    """Type of integrated workflow component (M1–M5)."""
    LIFECYCLE           = "lifecycle"
    ENGINE              = "engine"
    POLICY_ENGINE       = "policy_engine"
    ORCHESTRATION_ENGINE = "orchestration_engine"
    SNAPSHOT            = "snapshot"


class ComponentStatus(str, Enum):
    """Health status of an integrated component."""
    AVAILABLE   = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED    = "degraded"
    UNKNOWN     = "unknown"


class GatewayHealthStatus(str, Enum):
    """Overall health status of the gateway."""
    HEALTHY   = "healthy"
    DEGRADED  = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN   = "unknown"
