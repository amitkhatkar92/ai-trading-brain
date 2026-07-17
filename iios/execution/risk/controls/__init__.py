"""iios/execution/risk/controls/__init__.py
==================================================
Public API for the IIOS Execution Risk Controls Framework.

C6 Execution Intelligence — Phase 4, Module 4
"""
from __future__ import annotations

# ── Constants & enumerations ──────────────────────────────────────────────────
from .constants import (
    ACTOR_ENGINE,
    ACTOR_MANAGER,
    ACTOR_POLICY,
    ACTOR_SYSTEM,
    ACTION_PRIORITY,
    BLOCKING_ACTIONS,
    CONTROLS_SYSTEM_ID,
    DEFAULT_DECISION_TIMEOUT_MS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_REQUESTS,
    DEFAULT_PASS_THRESHOLD,
    DEFERRAL_ACTIONS,
    ENGINE_SYSTEM_ID,
    MANAGER_SYSTEM_ID,
    OUTCOME_TO_ACTION,
    PASSTHROUGH_ACTIONS,
    REGISTRY_SYSTEM_ID,
    TERMINAL_ACTIONS,
    VERSION,
    ControlAction,
    ControlEventType,
    PolicyType,
    highest_priority_action,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .exceptions import (
    ControlFrameworkError,
    ControlNotRunningError,
    ControlRegistrationError,
    ControlValidationError,
    EmergencyActionError,
    ExecutionControlError,
    OverrideError,
    PolicyEvaluationError,
    PolicyNotFoundError,
)

# ── Domain types ──────────────────────────────────────────────────────────────
from .risk_control_action import (
    ACTION_METADATA,
    ControlActionMetadata,
    action_priority,
    can_retry,
    get_action_metadata,
    is_blocking_action,
    is_emergency_action,
    is_terminal_action,
    requires_override,
)
from .risk_control_context import (
    ControlContext,
    make_control_context,
    make_control_context_from_rule_context,
)
from .risk_control_request import (
    ControlRequest,
    make_control_request,
)
from .risk_control_response import (
    ControlResponse,
    make_control_response,
    make_error_response,
)
from .risk_control_decision import (
    EmergencyInfo,
    OverrideInfo,
    RiskControlDecision,
    make_allow_decision,
    make_block_decision,
    make_emergency_decision,
    make_emergency_info,
    make_override_info,
    make_override_required_decision,
    make_warning_decision,
)
from .risk_control_events import (
    ControlEvent,
    make_control_approved_event,
    make_control_evaluated_event,
    make_control_paused_event,
    make_control_retried_event,
    make_emergency_triggered_event,
    make_execution_blocked_event,
    make_override_approved_event,
    make_override_requested_event,
)
from .risk_control_history import ControlHistory
from .risk_control_statistics import ControlStatistics
from .risk_control_validation import (
    ControlValidationResult,
    RiskControlValidator,
)

# ── Policies ──────────────────────────────────────────────────────────────────
from .risk_control_policy import (
    BasePolicy,
    ConfigurablePolicy,
    EmergencyPolicy,
    HighestSeverityPolicy,
    MajorityPolicy,
    SingleRulePolicy,
    WeightedSeverityPolicy,
)

# ── Services ──────────────────────────────────────────────────────────────────
from .risk_control_registry import ControlPolicyRegistry
from .risk_control_factory import RiskControlFactory
from .risk_control_engine import RiskControlEngine
from .risk_control_manager import RiskControlManager

__all__ = [
    # constants
    "CONTROLS_SYSTEM_ID",
    "ENGINE_SYSTEM_ID",
    "MANAGER_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "ACTOR_ENGINE",
    "ACTOR_MANAGER",
    "ACTOR_POLICY",
    "ACTOR_SYSTEM",
    "VERSION",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_REQUESTS",
    "DEFAULT_DECISION_TIMEOUT_MS",
    "DEFAULT_PASS_THRESHOLD",
    "ACTION_PRIORITY",
    "BLOCKING_ACTIONS",
    "TERMINAL_ACTIONS",
    "PASSTHROUGH_ACTIONS",
    "DEFERRAL_ACTIONS",
    "OUTCOME_TO_ACTION",
    # enumerations
    "ControlAction",
    "ControlEventType",
    "PolicyType",
    "highest_priority_action",
    # exceptions
    "ExecutionControlError",
    "ControlNotRunningError",
    "PolicyEvaluationError",
    "PolicyNotFoundError",
    "ControlValidationError",
    "OverrideError",
    "EmergencyActionError",
    "ControlFrameworkError",
    "ControlRegistrationError",
    # action metadata
    "ControlActionMetadata",
    "ACTION_METADATA",
    "get_action_metadata",
    "is_blocking_action",
    "is_terminal_action",
    "is_emergency_action",
    "requires_override",
    "can_retry",
    "action_priority",
    # context
    "ControlContext",
    "make_control_context",
    "make_control_context_from_rule_context",
    # request
    "ControlRequest",
    "make_control_request",
    # response
    "ControlResponse",
    "make_control_response",
    "make_error_response",
    # decision
    "RiskControlDecision",
    "OverrideInfo",
    "EmergencyInfo",
    "make_allow_decision",
    "make_block_decision",
    "make_warning_decision",
    "make_override_required_decision",
    "make_emergency_decision",
    "make_override_info",
    "make_emergency_info",
    # events
    "ControlEvent",
    "make_control_evaluated_event",
    "make_control_approved_event",
    "make_control_paused_event",
    "make_control_retried_event",
    "make_override_requested_event",
    "make_override_approved_event",
    "make_execution_blocked_event",
    "make_emergency_triggered_event",
    # history
    "ControlHistory",
    # statistics
    "ControlStatistics",
    # validation
    "ControlValidationResult",
    "RiskControlValidator",
    # policies
    "BasePolicy",
    "SingleRulePolicy",
    "MajorityPolicy",
    "HighestSeverityPolicy",
    "WeightedSeverityPolicy",
    "EmergencyPolicy",
    "ConfigurablePolicy",
    # services
    "ControlPolicyRegistry",
    "RiskControlFactory",
    "RiskControlEngine",
    "RiskControlManager",
]
