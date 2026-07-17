"""iios/execution/risk/engine/__init__.py
==================================================
Public API for the IIOS Execution Risk Engine.

C6 Execution Intelligence — Phase 4, Module 2
"""
from __future__ import annotations

# ── Constants & enumerations ──────────────────────────────────────────────────
from .constants import (
    ACTOR_ENGINE,
    ACTOR_MANAGER,
    ACTOR_SYSTEM,
    DEFAULT_MAX_EVALUATIONS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_RULES,
    DEFAULT_SEARCH_LIMIT,
    ENGINE_SYSTEM_ID,
    FACTORY_SYSTEM_ID,
    MANAGER_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    TERMINAL_OP_STATES,
    VALIDATOR_SYSTEM_ID,
    VERSION,
    EngineEventType,
    EngineOpState,
    OperationType,
    RuleOutcome,
    ValidationCode,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .exceptions import (
    EvaluationAggregationError,
    EvaluationCreationError,
    EvaluationExecutionError,
    EvaluationFinalizationError,
    EvaluationNotFoundError,
    EvaluationOperationError,
    ExecutionRiskEngineError,
    RiskEngineNotRunningError,
    RiskEngineStateError,
    RiskEngineValidationError,
    RuleRegistrationError,
)

# ── Domain objects ────────────────────────────────────────────────────────────
from .execution_risk_context import EvaluationContext, make_evaluation_context
from .execution_risk_events import (
    RiskEngineEvent,
    make_engine_started_event,
    make_engine_stopped_event,
    make_evaluation_completed_event,
    make_evaluation_failed_event,
    make_evaluation_started_event,
    make_rule_execution_completed_event,
    make_rule_execution_started_event,
    make_snapshot_published_event,
)
from .execution_risk_factory import EvaluationFactory
from .execution_risk_history import EngineRiskHistory
from .execution_risk_registry import EngineRiskRegistry
from .execution_risk_request import (
    EvaluationRequest,
    QueryEvaluationRequest,
    RiskRuleProtocol,
    RuleResult,
)
from .execution_risk_result import (
    EvaluationResult,
    make_failure_result,
    make_success_result,
)
from .execution_risk_snapshot import (
    EvaluationSummary,
    RiskEngineSnapshot,
    make_engine_risk_snapshot,
)
from .execution_risk_state import EngineOpStateRecord
from .execution_risk_statistics import EngineRiskStatistics
from .execution_risk_validation import EngineValidator, ValidationResult

# ── Engine & Manager ──────────────────────────────────────────────────────────
from .execution_risk_manager import RiskManager
from .execution_risk_engine import RiskEngine

__all__ = [
    # constants
    "ENGINE_SYSTEM_ID",
    "MANAGER_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    "VALIDATOR_SYSTEM_ID",
    "ACTOR_ENGINE",
    "ACTOR_MANAGER",
    "ACTOR_SYSTEM",
    "VERSION",
    "DEFAULT_MAX_EVALUATIONS",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_RULES",
    "DEFAULT_SEARCH_LIMIT",
    "TERMINAL_OP_STATES",
    # enumerations
    "EngineEventType",
    "EngineOpState",
    "OperationType",
    "RuleOutcome",
    "ValidationCode",
    # exceptions
    "ExecutionRiskEngineError",
    "RiskEngineNotRunningError",
    "EvaluationOperationError",
    "EvaluationCreationError",
    "EvaluationExecutionError",
    "EvaluationAggregationError",
    "EvaluationFinalizationError",
    "EvaluationNotFoundError",
    "RuleRegistrationError",
    "RiskEngineValidationError",
    "RiskEngineStateError",
    # domain objects
    "EvaluationContext",
    "make_evaluation_context",
    "RiskEngineEvent",
    "make_evaluation_started_event",
    "make_rule_execution_started_event",
    "make_rule_execution_completed_event",
    "make_evaluation_completed_event",
    "make_evaluation_failed_event",
    "make_snapshot_published_event",
    "make_engine_started_event",
    "make_engine_stopped_event",
    "EvaluationFactory",
    "EngineRiskHistory",
    "EngineRiskRegistry",
    "EvaluationRequest",
    "QueryEvaluationRequest",
    "RiskRuleProtocol",
    "RuleResult",
    "EvaluationResult",
    "make_success_result",
    "make_failure_result",
    "EvaluationSummary",
    "RiskEngineSnapshot",
    "make_engine_risk_snapshot",
    "EngineOpStateRecord",
    "EngineRiskStatistics",
    "EngineValidator",
    "ValidationResult",
    # services
    "RiskManager",
    "RiskEngine",
]
