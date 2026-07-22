"""
iios.portfolio.optimization
============================
Institutional Portfolio Optimization Framework.

This package selects the optimal institutional portfolio from
policy-approved portfolio candidates.  It performs portfolio
optimization using institutional objectives, allocation strategies,
constraints, and optimization models.

It performs NO policy evaluation, NO trade execution, and
NO broker communication.

Public API
----------
Primary entry-point:
    PortfolioOptimizationEngine

Domain objects:
    PortfolioCandidate, PortfolioObjective, PortfolioConstraint
    PortfolioSolution, AllocationPlan, RebalancingPlan
    PortfolioOptimizationRequest, PortfolioOptimizationResponse
    PortfolioOptimizationStrategy, OptimizationContext
    PortfolioOptimizationSummary

Results and introspection:
    OptimizationEngineStatus, OptimizationStatisticsSnapshot
    OptimizationEngineEvent, SolutionValidationResult

Factories:
    PortfolioOptimizationFactory

Enumerations:
    OptimizationObjective, OptimizationStrategyType, ConstraintType
    AllocationCapability, RebalancingCapability, ScoringMethod
    OptimizationEventType, OptimizationStatus, CandidateStatus
    StrategyStatus

Exceptions:
    PortfolioOptimizationError
    PortfolioOptimizationNotRunningError
    PortfolioOptimizationNotFoundError
    PortfolioOptimizationConfigurationError
    PortfolioOptimizationValidationError
    PortfolioOptimizationSolutionError
    PortfolioOptimizationConstraintError
    PortfolioOptimizationStrategyError
    PortfolioOptimizationCapacityError
    PortfolioOptimizationCandidateError

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from .constants import (
    OPTIMIZATION_SYSTEM_ID,
    VERSION,
    AllocationCapability,
    CandidateStatus,
    ConstraintType,
    OptimizationEventType,
    OptimizationObjective,
    OptimizationStatus,
    OptimizationStrategyType,
    RebalancingCapability,
    ScoringMethod,
    StrategyStatus,
)
from .exceptions import (
    PortfolioOptimizationCandidateError,
    PortfolioOptimizationCapacityError,
    PortfolioOptimizationConfigurationError,
    PortfolioOptimizationConstraintError,
    PortfolioOptimizationError,
    PortfolioOptimizationNotFoundError,
    PortfolioOptimizationNotRunningError,
    PortfolioOptimizationSolutionError,
    PortfolioOptimizationStrategyError,
    PortfolioOptimizationValidationError,
)
from .portfolio_candidate import PortfolioCandidate
from .portfolio_candidate_registry import PortfolioCandidateRegistry
from .portfolio_constraint import ConstraintResult, PortfolioConstraint
from .portfolio_constraint_engine import PortfolioConstraintEngine
from .portfolio_objective import ObjectiveResult, PortfolioObjective
from .portfolio_optimization_context import OptimizationContext
from .portfolio_optimization_engine import (
    OptimizationEngineStatus,
    PortfolioOptimizationEngine,
)
from .portfolio_optimization_events import (
    OptimizationEngineEvent,
    make_allocation_generated,
    make_candidates_loaded,
    make_constraints_loaded,
    make_objectives_loaded,
    make_optimization_completed,
    make_optimization_failed,
    make_optimization_started,
    make_portfolio_selected,
    make_rebalancing_generated,
    make_solution_validated,
)
from .portfolio_optimization_factory import PortfolioOptimizationFactory
from .portfolio_optimization_history import PortfolioOptimizationHistory
from .portfolio_optimization_manager import PortfolioOptimizationManager
from .portfolio_optimization_registry import PortfolioOptimizationRegistry
from .portfolio_optimization_request import PortfolioOptimizationRequest
from .portfolio_optimization_response import PortfolioOptimizationResponse
from .portfolio_optimization_statistics import (
    OptimizationStatisticsSnapshot,
    PortfolioOptimizationStatistics,
)
from .portfolio_optimization_strategy import PortfolioOptimizationStrategy
from .portfolio_optimizer import PortfolioOptimizer
from .portfolio_solution import (
    AllocationPlan,
    PortfolioOptimizationSummary,
    PortfolioSolution,
    RebalancingPlan,
)
from .portfolio_solution_selector import PortfolioSolutionSelector
from .portfolio_solution_validator import (
    PortfolioSolutionValidator,
    SolutionValidationResult,
)
from .portfolio_strategy_registry import PortfolioStrategyRegistry

__all__ = [
    # Engine
    "PortfolioOptimizationEngine",
    "OptimizationEngineStatus",
    # Domain objects
    "PortfolioCandidate",
    "PortfolioObjective",
    "ObjectiveResult",
    "PortfolioConstraint",
    "ConstraintResult",
    "PortfolioOptimizationStrategy",
    "AllocationPlan",
    "RebalancingPlan",
    "PortfolioSolution",
    "PortfolioOptimizationSummary",
    "PortfolioOptimizationRequest",
    "PortfolioOptimizationResponse",
    "OptimizationContext",
    "SolutionValidationResult",
    # Statistics
    "OptimizationStatisticsSnapshot",
    # Events
    "OptimizationEngineEvent",
    "make_optimization_started",
    "make_candidates_loaded",
    "make_objectives_loaded",
    "make_constraints_loaded",
    "make_allocation_generated",
    "make_rebalancing_generated",
    "make_optimization_completed",
    "make_portfolio_selected",
    "make_solution_validated",
    "make_optimization_failed",
    # Factory
    "PortfolioOptimizationFactory",
    # Registries
    "PortfolioCandidateRegistry",
    "PortfolioStrategyRegistry",
    "PortfolioOptimizationRegistry",
    # Engines
    "PortfolioConstraintEngine",
    "PortfolioSolutionSelector",
    "PortfolioSolutionValidator",
    "PortfolioOptimizer",
    # Enumerations
    "OptimizationObjective",
    "OptimizationStrategyType",
    "ConstraintType",
    "AllocationCapability",
    "RebalancingCapability",
    "ScoringMethod",
    "OptimizationEventType",
    "OptimizationStatus",
    "CandidateStatus",
    "StrategyStatus",
    # Constants
    "OPTIMIZATION_SYSTEM_ID",
    "VERSION",
    # Exceptions
    "PortfolioOptimizationError",
    "PortfolioOptimizationNotRunningError",
    "PortfolioOptimizationNotFoundError",
    "PortfolioOptimizationConfigurationError",
    "PortfolioOptimizationValidationError",
    "PortfolioOptimizationSolutionError",
    "PortfolioOptimizationConstraintError",
    "PortfolioOptimizationStrategyError",
    "PortfolioOptimizationCapacityError",
    "PortfolioOptimizationCandidateError",
]
