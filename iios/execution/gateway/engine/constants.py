"""iios/execution/gateway/engine/constants.py
==================================================
Constants, enumerations, and defaults for the IIOS
Execution Gateway Engine.

C6 Execution Intelligence — Phase 5, Module 2
"""
from __future__ import annotations

from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

ENGINE_SYSTEM_ID     = "iios:execution:gateway:engine"
MANAGER_SYSTEM_ID    = "iios:execution:gateway:engine:manager"
REGISTRY_SYSTEM_ID   = "iios:execution:gateway:engine:registry"
FACTORY_SYSTEM_ID    = "iios:execution:gateway:engine:factory"
VALIDATOR_SYSTEM_ID  = "iios:execution:gateway:engine:validator"
DISPATCHER_SYSTEM_ID = "iios:execution:gateway:engine:dispatcher"
SESSION_SYSTEM_ID    = "iios:execution:gateway:engine:session"

VERSION = "1.0.0"

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_MAX_REQUESTS          = 10_000
DEFAULT_MAX_HISTORY           = 5_000
DEFAULT_MAX_QUEUE_SIZE        = 5_000
DEFAULT_MAX_SESSIONS          = 1_000
DEFAULT_SESSION_TIMEOUT_SECS  = 3_600.0   # 1 hour
DEFAULT_MAX_RETRIES           = 3
DEFAULT_RETRY_DELAY_SECS      = 1.0
DEFAULT_SEARCH_LIMIT          = 1_000

# ── Actor labels ──────────────────────────────────────────────────────────────

ACTOR_ENGINE     = "iios:execution:gateway:engine"
ACTOR_MANAGER    = "iios:execution:gateway:engine:manager"
ACTOR_DISPATCHER = "iios:execution:gateway:engine:dispatcher"
ACTOR_SYSTEM     = "iios:system"


# ── Engine state ──────────────────────────────────────────────────────────────

class EngineState(str, Enum):
    """
    Operational state of the Gateway Engine.

    Tracks the current processing phase of the engine.
    IDLE indicates the engine is running and ready for requests.
    STOPPED / FAILED are terminal states.
    """
    IDLE          = "IDLE"
    INITIALIZING  = "INITIALIZING"
    VALIDATING    = "VALIDATING"
    QUEUING       = "QUEUING"
    DISPATCHING   = "DISPATCHING"
    WAITING       = "WAITING"
    COMPLETING    = "COMPLETING"
    FAILED        = "FAILED"
    STOPPED       = "STOPPED"


TERMINAL_ENGINE_STATES: frozenset[EngineState] = frozenset({
    EngineState.FAILED,
    EngineState.STOPPED,
})

ACTIVE_ENGINE_STATES: frozenset[EngineState] = frozenset({
    EngineState.IDLE,
    EngineState.INITIALIZING,
    EngineState.VALIDATING,
    EngineState.QUEUING,
    EngineState.DISPATCHING,
    EngineState.WAITING,
    EngineState.COMPLETING,
})


# ── Operation type ────────────────────────────────────────────────────────────

class OperationType(str, Enum):
    """Types of operations performed by the Gateway Engine."""
    INITIALIZE      = "INITIALIZE"
    START           = "START"
    SUBMIT_REQUEST  = "SUBMIT_REQUEST"
    QUEUE_REQUEST   = "QUEUE_REQUEST"
    DISPATCH_REQUEST = "DISPATCH_REQUEST"
    COMPLETE_REQUEST = "COMPLETE_REQUEST"
    CANCEL_REQUEST  = "CANCEL_REQUEST"
    RETRY_REQUEST   = "RETRY_REQUEST"
    SHUTDOWN        = "SHUTDOWN"


# ── Engine event types ────────────────────────────────────────────────────────

class EngineEventType(str, Enum):
    """Domain events published by the Execution Gateway Engine."""
    GATEWAY_STARTED     = "GATEWAY_STARTED"
    REQUEST_RECEIVED    = "REQUEST_RECEIVED"
    REQUEST_QUEUED      = "REQUEST_QUEUED"
    REQUEST_DISPATCHED  = "REQUEST_DISPATCHED"
    DISPATCH_COMPLETED  = "DISPATCH_COMPLETED"
    DISPATCH_FAILED     = "DISPATCH_FAILED"
    GATEWAY_STOPPED     = "GATEWAY_STOPPED"


# ── Queue type ────────────────────────────────────────────────────────────────

class QueueType(str, Enum):
    """The four queue types managed by GatewayOperationQueue."""
    FIFO         = "FIFO"
    PRIORITY     = "PRIORITY"
    RETRY        = "RETRY"
    CANCELLATION = "CANCELLATION"


# ── Request status ────────────────────────────────────────────────────────────

class RequestStatus(str, Enum):
    """Status of an EngineGatewayRequest."""
    PENDING     = "PENDING"
    QUEUED      = "QUEUED"
    DISPATCHING = "DISPATCHING"
    COMPLETED   = "COMPLETED"
    FAILED      = "FAILED"
    CANCELLED   = "CANCELLED"
    RETRYING    = "RETRYING"


TERMINAL_REQUEST_STATUSES: frozenset[RequestStatus] = frozenset({
    RequestStatus.COMPLETED,
    RequestStatus.FAILED,
    RequestStatus.CANCELLED,
})

ACTIVE_REQUEST_STATUSES: frozenset[RequestStatus] = frozenset({
    RequestStatus.PENDING,
    RequestStatus.QUEUED,
    RequestStatus.DISPATCHING,
    RequestStatus.RETRYING,
})


# ── Dispatch outcome ──────────────────────────────────────────────────────────

class DispatchOutcome(str, Enum):
    """The outcome of a dispatch call to the broker abstraction."""
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    DEFERRED = "DEFERRED"


# ── Session status ────────────────────────────────────────────────────────────

class SessionStatus(str, Enum):
    """Status of a GatewaySession."""
    ACTIVE     = "ACTIVE"
    EXPIRED    = "EXPIRED"
    CLOSED     = "CLOSED"
    RECOVERING = "RECOVERING"
