"""iios/execution/gateway/integration/__init__.py
==================================================
Public API for the IIOS Execution Gateway Integration Layer.

ExecutionGatewayIntegrationEngine is the ONLY public interface
to the Execution Gateway subsystem.

Every downstream subsystem (Execution Monitoring, Recovery,
Broker Plugins, Compliance, Audit, Analytics) MUST communicate
ONLY through this integration layer.

Quick start
-----------
  from iios.execution.gateway.integration import (
      ExecutionGatewayIntegrationEngine,
      make_integration_context,
      make_integration_request,
  )

  engine = ExecutionGatewayIntegrationEngine()
  engine.initialize()
  engine.start()

  ctx = make_integration_context(
      "EX-001", "ORD-001", "PORT-A", "STRAT-1",
      symbol="RELIANCE", side="BUY", quantity=50,
  )
  request  = make_integration_request(ctx, engine.integration_id)
  response = engine.submit(request)

  print(response.outcome)
  engine.stop()

C6 Execution Intelligence — Phase 5, Module 6
"""
from __future__ import annotations

# ── Constants / enumerations ──────────────────────────────────────────────────
from .constants import (
    ACTOR_INTEGRATION_ENGINE,
    ACTOR_INTEGRATION_MANAGER,
    ACTOR_INTEGRATION_SYSTEM,
    ACTIVE_REQUEST_STATUSES,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_REQUESTS,
    HEALTHY_COMPONENT_HEALTHS,
    INTEGRATION_COMPONENT_REGISTRY_SYSTEM_ID,
    INTEGRATION_MANAGER_SYSTEM_ID,
    INTEGRATION_REGISTRY_SYSTEM_ID,
    INTEGRATION_SYSTEM_ID,
    SCHEMA_VERSION,
    TERMINAL_REQUEST_STATUSES,
    VERSION,
    ComponentHealth,
    ComponentType,
    IntegrationEventType,
    IntegrationOutcome,
    IntegrationRequestStatus,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .exceptions import (
    ComponentNotHealthyError,
    ComponentNotRegisteredError,
    GatewayIntegrationError,
    IntegrationCapacityError,
    IntegrationNotRunningError,
    IntegrationRequestNotFoundError,
    IntegrationRequestValidationError,
    IntegrationWorkflowError,
    SubsystemNotInitializedError,
)

# ── Context ───────────────────────────────────────────────────────────────────
from .gateway_integration_context import (
    GatewayIntegrationContext,
    make_integration_context,
)

# ── Request ───────────────────────────────────────────────────────────────────
from .gateway_integration_request import (
    GatewayIntegrationRequest,
    make_integration_request,
)

# ── Response ──────────────────────────────────────────────────────────────────
from .gateway_integration_response import GatewayIntegrationResponse

# ── Integration snapshot ──────────────────────────────────────────────────────
from .gateway_integration_snapshot import GatewayIntegrationSnapshot

# ── Validation ────────────────────────────────────────────────────────────────
from .gateway_integration_validation import (
    GatewayIntegrationValidationResult,
    GatewayIntegrationValidator,
)

# ── Health ────────────────────────────────────────────────────────────────────
from .gateway_integration_health import (
    ComponentHealthRecord,
    GatewayIntegrationHealthMonitor,
    IntegrationHealthReport,
)

# ── Status ────────────────────────────────────────────────────────────────────
from .gateway_integration_status import GatewayIntegrationStatus

# ── Statistics ────────────────────────────────────────────────────────────────
from .gateway_integration_statistics import GatewayIntegrationStatistics

# ── History ───────────────────────────────────────────────────────────────────
from .gateway_integration_history import GatewayIntegrationHistory

# ── Events ────────────────────────────────────────────────────────────────────
from .gateway_integration_events import (
    IntegrationEvent,
    make_health_updated_event,
    make_request_completed_event,
    make_request_failed_event,
    make_request_received_event,
    make_request_routed_event,
    make_request_validated_event,
    make_snapshot_published_event,
    make_subsystem_initialized_event,
    make_subsystem_started_event,
    make_subsystem_stopped_event,
)

# ── Registries ────────────────────────────────────────────────────────────────
from .gateway_integration_registry import GatewayIntegrationRegistry
from .gateway_component_registry import GatewayComponentRegistry

# ── Factory ───────────────────────────────────────────────────────────────────
from .gateway_component_factory import GatewayComponentFactory

# ── Manager ───────────────────────────────────────────────────────────────────
from .gateway_integration_manager import GatewayIntegrationManager

# ── Primary engine (THE public interface) ─────────────────────────────────────
from .execution_gateway_integration_engine import ExecutionGatewayIntegrationEngine


__all__ = [
    # Constants
    "INTEGRATION_SYSTEM_ID",
    "INTEGRATION_MANAGER_SYSTEM_ID",
    "INTEGRATION_REGISTRY_SYSTEM_ID",
    "INTEGRATION_COMPONENT_REGISTRY_SYSTEM_ID",
    "ACTOR_INTEGRATION_ENGINE",
    "ACTOR_INTEGRATION_MANAGER",
    "ACTOR_INTEGRATION_SYSTEM",
    "DEFAULT_MAX_REQUESTS",
    "DEFAULT_MAX_HISTORY",
    "SCHEMA_VERSION",
    "VERSION",
    "TERMINAL_REQUEST_STATUSES",
    "ACTIVE_REQUEST_STATUSES",
    "HEALTHY_COMPONENT_HEALTHS",
    # Enums
    "ComponentHealth",
    "ComponentType",
    "IntegrationEventType",
    "IntegrationOutcome",
    "IntegrationRequestStatus",
    # Exceptions
    "GatewayIntegrationError",
    "IntegrationNotRunningError",
    "IntegrationRequestValidationError",
    "IntegrationRequestNotFoundError",
    "ComponentNotRegisteredError",
    "ComponentNotHealthyError",
    "IntegrationCapacityError",
    "IntegrationWorkflowError",
    "SubsystemNotInitializedError",
    # Context
    "GatewayIntegrationContext",
    "make_integration_context",
    # Request
    "GatewayIntegrationRequest",
    "make_integration_request",
    # Response
    "GatewayIntegrationResponse",
    # Integration snapshot
    "GatewayIntegrationSnapshot",
    # Validation
    "GatewayIntegrationValidationResult",
    "GatewayIntegrationValidator",
    # Health
    "ComponentHealthRecord",
    "GatewayIntegrationHealthMonitor",
    "IntegrationHealthReport",
    # Status
    "GatewayIntegrationStatus",
    # Statistics
    "GatewayIntegrationStatistics",
    # History
    "GatewayIntegrationHistory",
    # Events
    "IntegrationEvent",
    "make_health_updated_event",
    "make_request_completed_event",
    "make_request_failed_event",
    "make_request_received_event",
    "make_request_routed_event",
    "make_request_validated_event",
    "make_snapshot_published_event",
    "make_subsystem_initialized_event",
    "make_subsystem_started_event",
    "make_subsystem_stopped_event",
    # Registries / Factory / Manager
    "GatewayIntegrationRegistry",
    "GatewayComponentRegistry",
    "GatewayComponentFactory",
    "GatewayIntegrationManager",
    # PRIMARY ENGINE
    "ExecutionGatewayIntegrationEngine",
]
