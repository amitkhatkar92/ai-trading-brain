"""iios/execution/planning/__init__.py
Execution Planning & Smart Routing Engine — public API.
"""
from __future__ import annotations

from iios.execution.planning.planning_constants import (
    PLANNING_ENGINE_VERSION,
    PLANNING_ENGINE_SYSTEM_ID,
    ExecutionAlgorithm,
    ExecutionMode,
    ExecutionPlanStatus,
    ExecutionPriority,
    LiquidityLevel,
    OrderSplitType,
    PlanningDecision,
    PolicyType,
    RoutingStrategy,
)
from iios.execution.planning.planning_exceptions import (
    PlanningIntelligenceError,
    PlanNotFoundError,
    PlanAlreadyExistsError,
    PlanTerminalError,
    PlanInvalidError,
    RoutingError,
    RouteNotFoundError,
    RoutingFailedError,
    NoSuitableVenueError,
    PolicyError,
    PolicyViolationError,
    PolicyNotFoundError,
    ConstraintError,
    ConstraintViolationError,
    PlanningEngineError,
    PlanningEngineNotInitializedError,
    PlanningEngineAlreadyRunningError,
    PlanningRegistryError,
    PlanningRegistryOverflowError,
    PlanningRegistryItemNotFoundError,
)
from iios.execution.planning.planning_context import (
    PlanningContextState,
    get_planning_context,
    reset_planning_context,
    planning_session,
    planning_stage_scope,
)
from iios.execution.planning.planning_factory import PlanningFactory
from iios.execution.planning.planning_registry import (
    PlanningRegistry,
    get_planning_registry,
    reset_planning_registry,
)
from iios.execution.planning.planning_manager import (
    PlanningManager,
    PlanningManagerStats,
    get_planning_manager,
    reset_planning_manager,
)
from iios.execution.planning.execution_planning_engine import (
    ExecutionPlanningEngine,
    get_planning_engine,
    reset_planning_engine,
)
from iios.execution.planning.core import (
    ExecutionCost,
    ExecutionConstraints,
    ExecutionRoute,
    ExecutionSchedule,
    ExecutionStrategy,
    ExecutionInstruction,
    ExecutionStatistics,
    ExecutionPlan,
)
from iios.execution.planning.routing import (
    RouteRegistry,
    VenueInfo,
    RouteEvaluator,
    RouteScore,
    RouteSelector,
    RouteOptimizer,
    OptimizationResult,
    RoutingEngine,
)
from iios.execution.planning.planner import (
    ExecutionBatch,
    OrderSplitter,
    SplitConfig,
    SplitResult,
    OrderMerger,
    MergeResult,
    ExecutionScheduler,
    ScheduleRequest,
    OrderPlanner,
    PlanRequest,
    PlanResult,
)
from iios.execution.planning.analytics import (
    CostEstimator,
    CostEstimatorConfig,
    SlippageEstimator,
    SlippageEstimatorConfig,
    ImpactEstimator,
    ImpactEstimatorConfig,
    LiquidityEstimate,
    LiquidityEstimator,
    LiquidityEstimatorConfig,
)
from iios.execution.planning.policies import (
    ExecutionPolicy,
    ImmediatePolicy,
    RiskLimitedPolicy,
    PolicyEvaluation,
    PolicyRegistry,
    PolicyRule,
)

__version__   = PLANNING_ENGINE_VERSION
__system_id__ = PLANNING_ENGINE_SYSTEM_ID

__all__ = [
    # Engine
    "ExecutionPlanningEngine", "get_planning_engine", "reset_planning_engine",
    # Manager
    "PlanningManager", "PlanningManagerStats",
    "get_planning_manager", "reset_planning_manager",
    # Registry
    "PlanningRegistry", "get_planning_registry", "reset_planning_registry",
    # Factory / Context
    "PlanningFactory",
    "PlanningContextState", "get_planning_context", "reset_planning_context",
    "planning_session", "planning_stage_scope",
    # Core models
    "ExecutionPlan", "ExecutionCost", "ExecutionConstraints",
    "ExecutionRoute", "ExecutionSchedule", "ExecutionStrategy",
    "ExecutionInstruction", "ExecutionStatistics",
    # Routing
    "RouteRegistry", "VenueInfo", "RouteEvaluator", "RouteScore",
    "RouteSelector", "RouteOptimizer", "OptimizationResult", "RoutingEngine",
    # Planner
    "ExecutionBatch",
    "OrderSplitter", "SplitConfig", "SplitResult",
    "OrderMerger", "MergeResult",
    "ExecutionScheduler", "ScheduleRequest",
    "OrderPlanner", "PlanRequest", "PlanResult",
    # Analytics
    "CostEstimator", "CostEstimatorConfig",
    "SlippageEstimator", "SlippageEstimatorConfig",
    "ImpactEstimator", "ImpactEstimatorConfig",
    "LiquidityEstimate", "LiquidityEstimator", "LiquidityEstimatorConfig",
    # Policies
    "ExecutionPolicy", "ImmediatePolicy", "RiskLimitedPolicy",
    "PolicyEvaluation", "PolicyRegistry", "PolicyRule",
    # Enums / constants
    "ExecutionAlgorithm", "ExecutionMode", "ExecutionPlanStatus",
    "ExecutionPriority", "LiquidityLevel", "OrderSplitType",
    "PlanningDecision", "PolicyType", "RoutingStrategy",
    # Exceptions
    "PlanningIntelligenceError",
    "PlanNotFoundError", "PlanAlreadyExistsError",
    "PlanTerminalError", "PlanInvalidError",
    "RoutingError", "RouteNotFoundError", "RoutingFailedError", "NoSuitableVenueError",
    "PolicyError", "PolicyViolationError", "PolicyNotFoundError",
    "ConstraintError", "ConstraintViolationError",
    "PlanningEngineError", "PlanningEngineNotInitializedError",
    "PlanningEngineAlreadyRunningError",
    "PlanningRegistryError", "PlanningRegistryOverflowError",
    "PlanningRegistryItemNotFoundError",
]
