"""
iios.decision.policies
=======================
Decision Policy Framework — C9 Decision Intelligence, Phase 1, Module 3.

The Decision Policy Framework evaluates every institutional decision
against configurable enterprise policies and determines whether the
decision is:

  APPROVE | APPROVE_WITH_CONDITIONS | REJECT | BLOCK
  | ESCALATE | DEFER | REQUIRE_MANUAL_REVIEW

It performs NO optimisation, NO execution, and NO broker communication.

Quick start
-----------
>>> from iios.decision.policies import (
...     DecisionPolicyEngine,
...     DecisionPolicyFactory,
...     PolicyEvaluationRequest,
...     PolicyType, PolicyAction, PolicyPriority,
...     PolicyConditionOperator, PolicyRuleLogic,
...     PolicyChainMode, ConflictResolutionStrategy,
... )
>>> engine  = DecisionPolicyEngine()
>>> engine.start()
>>> factory = engine.factory()
>>> cond    = factory.create_condition(
...     "risk_score_gt_80", "inputs.risk_score",
...     PolicyConditionOperator.GT, 80,
... )
>>> rule    = factory.create_rule(
...     "high_risk", [cond], PolicyAction.REJECT
... )
>>> policy  = factory.create_policy(
...     "RiskThreshold", PolicyType.RISK,
...     PolicyPriority.HIGH, PolicyAction.APPROVE,
...     rules=[rule],
... )
>>> engine.register_policy(policy)
>>> ctx     = factory.create_context(
...     request_id="req-1", decision_id="dec-1",
...     inputs={"risk_score": 90},
... )
>>> req     = factory.create_request(ctx)
>>> resp    = engine.evaluate(req)
>>> resp.action
<PolicyAction.REJECT: 'reject'>
>>> engine.stop()
"""
from __future__ import annotations

# ── Constants & enums ────────────────────────────────────────────────────────
from .constants import (
    ACTOR_ENGINE,
    ACTOR_EVALUATOR,
    ACTOR_MANAGER,
    ACTOR_OPERATOR,
    ACTOR_SYSTEM,
    ACTOR_VALIDATOR,
    ACTION_PRECEDENCE,
    APPROVAL_ACTIONS,
    DEFAULT_EVALUATION_TIMEOUT,
    DEFAULT_MAX_CHAIN,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_POLICIES,
    DENY_ACTIONS,
    EMA_ALPHA,
    ESCALATION_ACTIONS,
    POLICIES_SYSTEM_ID,
    SCHEMA_VERSION,
    THROUGHPUT_WINDOW_S,
    VERSION,
    ConflictResolutionStrategy,
    PolicyAction,
    PolicyChainMode,
    PolicyConditionOperator,
    PolicyEvaluationStatus,
    PolicyEventType,
    PolicyPriority,
    PolicyRuleLogic,
    PolicyStatus,
    PolicyType,
    PolicyValidationCode,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .exceptions import (
    DecisionPolicyError,
    PolicyChainError,
    PolicyConfigurationError,
    PolicyConflictError,
    PolicyEngineNotRunningError,
    PolicyEvaluationError,
    PolicyNotFoundError,
    PolicyRegistryError,
    PolicyValidationError,
)

# ── Core data types ───────────────────────────────────────────────────────────
from .decision_policy_condition import PolicyCondition
from .decision_policy_context   import PolicyEvaluationContext
from .decision_policy_priority  import PolicyPriorityResolver
from .decision_policy_result    import (
    PolicyEvaluationSummary,
    PolicyRuleResult,
    SinglePolicyResult,
)
from .decision_policy_rule      import PolicyRule

# ── Policy & request types ────────────────────────────────────────────────────
from .decision_policy         import DecisionPolicy
from .decision_policy_request import PolicyEvaluationRequest

# ── Output / audit / event types ─────────────────────────────────────────────
from .decision_policy_audit    import PolicyAuditEntry, PolicyAuditReport, build_audit_report
from .decision_policy_events   import (
    DecisionPolicyEvent,
    make_policy_approved,
    make_policy_blocked,
    make_policy_escalated,
    make_policy_evaluation_completed,
    make_policy_evaluation_started,
    make_policy_loaded,
    make_policy_rejected,
    make_policy_validated,
)
from .decision_policy_response import DecisionPolicyResponse

# ── Services ──────────────────────────────────────────────────────────────────
from .decision_policy_chain      import DecisionPolicyChain
from .decision_policy_evaluator  import DecisionPolicyEvaluator
from .decision_policy_factory    import DecisionPolicyFactory
from .decision_policy_history    import DecisionPolicyHistory
from .decision_policy_manager    import DecisionPolicyManager
from .decision_policy_registry   import DecisionPolicyRegistry
from .decision_policy_statistics import DecisionPolicyStatistics
from .decision_policy_validator  import (
    DecisionPolicyValidator,
    PolicyValidationCheckResult,
    PolicyValidationResult,
)

# ── Engine & M2 adapter ───────────────────────────────────────────────────────
from .decision_policy_engine import DecisionPolicyEngine, PolicyFrameworkAdapter

__all__ = [
    # Constants
    "ACTOR_ENGINE", "ACTOR_EVALUATOR", "ACTOR_MANAGER", "ACTOR_OPERATOR",
    "ACTOR_SYSTEM", "ACTOR_VALIDATOR",
    "ACTION_PRECEDENCE", "APPROVAL_ACTIONS", "DENY_ACTIONS", "ESCALATION_ACTIONS",
    "DEFAULT_EVALUATION_TIMEOUT", "DEFAULT_MAX_CHAIN", "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_POLICIES", "EMA_ALPHA", "THROUGHPUT_WINDOW_S",
    "POLICIES_SYSTEM_ID", "SCHEMA_VERSION", "VERSION",
    # Enums
    "ConflictResolutionStrategy", "PolicyAction", "PolicyChainMode",
    "PolicyConditionOperator", "PolicyEvaluationStatus", "PolicyEventType",
    "PolicyPriority", "PolicyRuleLogic", "PolicyStatus", "PolicyType",
    "PolicyValidationCode",
    # Exceptions
    "DecisionPolicyError", "PolicyChainError", "PolicyConfigurationError",
    "PolicyConflictError", "PolicyEngineNotRunningError", "PolicyEvaluationError",
    "PolicyNotFoundError", "PolicyRegistryError", "PolicyValidationError",
    # Core types
    "PolicyCondition", "PolicyEvaluationContext", "PolicyPriorityResolver",
    "PolicyEvaluationSummary", "PolicyRuleResult", "SinglePolicyResult",
    "PolicyRule",
    # Policy & request
    "DecisionPolicy", "PolicyEvaluationRequest",
    # Output / audit / events
    "PolicyAuditEntry", "PolicyAuditReport", "build_audit_report",
    "DecisionPolicyEvent",
    "make_policy_approved", "make_policy_blocked", "make_policy_escalated",
    "make_policy_evaluation_completed", "make_policy_evaluation_started",
    "make_policy_loaded", "make_policy_rejected", "make_policy_validated",
    "DecisionPolicyResponse",
    # Services
    "DecisionPolicyChain", "DecisionPolicyEvaluator", "DecisionPolicyFactory",
    "DecisionPolicyHistory", "DecisionPolicyManager", "DecisionPolicyRegistry",
    "DecisionPolicyStatistics", "DecisionPolicyValidator",
    "PolicyValidationCheckResult", "PolicyValidationResult",
    # Engine
    "DecisionPolicyEngine", "PolicyFrameworkAdapter",
]
