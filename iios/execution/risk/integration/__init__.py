"""iios/execution/risk/integration/__init__.py
==================================================
Public API for the Execution Risk Integration subsystem (C6 Phase 4 M6).

This is the ONLY public interface to the Execution Risk subsystem.
Future modules (Execution Gateway, Broker Adapters, Compliance, Audit)
MUST interact ONLY through this integration layer.

Quick start
-----------
    from iios.execution.risk.integration import (
        ExecutionRiskIntegrationManager,
        IntegrationRequestFactory,
    )

    manager = ExecutionRiskIntegrationManager()
    manager.start()

    ctx = IntegrationRequestFactory.create_context("EX-1", "ORD-1",
              portfolio_id="PORT-1", symbol="RELIANCE", side="BUY",
              quantity=100, price=2500.0)
    req = IntegrationRequestFactory.create_request(ctx)

    response = manager.evaluate(req)
    if response.approved:
        proceed()
    else:
        reject(response.action, response.risk_state)

    manager.stop()

C6 Execution Intelligence — Phase 4, Module 6
"""
from __future__ import annotations

# ── Engine & Manager ──────────────────────────────────────────────────────────
from .execution_risk_integration_engine import ExecutionRiskIntegrationEngine
from .execution_risk_integration_manager import ExecutionRiskIntegrationManager

# ── Input / Output ────────────────────────────────────────────────────────────
from .execution_risk_context import ExecutionContext, make_execution_context
from .execution_risk_request import ExecutionRiskRequest, make_execution_risk_request
from .execution_risk_response import ExecutionRiskResponse

# ── Factory ───────────────────────────────────────────────────────────────────
from .execution_risk_factory import IntegrationRequestFactory

# ── Validation ────────────────────────────────────────────────────────────────
from .execution_risk_validation import IntegrationValidator, ValidationReport

# ── Health ────────────────────────────────────────────────────────────────────
from .execution_risk_health import ComponentHealth, SubsystemHealth

# ── Status ────────────────────────────────────────────────────────────────────
from .execution_risk_status import SubsystemStatus

# ── Statistics ────────────────────────────────────────────────────────────────
from .execution_risk_statistics import IntegrationStatistics

# ── History ───────────────────────────────────────────────────────────────────
from .execution_risk_history import IntegrationHistory

# ── Events ────────────────────────────────────────────────────────────────────
from .execution_risk_events import (
    IntegrationEvent,
    make_evaluation_completed_event,
    make_evaluation_requested_event,
    make_health_updated_event,
    make_snapshot_published_event,
    make_subsystem_initialized_event,
    make_subsystem_started_event,
    make_subsystem_stopped_event,
    make_validation_completed_event,
)

# ── Subsystem snapshot ────────────────────────────────────────────────────────
from .execution_risk_integration_snapshot import ExecutionRiskIntegrationSnapshot

# ── Registry ─────────────────────────────────────────────────────────────────
from .execution_risk_registry import ComponentRegistry

# ── Constants / enums ─────────────────────────────────────────────────────────
from .constants import (
    APPROVED_ACTIONS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_TIMEOUT_MS,
    ENGINE_SYSTEM_ID,
    INTEGRATION_SYSTEM_ID,
    MANAGER_SYSTEM_ID,
    REQUIRED_COMPONENT_TYPES,
    VERSION,
    ComponentType,
    EvaluationMode,
    IntegrationEventType,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .exceptions import (
    ComponentNotHealthyError,
    ComponentRegistrationError,
    ContextValidationError,
    EvaluationFailedError,
    ExecutionRiskIntegrationError,
    IntegrationHistoryError,
    IntegrationNotRunningError,
    IntegrationTimeoutError,
    RequestValidationError,
)

__all__ = [
    # Engine & Manager
    "ExecutionRiskIntegrationEngine",
    "ExecutionRiskIntegrationManager",
    # Input / Output
    "ExecutionContext",
    "make_execution_context",
    "ExecutionRiskRequest",
    "make_execution_risk_request",
    "ExecutionRiskResponse",
    # Factory
    "IntegrationRequestFactory",
    # Validation
    "IntegrationValidator",
    "ValidationReport",
    # Health
    "ComponentHealth",
    "SubsystemHealth",
    # Status
    "SubsystemStatus",
    # Statistics
    "IntegrationStatistics",
    # History
    "IntegrationHistory",
    # Events
    "IntegrationEvent",
    "make_evaluation_completed_event",
    "make_evaluation_requested_event",
    "make_health_updated_event",
    "make_snapshot_published_event",
    "make_subsystem_initialized_event",
    "make_subsystem_started_event",
    "make_subsystem_stopped_event",
    "make_validation_completed_event",
    # Subsystem snapshot
    "ExecutionRiskIntegrationSnapshot",
    # Registry
    "ComponentRegistry",
    # Constants / enums
    "APPROVED_ACTIONS",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_TIMEOUT_MS",
    "ENGINE_SYSTEM_ID",
    "INTEGRATION_SYSTEM_ID",
    "MANAGER_SYSTEM_ID",
    "REQUIRED_COMPONENT_TYPES",
    "VERSION",
    "ComponentType",
    "EvaluationMode",
    "IntegrationEventType",
    # Exceptions
    "ComponentNotHealthyError",
    "ComponentRegistrationError",
    "ContextValidationError",
    "EvaluationFailedError",
    "ExecutionRiskIntegrationError",
    "IntegrationHistoryError",
    "IntegrationNotRunningError",
    "IntegrationTimeoutError",
    "RequestValidationError",
]
