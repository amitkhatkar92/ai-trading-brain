"""
constants.py — iios.integration.lifecycle
------------------------------------------
Constants, enums, and the valid-transition table for the
Integration Lifecycle module.

C15 Enterprise Integration & Connectivity — Phase 1, Module 1
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, Set


# ════════════════════════════════════════════════════════════════════════
# Enums
# ════════════════════════════════════════════════════════════════════════


class IntegrationLifecycleState(str, Enum):
    """13 lifecycle states for an enterprise integration session."""
    CREATED      = "created"
    INITIALIZING = "initializing"
    DISCOVERING  = "discovering"
    CONFIGURING  = "configuring"
    VALIDATING   = "validating"
    READY        = "ready"
    CONNECTING   = "connecting"
    ACTIVE       = "active"
    PAUSED       = "paused"
    RESUMING     = "resuming"
    COMPLETED    = "completed"
    FAILED       = "failed"
    ARCHIVED     = "archived"


class IntegrationEventType(str, Enum):
    """11 lifecycle event types."""
    INTEGRATION_CREATED     = "integration_created"
    INTEGRATION_INITIALIZED = "integration_initialized"
    INTEGRATION_CONFIGURED  = "integration_configured"
    INTEGRATION_VALIDATED   = "integration_validated"
    INTEGRATION_CONNECTED   = "integration_connected"
    INTEGRATION_ACTIVATED   = "integration_activated"
    INTEGRATION_PAUSED      = "integration_paused"
    INTEGRATION_RESUMED     = "integration_resumed"
    INTEGRATION_COMPLETED   = "integration_completed"
    INTEGRATION_FAILED      = "integration_failed"
    INTEGRATION_ARCHIVED    = "integration_archived"


class IntegrationType(str, Enum):
    """Type of enterprise integration."""
    REST_API       = "rest_api"
    GRPC           = "grpc"
    WEBSOCKET      = "websocket"
    MESSAGE_QUEUE  = "message_queue"
    DATABASE       = "database"
    FILE           = "file"
    EVENT_STREAM   = "event_stream"
    INTERNAL       = "internal"


class IntegrationScope(str, Enum):
    """Operational scope of an integration session."""
    INTERNAL    = "internal"
    EXTERNAL    = "external"
    ENTERPRISE  = "enterprise"
    SUBSYSTEM   = "subsystem"
    GLOBAL      = "global"


class IntegrationValidationCode(str, Enum):
    """Validation check identifiers."""
    IDENTIFIER_CONSISTENCY  = "identifier_consistency"
    LIFECYCLE_CONSISTENCY   = "lifecycle_consistency"
    TRANSITION_VALIDITY     = "transition_validity"
    TIMESTAMP_CONSISTENCY   = "timestamp_consistency"
    HISTORY_INTEGRITY       = "history_integrity"


# ════════════════════════════════════════════════════════════════════════
# State classification sets
# ════════════════════════════════════════════════════════════════════════

ACTIVE_STATES: Set[IntegrationLifecycleState] = {
    IntegrationLifecycleState.INITIALIZING,
    IntegrationLifecycleState.DISCOVERING,
    IntegrationLifecycleState.CONFIGURING,
    IntegrationLifecycleState.VALIDATING,
    IntegrationLifecycleState.READY,
    IntegrationLifecycleState.CONNECTING,
    IntegrationLifecycleState.ACTIVE,
    IntegrationLifecycleState.PAUSED,
    IntegrationLifecycleState.RESUMING,
}

TERMINAL_STATES: Set[IntegrationLifecycleState] = {
    IntegrationLifecycleState.COMPLETED,
    IntegrationLifecycleState.FAILED,
    IntegrationLifecycleState.ARCHIVED,
}

SUCCESS_STATES: Set[IntegrationLifecycleState] = {
    IntegrationLifecycleState.COMPLETED,
}

IMMUTABLE_STATES: Set[IntegrationLifecycleState] = {
    IntegrationLifecycleState.ARCHIVED,
}

# ════════════════════════════════════════════════════════════════════════
# Valid transition table (strict institutional state machine)
# ════════════════════════════════════════════════════════════════════════

VALID_TRANSITIONS: Dict[IntegrationLifecycleState, Set[IntegrationLifecycleState]] = {
    IntegrationLifecycleState.CREATED: {
        IntegrationLifecycleState.INITIALIZING,
    },
    IntegrationLifecycleState.INITIALIZING: {
        IntegrationLifecycleState.DISCOVERING,
        IntegrationLifecycleState.FAILED,
    },
    IntegrationLifecycleState.DISCOVERING: {
        IntegrationLifecycleState.CONFIGURING,
        IntegrationLifecycleState.FAILED,
    },
    IntegrationLifecycleState.CONFIGURING: {
        IntegrationLifecycleState.VALIDATING,
        IntegrationLifecycleState.FAILED,
    },
    IntegrationLifecycleState.VALIDATING: {
        IntegrationLifecycleState.READY,
        IntegrationLifecycleState.FAILED,
    },
    IntegrationLifecycleState.READY: {
        IntegrationLifecycleState.CONNECTING,
        IntegrationLifecycleState.ARCHIVED,
    },
    IntegrationLifecycleState.CONNECTING: {
        IntegrationLifecycleState.ACTIVE,
        IntegrationLifecycleState.FAILED,
    },
    IntegrationLifecycleState.ACTIVE: {
        IntegrationLifecycleState.PAUSED,
        IntegrationLifecycleState.COMPLETED,
        IntegrationLifecycleState.FAILED,
    },
    IntegrationLifecycleState.PAUSED: {
        IntegrationLifecycleState.RESUMING,
        IntegrationLifecycleState.ARCHIVED,
        IntegrationLifecycleState.FAILED,
    },
    IntegrationLifecycleState.RESUMING: {
        IntegrationLifecycleState.ACTIVE,
        IntegrationLifecycleState.FAILED,
    },
    IntegrationLifecycleState.COMPLETED: {
        IntegrationLifecycleState.ARCHIVED,
    },
    IntegrationLifecycleState.FAILED: {
        IntegrationLifecycleState.ARCHIVED,
        IntegrationLifecycleState.INITIALIZING,   # allow retry
    },
    IntegrationLifecycleState.ARCHIVED: set(),    # terminal — no transitions
}

# ════════════════════════════════════════════════════════════════════════
# System identifiers
# ════════════════════════════════════════════════════════════════════════

LIFECYCLE_SYSTEM_ID = "iios:integration:lifecycle"
REGISTRY_SYSTEM_ID  = "iios:integration:registry"
VERSION             = "1.0.0"
SCHEMA_VERSION      = "1.0"
FRAMEWORK_VERSION   = "1.0.0"
BUILD_VERSION       = "1.0.0-stable"

ACTOR_LIFECYCLE = "iios:integration:lifecycle"
ACTOR_OPERATOR  = "iios:operator"
ACTOR_SYSTEM    = "iios:system"

# ════════════════════════════════════════════════════════════════════════
# Operational defaults
# ════════════════════════════════════════════════════════════════════════

DEFAULT_MAX_SESSIONS    = 10_000
DEFAULT_MAX_HISTORY     = 5_000
DEFAULT_MAX_TRANSITIONS = 100_000
DEFAULT_MAX_ARCHIVED    = 50_000
DEFAULT_VERSION         = "1.0.0"
