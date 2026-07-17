"""iios/execution/risk/rules/__init__.py
==================================================
Public API for the IIOS Execution Risk Rules Framework.

C6 Execution Intelligence — Phase 4, Module 3
"""
from __future__ import annotations

# ── Constants & enumerations ──────────────────────────────────────────────────
from .constants import (
    ACTOR_EXECUTOR,
    ACTOR_FRAMEWORK,
    ACTOR_SYSTEM,
    BLOCKING_OUTCOMES,
    DEFAULT_EXECUTION_TIMEOUT_MS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_RULES,
    DEFAULT_SEARCH_LIMIT,
    MANAGER_SYSTEM_ID,
    PASSING_OUTCOMES,
    REGISTRY_SYSTEM_ID,
    RULES_SYSTEM_ID,
    TERMINAL_OUTCOMES,
    VERSION,
    WARNING_OUTCOMES,
    ExecutionMode,
    RuleEventType,
    RuleOutcome,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .exceptions import (
    CircularDependencyError,
    DuplicateRuleError,
    ExecutionRuleError,
    RuleExecutionError,
    RuleFrameworkError,
    RuleNotFoundError,
    RuleNotRunningError,
    RuleRegistrationError,
    RuleTimeoutError,
    RuleValidationError,
)

# ── Domain types ──────────────────────────────────────────────────────────────
from .rule_category import RuleCategory
from .rule_priority import RulePriority
from .rule_result import (
    RuleResult,
    make_block_result,
    make_failed_result,
    make_override_required_result,
    make_pass_result,
    make_skip_result,
    make_warning_result,
)
from .rule_context import (
    RuleContext,
    make_rule_context,
    make_rule_context_from_engine,
)
from .rule_events import (
    RuleEvent,
    make_rule_blocked_event,
    make_rule_completed_event,
    make_rule_failed_event,
    make_rule_passed_event,
    make_rule_registered_event,
    make_rule_started_event,
    make_rule_unregistered_event,
    make_rule_warning_event,
)
from .rule_history import RuleHistory
from .rule_statistics import FrameworkStatistics, RuleExecutionStatistics
from .rule_validation import RuleFrameworkValidator, ValidationResult

# ── Base rule & adapter ───────────────────────────────────────────────────────
from .base_rule import BaseRule, RuleEngineAdapter

# ── Framework services ────────────────────────────────────────────────────────
from .rule_registry import RuleRegistry
from .rule_executor import RuleExecutor
from .rule_factory import RuleFactory
from .rule_manager import RuleManager

# ── Built-in rules ────────────────────────────────────────────────────────────
from .builtin import (
    ALL_BUILTIN_RULES,
    ComplianceRule,
    DailyLossRule,
    DuplicateOrderRule,
    EmergencyStopRule,
    ExposureRule,
    LiquidityRule,
    MarginRule,
    OperationalHealthRule,
    OrderSizeRule,
    PositionLimitRule,
    PriceDeviationRule,
    SessionRule,
)

__all__ = [
    # constants
    "RULES_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "MANAGER_SYSTEM_ID",
    "ACTOR_FRAMEWORK",
    "ACTOR_EXECUTOR",
    "ACTOR_SYSTEM",
    "VERSION",
    "DEFAULT_MAX_RULES",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_EXECUTION_TIMEOUT_MS",
    "DEFAULT_SEARCH_LIMIT",
    "BLOCKING_OUTCOMES",
    "PASSING_OUTCOMES",
    "WARNING_OUTCOMES",
    "TERMINAL_OUTCOMES",
    # enumerations
    "ExecutionMode",
    "RuleEventType",
    "RuleOutcome",
    # exceptions
    "ExecutionRuleError",
    "RuleRegistrationError",
    "DuplicateRuleError",
    "RuleNotFoundError",
    "RuleValidationError",
    "RuleExecutionError",
    "RuleTimeoutError",
    "RuleFrameworkError",
    "RuleNotRunningError",
    "CircularDependencyError",
    # domain types
    "RuleCategory",
    "RulePriority",
    "RuleResult",
    "make_pass_result",
    "make_warning_result",
    "make_block_result",
    "make_skip_result",
    "make_failed_result",
    "make_override_required_result",
    "RuleContext",
    "make_rule_context",
    "make_rule_context_from_engine",
    "RuleEvent",
    "make_rule_registered_event",
    "make_rule_unregistered_event",
    "make_rule_started_event",
    "make_rule_completed_event",
    "make_rule_passed_event",
    "make_rule_warning_event",
    "make_rule_blocked_event",
    "make_rule_failed_event",
    "RuleHistory",
    "RuleExecutionStatistics",
    "FrameworkStatistics",
    "RuleFrameworkValidator",
    "ValidationResult",
    # base
    "BaseRule",
    "RuleEngineAdapter",
    # services
    "RuleRegistry",
    "RuleExecutor",
    "RuleFactory",
    "RuleManager",
    # built-in rules
    "ALL_BUILTIN_RULES",
    "EmergencyStopRule",
    "ComplianceRule",
    "ExposureRule",
    "MarginRule",
    "LiquidityRule",
    "OrderSizeRule",
    "PositionLimitRule",
    "DailyLossRule",
    "PriceDeviationRule",
    "SessionRule",
    "OperationalHealthRule",
    "DuplicateOrderRule",
]
