"""iios/investment/strategy/__init__.py
Strategy Intelligence Engine — public API.
"""
from __future__ import annotations

from iios.investment.strategy.strategy_constants import (
    STRATEGY_ENGINE_SYSTEM_ID,
    STRATEGY_ENGINE_VERSION,
    DEFAULT_MAX_STRATEGIES,
    DEFAULT_SNAPSHOT_HISTORY,
    DEFAULT_SNAPSHOT_TTL_SEC,
    MIN_WIN_RATE,
    MIN_SHARPE,
    MAX_DRAWDOWN,
    MIN_TRADES_FOR_EVAL,
    TARGET_WIN_RATE,
    TARGET_SHARPE,
    TARGET_DRAWDOWN,
    LIFECYCLE_TRANSITIONS,
    AdaptationType,
    AssetClass,
    LifecycleEvent,
    MarketRegime,
    RegimeCompatibility,
    StrategyCategory,
    StrategyGrade,
    StrategyRecommendation,
    StrategyRiskLevel,
    StrategyStatus,
    StrategyTimeframe,
)
from iios.investment.strategy.strategy_exceptions import (
    StrategyIntelligenceError,
    StrategyError,
    StrategyNotFoundError,
    StrategyAlreadyExistsError,
    StrategyInvalidError,
    StrategyRegistryError,
    StrategyRegistryOverflowError,
    StrategyRegistryItemNotFoundError,
    StrategyRegistryItemAlreadyExistsError,
    StrategyEvaluationError,
    StrategyEvaluationDataInsufficientError,
    StrategyEvaluationFailedError,
    StrategySelectionError,
    NoStrategiesAvailableError,
    StrategySelectionFailedError,
    StrategyAdaptationError,
    StrategyAdaptationFailedError,
    StrategyLifecycleError,
    StrategyLifecycleInvalidTransitionError,
    StrategyLifecycleBlockedError,
    StrategyEngineError,
    StrategyEngineNotInitializedError,
    StrategyEngineAlreadyRunningError,
)
from iios.investment.strategy.strategy_context import (
    StrategyContextState,
    get_strategy_context,
    reset_strategy_context,
    strategy_session,
    strategy_stage_scope,
)
from iios.investment.strategy.strategy_factory import StrategyFactory
from iios.investment.strategy.strategy_registry import (
    StrategyRegistry,
    get_strategy_registry,
    reset_strategy_registry,
)
from iios.investment.strategy.strategy_manager import (
    StrategyManager,
    StrategyManagerStatistics,
    get_strategy_manager,
    reset_strategy_manager,
)
from iios.investment.strategy.strategy_intelligence_engine import (
    StrategyIntelligenceEngine,
    get_strategy_engine,
    reset_strategy_engine,
)
from iios.investment.strategy.strategy_intelligence import StrategyIntelligence
from iios.investment.strategy.core import (
    BaseStrategy,
    StrategyDefinition,
    StrategyHistory,
    StrategyMetadata,
    StrategyProfile,
    StrategySnapshot,
)
from iios.investment.strategy.evaluation import (
    StrategyComparator,
    StrategyEvaluator,
    StrategyRanker,
    StrategyScore,
)
from iios.investment.strategy.selection import StrategySelector
from iios.investment.strategy.adaptation import (
    AdaptationEngine,
    AdaptationResult,
    ParameterAdapter,
    RegimeAdapter,
    StrategyOptimizer,
)
from iios.investment.strategy.lifecycle import (
    LifecycleHistory,
    LifecycleHistoryEntry,
    LifecycleManager,
)
from iios.investment.strategy.performance import (
    PerformanceRecord,
    PerformanceTracker,
    StrategyStatistics,
)

__version__   = STRATEGY_ENGINE_VERSION
__system_id__ = STRATEGY_ENGINE_SYSTEM_ID

__all__ = [
    # Engine
    "StrategyIntelligenceEngine",
    "get_strategy_engine",
    "reset_strategy_engine",
    # Manager
    "StrategyManager",
    "StrategyManagerStatistics",
    "get_strategy_manager",
    "reset_strategy_manager",
    # Registry
    "StrategyRegistry",
    "get_strategy_registry",
    "reset_strategy_registry",
    # Factory
    "StrategyFactory",
    # Context
    "StrategyContextState",
    "get_strategy_context",
    "reset_strategy_context",
    "strategy_session",
    "strategy_stage_scope",
    # Intelligence output
    "StrategyIntelligence",
    # Core
    "BaseStrategy",
    "StrategyDefinition",
    "StrategyMetadata",
    "StrategySnapshot",
    "StrategyProfile",
    "StrategyHistory",
    # Evaluation
    "StrategyScore",
    "StrategyEvaluator",
    "StrategyRanker",
    "StrategyComparator",
    # Selection
    "StrategySelector",
    # Adaptation
    "AdaptationResult",
    "RegimeAdapter",
    "ParameterAdapter",
    "StrategyOptimizer",
    "AdaptationEngine",
    # Lifecycle
    "LifecycleHistoryEntry",
    "LifecycleHistory",
    "LifecycleManager",
    # Performance
    "PerformanceRecord",
    "PerformanceTracker",
    "StrategyStatistics",
    # Constants / Enums
    "AdaptationType",
    "AssetClass",
    "LifecycleEvent",
    "MarketRegime",
    "RegimeCompatibility",
    "StrategyCategory",
    "StrategyGrade",
    "StrategyRecommendation",
    "StrategyRiskLevel",
    "StrategyStatus",
    "StrategyTimeframe",
    "STRATEGY_ENGINE_VERSION",
    "STRATEGY_ENGINE_SYSTEM_ID",
    "MIN_WIN_RATE",
    "MIN_SHARPE",
    "MAX_DRAWDOWN",
    "MIN_TRADES_FOR_EVAL",
    "LIFECYCLE_TRANSITIONS",
    # Exceptions
    "StrategyIntelligenceError",
    "StrategyNotFoundError",
    "StrategyAlreadyExistsError",
    "StrategyInvalidError",
    "StrategyRegistryOverflowError",
    "StrategyEvaluationDataInsufficientError",
    "StrategyEvaluationFailedError",
    "NoStrategiesAvailableError",
    "StrategySelectionFailedError",
    "StrategyAdaptationFailedError",
    "StrategyLifecycleInvalidTransitionError",
    "StrategyLifecycleBlockedError",
    "StrategyEngineNotInitializedError",
    "StrategyEngineAlreadyRunningError",
]
