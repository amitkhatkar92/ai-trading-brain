"""
iios/decisions/__init__.py
===========================
Public API for the Decision Engine Core (IIOS Decision Layer).

No investment action shall be produced by IIOS without passing through
the DecisionEngine gateway.
"""
from __future__ import annotations

# ── Constants & enums ─────────────────────────────────────────────────────────
from .decision_constants import (
    DecisionType,
    DecisionStatus,
    DecisionPriority,
    CandidateStatus,
    WorkflowStage,
    PolicyOutcome,
    DecisionDimension,
    DECISION_ENGINE_VERSION,
    MAX_DECISION_RECORDS,
    MAX_CANDIDATES_PER_REQUEST,
    DEFAULT_DECISION_TTL_S,
    MIN_CONFIDENCE_THRESHOLD,
    DEFAULT_DIMENSION_WEIGHTS,
    DECISION_ENGINE_SYSTEM_ID,
    DECISION_AUTO_SELECTOR_ID,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .decision_exceptions import (
    DecisionEngineError,
    DecisionError,
    DecisionNotFoundError,
    DecisionAlreadyExistsError,
    DecisionExpiredError,
    DecisionCancelledError,
    DecisionRequestError,
    InvalidDecisionRequestError,
    MissingDecisionContextError,
    PolicyError,
    PolicyViolationError,
    NoPoliciesDefinedError,
    PolicyConflictError,
    EvaluationError,
    NoCandidatesError,
    EvaluationFailedError,
    ScoringError,
    WorkflowError,
    WorkflowStageFailedError,
    WorkflowAbortedError,
    RegistryError,
    RegistryOverflowError,
    EngineLifecycleError,
    EngineNotInitializedError,
    EngineAlreadyRunningError,
)

# ── Models ────────────────────────────────────────────────────────────────────
from .models.decision_option import DecisionOption
from .models.decision_candidate import DecisionCandidate, PolicyResult
from .models.decision_metadata import DecisionMetadata
from .models.decision_request import DecisionRequest
from .models.decision import Decision
from .models.decision_result import DecisionResult, StageRecord
from .models.decision_statistics import DecisionStatistics
from .models.decision_history import DecisionHistory

# ── Policies ──────────────────────────────────────────────────────────────────
from .policies.decision_policy import (
    DecisionPolicy,
    MinConfidencePolicy,
    MaxRiskPolicy,
    RequireEvidencePolicy,
    MinCandidatesPolicy,
    NotExpiredRequestPolicy,
    AllowlistTypePolicy,
)

# ── Engine & manager ──────────────────────────────────────────────────────────
from .core.decision_engine import (
    DecisionEngine,
    get_decision_engine,
    reset_decision_engine,
)
from .core.decision_manager import (
    DecisionManager,
    get_decision_manager,
    reset_decision_manager,
)

__version__   = DECISION_ENGINE_VERSION
__status__    = "production"
__layer__     = "LAYER-10"

__all__ = [
    # enums / constants
    "DecisionType", "DecisionStatus", "DecisionPriority", "CandidateStatus",
    "WorkflowStage", "PolicyOutcome", "DecisionDimension",
    "DECISION_ENGINE_VERSION", "MAX_DECISION_RECORDS", "MAX_CANDIDATES_PER_REQUEST",
    "DEFAULT_DECISION_TTL_S", "MIN_CONFIDENCE_THRESHOLD", "DEFAULT_DIMENSION_WEIGHTS",
    "DECISION_ENGINE_SYSTEM_ID", "DECISION_AUTO_SELECTOR_ID",
    # exceptions
    "DecisionEngineError", "DecisionError", "DecisionNotFoundError",
    "DecisionAlreadyExistsError", "DecisionExpiredError", "DecisionCancelledError",
    "DecisionRequestError", "InvalidDecisionRequestError", "MissingDecisionContextError",
    "PolicyError", "PolicyViolationError", "NoPoliciesDefinedError", "PolicyConflictError",
    "EvaluationError", "NoCandidatesError", "EvaluationFailedError", "ScoringError",
    "WorkflowError", "WorkflowStageFailedError", "WorkflowAbortedError",
    "RegistryError", "RegistryOverflowError",
    "EngineLifecycleError", "EngineNotInitializedError", "EngineAlreadyRunningError",
    # models
    "DecisionOption", "DecisionCandidate", "PolicyResult", "DecisionMetadata",
    "DecisionRequest", "Decision", "DecisionResult", "StageRecord",
    "DecisionStatistics", "DecisionHistory",
    # policies
    "DecisionPolicy", "MinConfidencePolicy", "MaxRiskPolicy",
    "RequireEvidencePolicy", "MinCandidatesPolicy", "NotExpiredRequestPolicy",
    "AllowlistTypePolicy",
    # engine
    "DecisionEngine", "get_decision_engine", "reset_decision_engine",
    "DecisionManager", "get_decision_manager", "reset_decision_manager",
]

