"""iios/ontology/reasoning/__init__.py — Public API for the IIOS Reasoning Engine."""

# Constants & enums
from .reasoning_constants import (
    ReasoningType,
    InferenceStatus,
    ConsistencyStatus,
    ExplanationType,
    RuleType,
    ReasoningPhase,
    IssueSeverity,
    IssueType,
    CONFIDENCE_CERTAIN,
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_LOW,
    CONFIDENCE_SPECULATIVE,
    PRED_SUBTYPE_OF,
    PRED_TRANSITIVE_SUBTYPE,
    PRED_INHERITS_PROPERTY,
    PRED_HAS_OWN_PROPERTY,
    PRED_RELATED_TO,
    PRED_INVERSE_RELATED,
    PRED_IS_CONSISTENT,
    PRED_HAS_NAMESPACE,
    PRED_APPLIES_TO_SUBTYPE,
    MAX_INFERENCE_DEPTH,
    MAX_FIXPOINT_ITERATIONS,
    MAX_RULES,
    MAX_FACTS_PER_SESSION,
    REASONING_TIMEOUT_MS,
    SESSION_TTL_SECONDS,
    MAX_SESSIONS,
    PROOF_MAX_STEPS,
    REASONING_ENGINE_VERSION,
    SYSTEM_REASONING_ACTOR,
    RULE_INHERITANCE_PROPAGATION,
    RULE_SUBTYPE_TRANSITIVITY,
    RULE_SYMMETRIC_RELATIONSHIP,
    RULE_TYPE_CONSISTENCY,
    RULE_NAMESPACE_CONSISTENCY,
    RULE_REFERENCE_VALIDITY,
    RULE_ABSTRACT_TYPE_CHECK,
    RULE_ORPHAN_TYPE_CHECK,
    RULE_REL_ENDPOINT_CHECK,
)

# Exceptions
from .reasoning_exceptions import (
    ReasoningError,
    InferenceError,
    InferenceTimeoutError,
    InferenceDepthError,
    InferenceCycleError,
    ConsistencyError,
    OntologyInconsistencyError,
    ReasoningConstraintError,
    ConflictError,
    RuleError,
    DuplicateRuleError,
    UnknownRuleError,
    RuleExecutionError,
    ExplanationError,
    SessionError,
    SessionNotFoundError,
    SessionExpiredError,
    ReasoningEngineError,
    ReasoningNotInitializedError,
)

# Result models
from .reasoning_result import (
    InferredFact,
    ConsistencyIssue,
    FactStore,
    ReasoningResult,
)

# Trace
from .reasoning_trace import (
    TraceEntry,
    ReasoningTrace,
)

# Context
from .reasoning_context import (
    ReasoningContext,
    get_reasoning_context,
    reset_reasoning_context,
)

# Factory
from .reasoning_factory import (
    ReasoningRequest,
    ReasoningResponse,
    ReasoningFactory,
    get_reasoning_factory,
    reset_reasoning_factory,
)

# Session
from .reasoning_session import (
    ReasoningSession,
    SessionManager,
    get_session_manager,
    reset_session_manager,
)

# Statistics
from .reasoning_statistics import (
    ReasoningStats,
    get_reasoning_statistics,
    reset_reasoning_statistics,
)

# Registry
from .reasoning_registry import (
    ReasoningModule,
    ReasoningModuleRegistry,
    get_reasoning_registry,
    reset_reasoning_registry,
)

# Inference sub-package
from .inference import (
    InferenceRule,
    InferenceRegistry,
    get_inference_registry,
    reset_inference_registry,
    InferenceGraph,
    InferenceNode,
    InferenceEdge,
    InferenceExecutor,
    get_inference_executor,
    reset_inference_executor,
    InferenceEngine,
    get_inference_engine_instance,
    reset_inference_engine_instance,
)

# Explanation sub-package
from .explanation import (
    DecisionTrace,
    ProofNode,
    ProofGenerator,
    get_proof_generator,
    reset_proof_generator,
    ReasoningExplainer,
    get_reasoning_explainer,
    reset_reasoning_explainer,
    ExplanationEngine,
    get_explanation_engine,
    reset_explanation_engine,
)

# Manager
from .reasoning_manager import (
    ReasoningManager,
    get_reasoning_manager,
    reset_reasoning_manager,
)

# Master facade
from .reasoning_engine import (
    ReasoningEngine,
    get_reasoning_engine,
    reset_reasoning_engine,
)

__all__ = [
    # constants
    "ReasoningType", "InferenceStatus", "ConsistencyStatus",
    "ExplanationType", "RuleType", "ReasoningPhase",
    "IssueSeverity", "IssueType",
    "CONFIDENCE_CERTAIN", "CONFIDENCE_HIGH", "CONFIDENCE_MEDIUM",
    "CONFIDENCE_LOW", "CONFIDENCE_SPECULATIVE",
    "PRED_SUBTYPE_OF", "PRED_TRANSITIVE_SUBTYPE", "PRED_INHERITS_PROPERTY",
    "PRED_HAS_OWN_PROPERTY", "PRED_RELATED_TO", "PRED_INVERSE_RELATED",
    "PRED_IS_CONSISTENT", "PRED_HAS_NAMESPACE", "PRED_APPLIES_TO_SUBTYPE",
    "MAX_INFERENCE_DEPTH", "MAX_FIXPOINT_ITERATIONS", "MAX_RULES",
    "MAX_FACTS_PER_SESSION", "REASONING_TIMEOUT_MS", "SESSION_TTL_SECONDS",
    "MAX_SESSIONS", "PROOF_MAX_STEPS",
    "REASONING_ENGINE_VERSION", "SYSTEM_REASONING_ACTOR",
    "RULE_INHERITANCE_PROPAGATION", "RULE_SUBTYPE_TRANSITIVITY",
    "RULE_SYMMETRIC_RELATIONSHIP", "RULE_TYPE_CONSISTENCY",
    "RULE_NAMESPACE_CONSISTENCY", "RULE_REFERENCE_VALIDITY",
    "RULE_ABSTRACT_TYPE_CHECK", "RULE_ORPHAN_TYPE_CHECK", "RULE_REL_ENDPOINT_CHECK",
    # exceptions
    "ReasoningError", "InferenceError", "InferenceTimeoutError",
    "InferenceDepthError", "InferenceCycleError", "ConsistencyError",
    "OntologyInconsistencyError", "ReasoningConstraintError", "ConflictError",
    "RuleError", "DuplicateRuleError", "UnknownRuleError", "RuleExecutionError",
    "ExplanationError", "SessionError", "SessionNotFoundError",
    "SessionExpiredError", "ReasoningEngineError", "ReasoningNotInitializedError",
    # results
    "InferredFact", "ConsistencyIssue", "FactStore", "ReasoningResult",
    "TraceEntry", "ReasoningTrace",
    # context
    "ReasoningContext", "get_reasoning_context", "reset_reasoning_context",
    # factory
    "ReasoningRequest", "ReasoningResponse",
    "ReasoningFactory", "get_reasoning_factory", "reset_reasoning_factory",
    # session
    "ReasoningSession", "SessionManager", "get_session_manager", "reset_session_manager",
    # statistics
    "ReasoningStats", "get_reasoning_statistics", "reset_reasoning_statistics",
    # module registry
    "ReasoningModule", "ReasoningModuleRegistry",
    "get_reasoning_registry", "reset_reasoning_registry",
    # inference
    "InferenceRule",
    "InferenceRegistry", "get_inference_registry", "reset_inference_registry",
    "InferenceGraph", "InferenceNode", "InferenceEdge",
    "InferenceExecutor", "get_inference_executor", "reset_inference_executor",
    "InferenceEngine", "get_inference_engine_instance", "reset_inference_engine_instance",
    # explanation
    "DecisionTrace",
    "ProofNode", "ProofGenerator", "get_proof_generator", "reset_proof_generator",
    "ReasoningExplainer", "get_reasoning_explainer", "reset_reasoning_explainer",
    "ExplanationEngine", "get_explanation_engine", "reset_explanation_engine",
    # manager & engine
    "ReasoningManager", "get_reasoning_manager", "reset_reasoning_manager",
    "ReasoningEngine", "get_reasoning_engine", "reset_reasoning_engine",
]
