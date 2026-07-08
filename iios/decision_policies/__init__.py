"""iios/decision_policies/__init__.py — Decision Policy & Rule Engine public API."""
from __future__ import annotations

# ── Constants & enumerations ───────────────────────────────────────────────────
from .policy_constants import (
    ComplianceCategory,
    ConflictResolution,
    ConstraintType,
    DEFAULT_RULE_PRIORITY,
    EvaluationMode,
    GroupOperator,
    POLICY_ENGINE_SYSTEM_ID,
    POLICY_ENGINE_VERSION,
    PolicyPriority,
    PolicyVerdict,
    RuleStatus,
    RuleType,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .policy_exceptions import (
    CircularRuleDependencyError,
    ComplianceError,
    CompliancePolicyNotFoundError,
    CompliancePolicyViolationError,
    ConstraintAlreadyExistsError,
    ConstraintError,
    ConstraintNotFoundError,
    ConstraintViolationError,
    EngineAlreadyRunningError,
    EngineLifecycleError,
    EngineNotInitializedError,
    EvaluationError,
    EvaluationFailedError,
    InvalidOverrideError,
    NoApplicablePoliciesError,
    OverrideError,
    PolicyAlreadyExistsError,
    PolicyConflictError,
    PolicyDisabledError,
    PolicyEngineError,
    PolicyError,
    PolicyNotFoundError,
    RegistryError,
    RegistryOverflowError,
    RuleAlreadyExistsError,
    RuleDependencyError,
    RuleError,
    RuleExecutionError,
    RuleNotFoundError,
    UnauthorizedOverrideError,
)

# ── Context ───────────────────────────────────────────────────────────────────
from .policy_context import (
    EvaluationContext,
    PolicyContextState,
    PolicyDiagnostic,
    evaluation_scope,
    get_policy_context,
    policy_stage_scope,
    reset_policy_context,
)

# ── Rules ─────────────────────────────────────────────────────────────────────
from .rules.rule import (
    CompositeRule,
    ConditionalRule,
    DynamicRule,
    PriorityRule,
    Rule,
    StaticRule,
)
from .rules.rule_engine import RuleEngine
from .rules.rule_executor import RuleExecutor
from .rules.rule_group import RuleGroup
from .rules.rule_registry import RuleRegistry, get_rule_registry, reset_rule_registry
from .rules.rule_result import RuleGroupResult, RuleResult

# ── Constraints ───────────────────────────────────────────────────────────────
from .constraints.constraint import (
    BoundedConstraint,
    Constraint,
    HardConstraint,
    SoftConstraint,
    StaticConstraint,
    ThresholdConstraint,
)
from .constraints.constraint_engine import ConstraintEngine
from .constraints.constraint_registry import (
    ConstraintRegistry,
    get_constraint_registry,
    reset_constraint_registry,
)
from .constraints.constraint_result import ConstraintResult
from .constraints.constraint_validator import ConstraintValidator

# ── Compliance ────────────────────────────────────────────────────────────────
from .compliance.compliance_engine import ComplianceEngine
from .compliance.compliance_policy import CompliancePolicy, ComplianceResult, StaticCompliancePolicy
from .compliance.compliance_report import ComplianceReport, build_compliance_report
from .compliance.compliance_validator import ComplianceValidator

# ── Evaluation ────────────────────────────────────────────────────────────────
from .evaluation.conflict_detector import ConflictDetector
from .evaluation.policy_evaluator import (
    PolicyEvaluationRequest,
    PolicyEvaluationResult,
    PolicyEvaluator,
)

# ── Registry ──────────────────────────────────────────────────────────────────
from .registry.policy_registry import PolicyRegistry, get_policy_registry, reset_policy_registry

# ── Factory ───────────────────────────────────────────────────────────────────
from .policy_factory import PolicyFactory

# ── Manager & Engine ──────────────────────────────────────────────────────────
from .policy_manager import PolicyManager, get_policy_manager, reset_policy_manager
from .decision_policy_engine import (
    DecisionPolicyEngine,
    get_decision_policy_engine,
    reset_decision_policy_engine,
)

__version__ = POLICY_ENGINE_VERSION
__status__  = "production"
__layer__   = "LAYER-10-POLICY"

__all__ = [
    # Constants
    "RuleStatus", "RuleType", "GroupOperator", "ConstraintType",
    "ComplianceCategory", "PolicyVerdict", "EvaluationMode",
    "PolicyPriority", "ConflictResolution", "POLICY_ENGINE_VERSION",
    # Exceptions
    "PolicyEngineError", "PolicyError", "PolicyNotFoundError", "PolicyAlreadyExistsError",
    "RuleNotFoundError", "RuleExecutionError", "RuleDependencyError",
    "CircularRuleDependencyError", "RuleAlreadyExistsError",
    "ConstraintViolationError", "ConstraintNotFoundError", "ConstraintAlreadyExistsError",
    "CompliancePolicyViolationError", "CompliancePolicyNotFoundError",
    "EngineNotInitializedError", "EngineAlreadyRunningError",
    "NoApplicablePoliciesError", "PolicyConflictError",
    # Context
    "EvaluationContext", "evaluation_scope", "policy_stage_scope",
    # Rules
    "Rule", "StaticRule", "DynamicRule", "ConditionalRule", "CompositeRule", "PriorityRule",
    "RuleGroup", "RuleResult", "RuleGroupResult",
    "RuleRegistry", "get_rule_registry", "reset_rule_registry",
    "RuleEngine", "RuleExecutor",
    # Constraints
    "Constraint", "HardConstraint", "SoftConstraint",
    "StaticConstraint", "BoundedConstraint", "ThresholdConstraint",
    "ConstraintResult", "ConstraintEngine", "ConstraintValidator",
    "get_constraint_registry", "reset_constraint_registry",
    # Compliance
    "CompliancePolicy", "StaticCompliancePolicy", "ComplianceResult",
    "ComplianceReport", "ComplianceEngine", "build_compliance_report",
    # Evaluation
    "PolicyEvaluationRequest", "PolicyEvaluationResult", "PolicyEvaluator",
    "ConflictDetector",
    # Registry
    "PolicyRegistry", "get_policy_registry", "reset_policy_registry",
    # Factory
    "PolicyFactory",
    # Manager & Engine
    "PolicyManager", "get_policy_manager", "reset_policy_manager",
    "DecisionPolicyEngine", "get_decision_policy_engine", "reset_decision_policy_engine",
]
