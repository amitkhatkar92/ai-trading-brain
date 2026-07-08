"""
iios/intelligence/reasoning/__init__.py
=======================================
Public API for the Reasoning & Debate Engine.
"""
from __future__ import annotations

# ── Constants & enums ─────────────────────────────────────────────────────────
from .reasoning_constants import (
    REASONING_ENGINE_VERSION,
    MAX_DEBATE_ROUNDS,
    MAX_EVIDENCE_ITEMS,
    MAX_REASONING_SESSIONS,
    DEFAULT_SESSION_TIMEOUT_S,
    DEFAULT_DEBATE_TIMEOUT_S,
    CONFIDENCE_THRESHOLD_HIGH,
    CONFIDENCE_THRESHOLD_MODERATE,
    ReasoningType,
    ReasoningStatus,
    EvidenceType,
    EvidenceStrength,
    EvidenceStatus,
    EvidenceRelation,
    DebateRole,
    DebateStatus,
    ArgumentType,
    ConfidenceLevel,
    ExplanationType,
    TraceStepType,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .reasoning_exceptions import (
    ReasoningError,
    ReasoningSessionError,
    SessionNotFoundError,
    SessionAlreadyExistsError,
    SessionTimeoutError,
    SessionStateError,
    EvidenceError,
    EvidenceNotFoundError,
    EvidenceValidationError,
    EvidenceConflictError,
    InsufficientEvidenceError,
    DebateError,
    DebateNotFoundError,
    DebateDeadlockError,
    DebateTimeoutError,
    InsufficientParticipantsError,
    ConfidenceError,
    InsufficientDataForConfidenceError,
    ConfidenceCalculationError,
    ExplanationError,
    ExplanationNotFoundError,
    TraceNotFoundError,
    ReasoningEngineError,
    EngineNotInitializedError,
    EngineAlreadyRunningError,
)

# ── Context ───────────────────────────────────────────────────────────────────
from .reasoning_context import (
    ReasoningContextState,
    ReasoningDiagnostic,
    get_reasoning_context,
    reset_reasoning_context,
    reasoning_session_scope,
    debate_scope,
)

# ── Core models ───────────────────────────────────────────────────────────────
from .reasoning_result  import ReasoningResult, ReasoningOutput
from .reasoning_session import ReasoningSession

# ── Evidence ──────────────────────────────────────────────────────────────────
from .evidence.evidence_registry import (
    Evidence,
    EvidenceRegistry,
    get_evidence_registry,
    reset_evidence_registry,
)
from .evidence.evidence_validator import EvidenceValidator, ValidationResult
from .evidence.evidence_ranker    import EvidenceRanker, RankedEvidence
from .evidence.evidence_graph     import EvidenceGraph, EvidenceNode, EvidenceEdge
from .evidence.evidence_chain     import EvidenceChain, ChainLink
from .evidence.evidence_manager   import (
    EvidenceManager,
    get_evidence_manager,
    reset_evidence_manager,
)

# ── Debate ────────────────────────────────────────────────────────────────────
from .debate.argument         import Argument
from .debate.counter_argument import CounterArgument
from .debate.debate_round     import DebateRound
from .debate.debate_session   import DebateSession, DebateParticipant
from .debate.debate_summary   import DebateSummary
from .debate.debate_engine    import DebateEngine, get_debate_engine, reset_debate_engine
from .debate.debate_manager   import (
    DebateManager,
    ArgumentProviderFn,
    get_debate_manager,
    reset_debate_manager,
)

# ── Confidence ────────────────────────────────────────────────────────────────
from .confidence.confidence_model      import ConfidenceModel, ConfidenceComponent
from .confidence.confidence_report     import ConfidenceReport
from .confidence.confidence_calculator import ConfidenceCalculator
from .confidence.confidence_engine     import (
    ConfidenceEngine,
    get_confidence_engine,
    reset_confidence_engine,
)

# ── Explanation ───────────────────────────────────────────────────────────────
from .explanation.reasoning_trace    import ReasoningTrace, TraceStep
from .explanation.proof_chain        import ProofChain, ProofStep
from .explanation.decision_explanation import DecisionExplanation
from .explanation.explanation_engine import (
    ExplanationEngine,
    get_explanation_engine,
    reset_explanation_engine,
)

# ── Registry / factory ────────────────────────────────────────────────────────
from .reasoning_registry import (
    ReasoningSessionRegistry,
    get_session_registry,
    reset_session_registry,
)
from .reasoning_factory import (
    ReasoningSessionFactory,
    get_reasoning_factory,
    reset_reasoning_factory,
)

# ── Manager & Engine ──────────────────────────────────────────────────────────
from .reasoning_manager import (
    ReasoningManager,
    get_reasoning_manager,
    reset_reasoning_manager,
)
from .reasoning_engine import (
    ReasoningEngine,
    get_reasoning_engine,
    reset_reasoning_engine,
)

__all__ = [
    # Version
    "REASONING_ENGINE_VERSION",
    # Constants
    "MAX_DEBATE_ROUNDS", "MAX_EVIDENCE_ITEMS", "MAX_REASONING_SESSIONS",
    "DEFAULT_SESSION_TIMEOUT_S", "DEFAULT_DEBATE_TIMEOUT_S",
    "CONFIDENCE_THRESHOLD_HIGH", "CONFIDENCE_THRESHOLD_MODERATE",
    # Enums
    "ReasoningType", "ReasoningStatus",
    "EvidenceType", "EvidenceStrength", "EvidenceStatus", "EvidenceRelation",
    "DebateRole", "DebateStatus", "ArgumentType",
    "ConfidenceLevel", "ExplanationType", "TraceStepType",
    # Exceptions
    "ReasoningError", "ReasoningSessionError",
    "SessionNotFoundError", "SessionAlreadyExistsError",
    "SessionTimeoutError", "SessionStateError",
    "EvidenceError", "EvidenceNotFoundError", "EvidenceValidationError",
    "EvidenceConflictError", "InsufficientEvidenceError",
    "DebateError", "DebateNotFoundError", "DebateDeadlockError",
    "DebateTimeoutError", "InsufficientParticipantsError",
    "ConfidenceError", "InsufficientDataForConfidenceError",
    "ConfidenceCalculationError",
    "ExplanationError", "ExplanationNotFoundError", "TraceNotFoundError",
    "ReasoningEngineError", "EngineNotInitializedError", "EngineAlreadyRunningError",
    # Context
    "ReasoningContextState", "ReasoningDiagnostic",
    "get_reasoning_context", "reset_reasoning_context",
    "reasoning_session_scope", "debate_scope",
    # Models
    "ReasoningResult", "ReasoningOutput", "ReasoningSession",
    # Evidence
    "Evidence", "EvidenceRegistry",
    "get_evidence_registry", "reset_evidence_registry",
    "EvidenceValidator", "ValidationResult",
    "EvidenceRanker", "RankedEvidence",
    "EvidenceGraph", "EvidenceNode", "EvidenceEdge",
    "EvidenceChain", "ChainLink",
    "EvidenceManager", "get_evidence_manager", "reset_evidence_manager",
    # Debate
    "Argument", "CounterArgument",
    "DebateRound", "DebateSession", "DebateParticipant", "DebateSummary",
    "DebateEngine", "get_debate_engine", "reset_debate_engine",
    "DebateManager", "ArgumentProviderFn",
    "get_debate_manager", "reset_debate_manager",
    # Confidence
    "ConfidenceModel", "ConfidenceComponent",
    "ConfidenceReport", "ConfidenceCalculator",
    "ConfidenceEngine", "get_confidence_engine", "reset_confidence_engine",
    # Explanation
    "ReasoningTrace", "TraceStep",
    "ProofChain", "ProofStep",
    "DecisionExplanation",
    "ExplanationEngine", "get_explanation_engine", "reset_explanation_engine",
    # Registry / factory
    "ReasoningSessionRegistry", "get_session_registry", "reset_session_registry",
    "ReasoningSessionFactory", "get_reasoning_factory", "reset_reasoning_factory",
    # Manager & engine (public singletons)
    "ReasoningManager", "get_reasoning_manager", "reset_reasoning_manager",
    "ReasoningEngine", "get_reasoning_engine", "reset_reasoning_engine",
]
