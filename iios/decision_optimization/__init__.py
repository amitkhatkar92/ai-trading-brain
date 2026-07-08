"""
iios/decision_optimization/__init__.py
Decision Optimization Engine — public API.
"""
from __future__ import annotations

from .optimization_constants import (
    AlgorithmType,
    ConstraintType,
    DEFAULT_ALGORITHM_TYPE,
    DEFAULT_OBJECTIVE_WEIGHT,
    DEFAULT_OPTIMIZATION_MODE,
    DEFAULT_SENSITIVITY_STEPS,
    DEFAULT_SIMULATION_TRIALS,
    MAX_ALGORITHMS_IN_REGISTRY,
    MAX_CANDIDATES_PER_REQUEST,
    MAX_OBJECTIVES_PER_REQUEST,
    MAX_OPTIMIZATION_HISTORY,
    ObjectiveAggregation,
    ObjectiveType,
    OptimizationMode,
    OptimizationStatus,
    OPTIMIZATION_ENGINE_SYSTEM_ID,
    OPTIMIZATION_ENGINE_VERSION,
)
from .optimization_exceptions import (
    AlgorithmError,
    AlgorithmExecutionError,
    AlgorithmNotFoundError,
    CandidateError,
    CandidateNotFoundError,
    ConstraintAlreadyExistsError,
    ConstraintError,
    ConstraintNotFoundError,
    ConstraintViolationError,
    EngineAlreadyRunningError,
    EngineLifecycleError,
    EngineNotInitializedError,
    InfeasibleSolutionError,
    InsufficientCandidatesError,
    InvalidObjectiveError,
    ObjectiveAlreadyExistsError,
    ObjectiveError,
    ObjectiveEvaluationError,
    ObjectiveNotFoundError,
    OptimizationAlreadyExistsError,
    OptimizationEngineError,
    OptimizationError,
    OptimizationFailedError,
    OptimizationNotFoundError,
    RegistryError,
    RegistryOverflowError,
    ScenarioNotFoundError,
    SimulationError,
    SimulationFailedError,
    UnsupportedAlgorithmError,
)
from .optimization_context import (
    Candidate,
    OptDiagnostic,
    OptimizationContextState,
    get_optimization_context,
    opt_stage_scope,
    optimization_session,
    reset_optimization_context,
)
from .objectives.objective import (
    CompositeObjective,
    Objective,
    PayloadObjective,
    ScoreObjective,
)
from .objectives.objective_function import FunctionObjective
from .objectives.objective_manager import ObjectiveManager
from .objectives.objective_registry import (
    ObjectiveRegistry,
    get_objective_registry,
    reset_objective_registry,
)
from .objectives.objective_result import (
    ObjectiveResult,
    ObjectiveScore,
    build_objective_result,
)
from .constraints.constraint_checker import (
    BoundedConstraint,
    ConstraintCheckResult,
    OptimizationConstraint,
    PredicateConstraint,
    ThresholdConstraint,
)
from .constraints.constraint_optimizer import (
    ConstraintOptimizer,
    get_constraint_optimizer,
    reset_constraint_optimizer,
)
from .constraints.constraint_report import ConstraintReport, build_constraint_report
from .constraints.constraint_solver import ConstraintSolver
from .algorithms.optimization_algorithm import (
    ConstraintSatisfactionOptimizer,
    GreedyOptimizer,
    MultiObjectiveOptimizer,
    OptimizationAlgorithm,
    OptimizationSolution,
    WeightedSumOptimizer,
)
from .algorithms.algorithm_executor import AlgorithmExecutor
from .algorithms.algorithm_registry import (
    AlgorithmRegistry,
    get_algorithm_registry,
    reset_algorithm_registry,
)
from .algorithms.algorithm_selector import AlgorithmSelector
from .simulation.simulation_engine import SimulationEngine
from .simulation.scenario_optimizer import Scenario, ScenarioOptimizer, ScenarioResult
from .simulation.sensitivity_analyzer import SensitivityAnalyzer
from .simulation.robustness_evaluator import RobustnessEvaluator
from .optimization_registry import (
    OptimizationRegistry,
    get_optimization_registry,
    reset_optimization_registry,
)
from .optimization_manager import (
    OptimizationManager,
    OptimizationRequest,
    OptimizationResult,
    get_optimization_manager,
    reset_optimization_manager,
)
from .optimization_factory import OptimizationFactory
from .decision_optimization_engine import (
    DecisionOptimizationEngine,
    get_decision_optimization_engine,
    reset_decision_optimization_engine,
)

__version__ = OPTIMIZATION_ENGINE_VERSION

__all__ = [
    # Constants / enums
    "ObjectiveType", "ObjectiveAggregation", "ConstraintType",
    "OptimizationStatus", "AlgorithmType", "OptimizationMode",
    "OPTIMIZATION_ENGINE_VERSION", "OPTIMIZATION_ENGINE_SYSTEM_ID",
    # Exceptions
    "OptimizationEngineError", "OptimizationError",
    "OptimizationNotFoundError", "OptimizationAlreadyExistsError", "OptimizationFailedError",
    "ObjectiveError", "ObjectiveNotFoundError", "ObjectiveAlreadyExistsError",
    "InvalidObjectiveError", "ObjectiveEvaluationError",
    "ConstraintError", "ConstraintNotFoundError", "ConstraintAlreadyExistsError",
    "ConstraintViolationError", "InfeasibleSolutionError",
    "AlgorithmError", "AlgorithmNotFoundError", "AlgorithmExecutionError",
    "UnsupportedAlgorithmError",
    "SimulationError", "SimulationFailedError", "ScenarioNotFoundError",
    "EngineLifecycleError", "EngineNotInitializedError", "EngineAlreadyRunningError",
    "RegistryError", "RegistryOverflowError",
    "CandidateError", "CandidateNotFoundError", "InsufficientCandidatesError",
    # Context
    "Candidate", "OptDiagnostic", "OptimizationContextState",
    "optimization_session", "opt_stage_scope",
    "get_optimization_context", "reset_optimization_context",
    # Objectives
    "Objective", "ScoreObjective", "PayloadObjective", "CompositeObjective",
    "FunctionObjective",
    "ObjectiveManager",
    "ObjectiveRegistry", "get_objective_registry", "reset_objective_registry",
    "ObjectiveScore", "ObjectiveResult", "build_objective_result",
    # Constraints
    "OptimizationConstraint", "ConstraintCheckResult",
    "ThresholdConstraint", "BoundedConstraint", "PredicateConstraint",
    "ConstraintSolver",
    "ConstraintReport", "build_constraint_report",
    "ConstraintOptimizer", "get_constraint_optimizer", "reset_constraint_optimizer",
    # Algorithms
    "OptimizationAlgorithm", "OptimizationSolution",
    "GreedyOptimizer", "WeightedSumOptimizer",
    "ConstraintSatisfactionOptimizer", "MultiObjectiveOptimizer",
    "AlgorithmExecutor",
    "AlgorithmRegistry", "get_algorithm_registry", "reset_algorithm_registry",
    "AlgorithmSelector",
    # Simulation
    "SimulationEngine",
    "Scenario", "ScenarioOptimizer", "ScenarioResult",
    "SensitivityAnalyzer",
    "RobustnessEvaluator",
    # Registry
    "OptimizationRegistry", "get_optimization_registry", "reset_optimization_registry",
    # Manager / request / result
    "OptimizationRequest", "OptimizationResult",
    "OptimizationManager", "get_optimization_manager", "reset_optimization_manager",
    # Factory
    "OptimizationFactory",
    # Engine
    "DecisionOptimizationEngine",
    "get_decision_optimization_engine", "reset_decision_optimization_engine",
]
