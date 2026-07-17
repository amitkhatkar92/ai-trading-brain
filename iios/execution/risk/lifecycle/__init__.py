"""iios/execution/risk/lifecycle/__init__.py
==================================================
Public API for the IIOS Execution Risk Lifecycle layer.

C6 Execution Intelligence — Phase 4, Module 1
"""
from __future__ import annotations

# ── Constants & enumerations ──────────────────────────────────────────────────
from .constants import (
    ACTIVE_STATES,
    ACTOR_FACTORY,
    ACTOR_LIFECYCLE,
    ACTOR_REGISTRY,
    ACTOR_SYSTEM,
    BLOCKING_STATES,
    DEFAULT_MAX_EVALUATIONS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_SEARCH_LIMIT,
    ENDED_STATES,
    FACTORY_SYSTEM_ID,
    LIFECYCLE_SYSTEM_ID,
    OUTCOME_STATES,
    PASS_STATES,
    REGISTRY_SYSTEM_ID,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    VALIDATOR_SYSTEM_ID,
    VERSION,
    RiskCategory,
    RiskEventType,
    RiskState,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .exceptions import (
    DuplicateRiskError,
    ExecutionRiskLifecycleError,
    InvalidRiskTransitionError,
    RiskNotFoundError,
    RiskRegistryCapacityError,
    RiskRegistryNotRunningError,
    RiskStateError,
    RiskValidationError,
)

# ── Domain model ──────────────────────────────────────────────────────────────
from .execution_risk import ExecutionRisk
from .execution_risk_context import RiskContext, make_risk_context
from .execution_risk_event import (
    RiskEvent,
    make_risk_archived,
    make_risk_blocked,
    make_risk_created,
    make_risk_evaluation_started,
    make_risk_expired,
    make_risk_overridden,
    make_risk_passed,
    make_risk_warning,
)
from .execution_risk_history import RiskHistory
from .execution_risk_metadata import RiskMetadata
from .execution_risk_state import RiskStateRecord
from .execution_risk_statistics import RiskStatistics
from .execution_risk_transition import RiskTransition, make_risk_transition
from .execution_risk_validation import RiskValidator, ValidationResult

# ── Services ──────────────────────────────────────────────────────────────────
from .execution_risk_factory import RiskFactory
from .execution_risk_registry import RiskRegistry

__all__ = [
    # constants
    "LIFECYCLE_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    "VALIDATOR_SYSTEM_ID",
    "ACTOR_SYSTEM",
    "ACTOR_LIFECYCLE",
    "ACTOR_REGISTRY",
    "ACTOR_FACTORY",
    "VERSION",
    "DEFAULT_MAX_EVALUATIONS",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_SEARCH_LIMIT",
    "VALID_TRANSITIONS",
    "TERMINAL_STATES",
    "ACTIVE_STATES",
    "OUTCOME_STATES",
    "ENDED_STATES",
    "PASS_STATES",
    "BLOCKING_STATES",
    # enums
    "RiskState",
    "RiskCategory",
    "RiskEventType",
    # exceptions
    "ExecutionRiskLifecycleError",
    "InvalidRiskTransitionError",
    "RiskNotFoundError",
    "DuplicateRiskError",
    "RiskValidationError",
    "RiskRegistryCapacityError",
    "RiskRegistryNotRunningError",
    "RiskStateError",
    # domain model
    "ExecutionRisk",
    "RiskStateRecord",
    "RiskTransition",
    "RiskEvent",
    "RiskHistory",
    "RiskMetadata",
    "RiskStatistics",
    "RiskContext",
    "ValidationResult",
    # factory functions
    "make_risk_transition",
    "make_risk_context",
    "make_risk_created",
    "make_risk_evaluation_started",
    "make_risk_passed",
    "make_risk_warning",
    "make_risk_blocked",
    "make_risk_overridden",
    "make_risk_expired",
    "make_risk_archived",
    # services
    "RiskFactory",
    "RiskRegistry",
    # validator
    "RiskValidator",
]
