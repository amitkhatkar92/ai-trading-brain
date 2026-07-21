"""
iios.decision.optimization
==========================
Decision Optimization Framework — C9 Decision Intelligence, Phase 1, Module 4.

Selects the optimal institutional decision from policy-approved candidates
using multi-objective optimization, configurable constraints, priorities,
and optimization strategies.

This framework:
  - DOES     evaluate, score, rank, and select candidate decisions
  - DOES NOT evaluate institutional policies
  - DOES NOT execute trades or place orders
  - DOES NOT modify portfolios
  - DOES NOT communicate with brokers

Primary entry point: :class:`DecisionOptimizationEngine`
M2 bridge:           :class:`OptimizationFrameworkAdapter`
"""

# ── Constants ──────────────────────────────────────────────────────────────
from .constants import (
    ACTOR_ENGINE,
    ACTOR_MANAGER,
    ACTOR_OPERATOR,
    ACTOR_OPTIMIZER,
    ACTOR_SYSTEM,
    DEFAULT_MAX_CANDIDATES,
    DEFAULT_MAX_CONSTRAINTS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_OBJECTIVES,
    DEFAULT_MAX_STRATEGIES,
    DEFAULT_STRATEGY_ID,
    EMA_ALPHA,
    MAXIMIZE_OBJECTIVES,
    MINIMIZE_OBJECTIVES,
    OBJECTIVE_FIELD_DEFAULTS,
    OPTIMIZATION_SYSTEM_ID,
    SCHEMA_VERSION,
    THROUGHPUT_WINDOW_S,
    VERSION,
    ConstraintOperator,
    ConstraintType,
    OptimizationEventType,
    OptimizationObjectiveType,
    OptimizationStatus,
    OptimizationStrategyType,
    OptimizationValidationCode,
)

# ── Exceptions ────────────────────────────────────────────────────────────
from .exceptions import (
    CandidateRegistryError,
    ConstraintNotFoundError,
    DecisionOptimizationError,
    NoCandidatesError,
    NoFeasibleSolutionError,
    ObjectiveNotFoundError,
    OptimizationConfigurationError,
    OptimizationEngineNotRunningError,
    OptimizationValidationError,
    StrategyNotFoundError,
)

# ── Core value objects ────────────────────────────────────────────────────
from .decision_candidate import CandidateScore, DecisionCandidate
from .decision_constraint import (
    ConstraintCheckResult,
    ConstraintEvaluationResult,
    DecisionConstraint,
)
from .decision_objective import DecisionObjective
from .decision_optimization_context import DecisionOptimizationContext
from .decision_optimization_strategy import DecisionOptimizationStrategy
from .decision_optimization_request import DecisionOptimizationRequest
from .decision_optimization_response import (
    DecisionOptimizationResponse,
    DecisionOptimizationSummary,
    OptimizationReport,
)
from .decision_ranking_engine import DecisionRanking
from .decision_solution import DecisionSolution
from .decision_optimization_events import (
    DecisionOptimizationEvent,
    make_candidates_loaded,
    make_constraints_loaded,
    make_objectives_loaded,
    make_optimization_completed,
    make_optimization_failed,
    make_optimization_started,
    make_solution_selected,
    make_solution_validated,
)

# ── Internal engines ──────────────────────────────────────────────────────
from .decision_candidate_registry import DecisionCandidateRegistry
from .decision_constraint_engine import DecisionConstraintEngine
from .decision_scoring_engine import DecisionScoringEngine
from .decision_ranking_engine import DecisionRankingEngine
from .decision_priority_engine import DecisionPriorityEngine
from .decision_solution_selector import DecisionSolutionSelector
from .decision_solution_validator import (
    DecisionSolutionValidator,
    SolutionValidationCheckResult,
    SolutionValidationResult,
)
from .decision_optimizer import DecisionOptimizer

# ── Registries ────────────────────────────────────────────────────────────
from .decision_optimization_registry import DecisionOptimizationRegistry
from .decision_strategy_registry import DecisionStrategyRegistry

# ── Observability ─────────────────────────────────────────────────────────
from .decision_optimization_history import DecisionOptimizationHistory
from .decision_optimization_statistics import DecisionOptimizationStatistics

# ── Factory ───────────────────────────────────────────────────────────────
from .decision_optimization_factory import DecisionOptimizationFactory

# ── Manager ───────────────────────────────────────────────────────────────
from .decision_optimization_manager import DecisionOptimizationManager

# ── Engine (primary interface) ────────────────────────────────────────────
from .decision_optimization_engine import (
    DecisionOptimizationEngine,
    OptimizationFrameworkAdapter,
)

__all__ = [
    # Constants
    "ACTOR_ENGINE",
    "ACTOR_MANAGER",
    "ACTOR_OPERATOR",
    "ACTOR_OPTIMIZER",
    "ACTOR_SYSTEM",
    "DEFAULT_MAX_CANDIDATES",
    "DEFAULT_MAX_CONSTRAINTS",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_OBJECTIVES",
    "DEFAULT_MAX_STRATEGIES",
    "DEFAULT_STRATEGY_ID",
    "EMA_ALPHA",
    "MAXIMIZE_OBJECTIVES",
    "MINIMIZE_OBJECTIVES",
    "OBJECTIVE_FIELD_DEFAULTS",
    "OPTIMIZATION_SYSTEM_ID",
    "SCHEMA_VERSION",
    "THROUGHPUT_WINDOW_S",
    "VERSION",
    "ConstraintOperator",
    "ConstraintType",
    "OptimizationEventType",
    "OptimizationObjectiveType",
    "OptimizationStatus",
    "OptimizationStrategyType",
    "OptimizationValidationCode",
    # Exceptions
    "CandidateRegistryError",
    "ConstraintNotFoundError",
    "DecisionOptimizationError",
    "NoCandidatesError",
    "NoFeasibleSolutionError",
    "ObjectiveNotFoundError",
    "OptimizationConfigurationError",
    "OptimizationEngineNotRunningError",
    "OptimizationValidationError",
    "StrategyNotFoundError",
    # Value objects
    "CandidateScore",
    "ConstraintCheckResult",
    "ConstraintEvaluationResult",
    "DecisionCandidate",
    "DecisionConstraint",
    "DecisionObjective",
    "DecisionOptimizationContext",
    "DecisionOptimizationEvent",
    "DecisionOptimizationRequest",
    "DecisionOptimizationResponse",
    "DecisionOptimizationSummary",
    "DecisionOptimizationStrategy",
    "DecisionRanking",
    "DecisionSolution",
    "OptimizationReport",
    # Engines
    "DecisionCandidateRegistry",
    "DecisionConstraintEngine",
    "DecisionOptimizer",
    "DecisionPriorityEngine",
    "DecisionRankingEngine",
    "DecisionScoringEngine",
    "DecisionSolutionSelector",
    "DecisionSolutionValidator",
    # Registries
    "DecisionOptimizationRegistry",
    "DecisionStrategyRegistry",
    # Observability
    "DecisionOptimizationFactory",
    "DecisionOptimizationHistory",
    "DecisionOptimizationStatistics",
    # Manager + Engine
    "DecisionOptimizationManager",
    "DecisionOptimizationEngine",
    "OptimizationFrameworkAdapter",
    # Event factories
    "make_candidates_loaded",
    "make_constraints_loaded",
    "make_objectives_loaded",
    "make_optimization_completed",
    "make_optimization_failed",
    "make_optimization_started",
    "make_solution_selected",
    "make_solution_validated",
    # Validation detail
    "SolutionValidationCheckResult",
    "SolutionValidationResult",
]
