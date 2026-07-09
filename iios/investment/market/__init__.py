"""iios/investment/market/__init__.py
Market Intelligence Engine — public API surface.
"""
from __future__ import annotations

# ── constants ─────────────────────────────────────────────────────────────────
from iios.investment.market.market_constants import (
    BreadthCondition,
    CorrelationRegime,
    LiquidityLevel,
    MarketPhase,
    MarketRegime,
    MarketStatus,
    MarketStrength,
    SentimentLevel,
    TrendDirection,
    VolatilityLevel,
    MARKET_ENGINE_VERSION,
    MARKET_ENGINE_SYSTEM_ID,
)

# ── exceptions ────────────────────────────────────────────────────────────────
from iios.investment.market.market_exceptions import (
    MarketIntelligenceError,
    MarketStateError,
    MarketStateNotFoundError,
    MarketStateAlreadyExistsError,
    MarketStateTransitionError,
    RegimeError,
    RegimeNotFoundError,
    RegimeInvalidError,
    RegimeTransitionError,
    SnapshotError,
    SnapshotNotFoundError,
    SnapshotStaleError,
    SnapshotInvalidError,
    MarketAnalysisError,
    MarketAnalysisFailedError,
    MarketAnalysisTimeoutError,
    MarketEngineError,
    MarketEngineNotInitializedError,
    MarketEngineAlreadyRunningError,
    MarketRegistryError,
    MarketRegistryItemNotFoundError,
    MarketRegistryItemAlreadyExistsError,
    MarketRegistryOverflowError,
    MarketDataError,
    MarketDataMissingError,
    MarketDataInvalidError,
    MarketDataStaleError,
)

# ── context ───────────────────────────────────────────────────────────────────
from iios.investment.market.market_context import (
    MarketContextState,
    get_market_context,
    reset_market_context,
    market_session,
    market_stage_scope,
)

# ── market state ──────────────────────────────────────────────────────────────
from iios.investment.market.market_state.market_state import MarketState
from iios.investment.market.market_state.market_snapshot import MarketSnapshot
from iios.investment.market.market_state.market_state_manager import MarketStateManager
from iios.investment.market.market_state.market_statistics import MarketStatistics

# ── regime ────────────────────────────────────────────────────────────────────
from iios.investment.market.regime.regime_transition import RegimeTransition
from iios.investment.market.regime.regime_history import RegimeHistory
from iios.investment.market.regime.regime_classifier import RegimeClassifier, DefaultRegimeClassifier
from iios.investment.market.regime.market_regime_engine import MarketRegimeEngine

# ── analytics ─────────────────────────────────────────────────────────────────
from iios.investment.market.analytics.trend_analyzer import TrendAnalyzer, TrendAnalysis
from iios.investment.market.analytics.breadth_analyzer import BreadthAnalyzer, BreadthAnalysis
from iios.investment.market.analytics.volatility_analyzer import VolatilityAnalyzer, VolatilityAnalysis
from iios.investment.market.analytics.liquidity_analyzer import LiquidityAnalyzer, LiquidityAnalysis
from iios.investment.market.analytics.correlation_analyzer import CorrelationAnalyzer, CorrelationAnalysis
from iios.investment.market.analytics.market_structure_engine import MarketStructureEngine, MarketStructure

# ── models ────────────────────────────────────────────────────────────────────
from iios.investment.market.models.market_health import MarketHealth
from iios.investment.market.models.market_signal import MarketSignal, SignalType, SignalStrength
from iios.investment.market.models.market_summary import MarketSummary
from iios.investment.market.models.market_intelligence import MarketIntelligence

# ── factory ───────────────────────────────────────────────────────────────────
from iios.investment.market.market_factory import MarketFactory

# ── registry ──────────────────────────────────────────────────────────────────
from iios.investment.market.market_registry import (
    MarketRegistry,
    get_market_registry,
    reset_market_registry,
)

# ── manager ───────────────────────────────────────────────────────────────────
from iios.investment.market.market_manager import (
    MarketManager,
    get_market_manager,
    reset_market_manager,
)

# ── engine ────────────────────────────────────────────────────────────────────
from iios.investment.market.market_intelligence_engine import (
    MarketIntelligenceEngine,
    get_market_engine,
    reset_market_engine,
)

__version__ = MARKET_ENGINE_VERSION

__all__ = [
    # constants
    "BreadthCondition", "CorrelationRegime", "LiquidityLevel", "MarketPhase",
    "MarketRegime", "MarketStatus", "MarketStrength", "SentimentLevel",
    "TrendDirection", "VolatilityLevel",
    "MARKET_ENGINE_VERSION", "MARKET_ENGINE_SYSTEM_ID",
    # exceptions
    "MarketIntelligenceError",
    "MarketStateError", "MarketStateNotFoundError", "MarketStateAlreadyExistsError",
    "MarketStateTransitionError",
    "RegimeError", "RegimeNotFoundError", "RegimeInvalidError", "RegimeTransitionError",
    "SnapshotError", "SnapshotNotFoundError", "SnapshotStaleError", "SnapshotInvalidError",
    "MarketAnalysisError", "MarketAnalysisFailedError", "MarketAnalysisTimeoutError",
    "MarketEngineError", "MarketEngineNotInitializedError", "MarketEngineAlreadyRunningError",
    "MarketRegistryError", "MarketRegistryItemNotFoundError",
    "MarketRegistryItemAlreadyExistsError", "MarketRegistryOverflowError",
    "MarketDataError", "MarketDataMissingError", "MarketDataInvalidError", "MarketDataStaleError",
    # context
    "MarketContextState", "get_market_context", "reset_market_context",
    "market_session", "market_stage_scope",
    # market state
    "MarketState", "MarketSnapshot", "MarketStateManager", "MarketStatistics",
    # regime
    "RegimeTransition", "RegimeHistory", "RegimeClassifier", "DefaultRegimeClassifier",
    "MarketRegimeEngine",
    # analytics
    "TrendAnalyzer", "TrendAnalysis",
    "BreadthAnalyzer", "BreadthAnalysis",
    "VolatilityAnalyzer", "VolatilityAnalysis",
    "LiquidityAnalyzer", "LiquidityAnalysis",
    "CorrelationAnalyzer", "CorrelationAnalysis",
    "MarketStructureEngine", "MarketStructure",
    # models
    "MarketHealth", "MarketSignal", "SignalType", "SignalStrength",
    "MarketSummary", "MarketIntelligence",
    # factory
    "MarketFactory",
    # registry
    "MarketRegistry", "get_market_registry", "reset_market_registry",
    # manager
    "MarketManager", "get_market_manager", "reset_market_manager",
    # engine
    "MarketIntelligenceEngine", "get_market_engine", "reset_market_engine",
]
