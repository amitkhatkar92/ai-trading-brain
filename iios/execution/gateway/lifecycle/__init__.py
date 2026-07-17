"""iios/execution/gateway/lifecycle/__init__.py
==================================================
Public API for the Execution Gateway Lifecycle (C6 Phase 5, M1).

This is the ONLY public interface to the gateway lifecycle subsystem.
Future modules (Gateway Engine, Broker Abstraction, Routing Framework,
Gateway Snapshot, Gateway Integration) MUST NOT import internal modules
directly.

Quick start
-----------
    from iios.execution.gateway.lifecycle import (
        GatewayLifecycle,
        make_gateway_context,
    )

    lc = GatewayLifecycle()
    lc.start()

    ctx     = make_gateway_context("EX-1", "ORD-1", "PORT-1", "STRAT-1",
                  symbol="RELIANCE", side="BUY", quantity=100, price=2500.0)
    request = lc.create_from_context(ctx)

    lc.receive(request.gateway_id)
    lc.start_validation(request.gateway_id)
    lc.mark_ready(request.gateway_id)
    lc.queue(request.gateway_id)
    lc.start_routing(request.gateway_id)
    lc.dispatch(request.gateway_id)
    lc.complete(request.gateway_id)
    lc.archive(request.gateway_id)

    print(lc.statistics().to_dict())
    lc.stop()

C6 Execution Intelligence — Phase 5, Module 1
"""
from __future__ import annotations

# ── Core ──────────────────────────────────────────────────────────────────────
from .gateway_lifecycle import GatewayLifecycle
from .gateway_request import GatewayRequest

# ── Registry & Factory ────────────────────────────────────────────────────────
from .gateway_registry import GatewayRegistry
from .gateway_factory import GatewayFactory

# ── Value objects ─────────────────────────────────────────────────────────────
from .gateway_context import GatewayContext, make_gateway_context
from .gateway_metadata import GatewayMetadata

# ── State machine ─────────────────────────────────────────────────────────────
from .gateway_state import GatewayStateRecord
from .gateway_transition import GatewayTransition, make_gateway_transition
from .gateway_history import GatewayHistory

# ── Statistics ────────────────────────────────────────────────────────────────
from .gateway_statistics import GatewayStatistics

# ── Validation ────────────────────────────────────────────────────────────────
from .gateway_validation import GatewayValidator, ValidationResult

# ── Events ────────────────────────────────────────────────────────────────────
from .gateway_events import (
    GatewayEvent,
    make_gateway_archived,
    make_gateway_cancelled,
    make_gateway_completed,
    make_gateway_created,
    make_gateway_dispatched,
    make_gateway_failed,
    make_gateway_queued,
    make_gateway_received,
    make_gateway_validated,
)

# ── Constants / enums ─────────────────────────────────────────────────────────
from .constants import (
    ACTIVE_STATES,
    ACTOR_LIFECYCLE,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_REQUESTS,
    ENDED_STATES,
    FAILURE_STATES,
    LIFECYCLE_SYSTEM_ID,
    OUTCOME_STATES,
    REGISTRY_SYSTEM_ID,
    SUCCESS_STATES,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    VERSION,
    GatewayEventType,
    GatewayState,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .exceptions import (
    DuplicateGatewayRequestError,
    ExecutionGatewayLifecycleError,
    GatewayLifecycleNotRunningError,
    GatewayRegistryCapacityError,
    GatewayRequestNotFoundError,
    GatewayStateError,
    GatewayValidationError,
    InvalidGatewayTransitionError,
)

__all__ = [
    # Core
    "GatewayLifecycle",
    "GatewayRequest",
    # Registry & Factory
    "GatewayRegistry",
    "GatewayFactory",
    # Value objects
    "GatewayContext",
    "make_gateway_context",
    "GatewayMetadata",
    # State machine
    "GatewayStateRecord",
    "GatewayTransition",
    "make_gateway_transition",
    "GatewayHistory",
    # Statistics
    "GatewayStatistics",
    # Validation
    "GatewayValidator",
    "ValidationResult",
    # Events
    "GatewayEvent",
    "make_gateway_archived",
    "make_gateway_cancelled",
    "make_gateway_completed",
    "make_gateway_created",
    "make_gateway_dispatched",
    "make_gateway_failed",
    "make_gateway_queued",
    "make_gateway_received",
    "make_gateway_validated",
    # Constants / enums
    "ACTIVE_STATES",
    "ACTOR_LIFECYCLE",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_REQUESTS",
    "ENDED_STATES",
    "FAILURE_STATES",
    "LIFECYCLE_SYSTEM_ID",
    "OUTCOME_STATES",
    "REGISTRY_SYSTEM_ID",
    "SUCCESS_STATES",
    "TERMINAL_STATES",
    "VALID_TRANSITIONS",
    "VERSION",
    "GatewayEventType",
    "GatewayState",
    # Exceptions
    "DuplicateGatewayRequestError",
    "ExecutionGatewayLifecycleError",
    "GatewayLifecycleNotRunningError",
    "GatewayRegistryCapacityError",
    "GatewayRequestNotFoundError",
    "GatewayStateError",
    "GatewayValidationError",
    "InvalidGatewayTransitionError",
]
