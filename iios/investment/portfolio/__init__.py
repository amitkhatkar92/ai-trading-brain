"""iios/investment/portfolio/__init__.py
Portfolio & Risk Intelligence Engine — public API.
"""
from __future__ import annotations

from iios.investment.portfolio.portfolio_constants import (
    PORTFOLIO_ENGINE_VERSION,
    PORTFOLIO_ENGINE_SYSTEM_ID,
    AllocationStatus,
    AssetClass,
    DrawdownSeverity,
    ExposureType,
    PortfolioHealthStatus,
    PortfolioObjective,
    PortfolioStatus,
    PortfolioType,
    PositionStatus,
    PositionType,
    RiskCategory,
    RiskLevel,
)
from iios.investment.portfolio.portfolio_exceptions import (
    PortfolioIntelligenceError,
    PortfolioNotFoundError,
    PortfolioAlreadyExistsError,
    PortfolioInvalidError,
    PositionNotFoundError,
    PositionAlreadyExistsError,
    PositionInvalidError,
    RiskError,
    RiskLimitExceededError,
    RiskAnalysisFailedError,
    ExposureError,
    ExposureLimitExceededError,
    ExposureDataMissingError,
    AllocationError,
    AllocationLimitExceededError,
    AllocationInvalidError,
    DrawdownError,
    DrawdownLimitExceededError,
    PortfolioEngineError,
    PortfolioEngineNotInitializedError,
    PortfolioEngineAlreadyRunningError,
    PortfolioRegistryError,
    PortfolioRegistryOverflowError,
    PortfolioRegistryItemNotFoundError,
    PortfolioRegistryItemAlreadyExistsError,
)
from iios.investment.portfolio.portfolio_context import (
    PortfolioContextState,
    get_portfolio_context,
    reset_portfolio_context,
    portfolio_session,
    portfolio_stage_scope,
)
from iios.investment.portfolio.portfolio_factory import PortfolioFactory
from iios.investment.portfolio.portfolio_registry import (
    PortfolioRegistry,
    get_portfolio_registry,
    reset_portfolio_registry,
)
from iios.investment.portfolio.portfolio_manager import (
    PortfolioManager,
    get_portfolio_manager,
    reset_portfolio_manager,
)
from iios.investment.portfolio.portfolio_intelligence_engine import (
    PortfolioIntelligenceEngine,
    get_portfolio_engine,
    reset_portfolio_engine,
)
from iios.investment.portfolio.core import (
    Position,
    PositionGroup,
    AssetAllocation,
    Portfolio,
    PortfolioSnapshot,
    PortfolioHistory,
    PortfolioProfile,
    PortfolioStatistics,
    PortfolioIntelligence,
)
from iios.investment.portfolio.risk import (
    RiskProfile,
    RiskStatistics,
    RiskRegistry,
    DrawdownAnalysis,
    DrawdownEngine,
    RiskAnalyzer,
    RiskEngine,
)
from iios.investment.portfolio.exposure import (
    ExposureLimits,
    ExposureReport,
    ExposureTracker,
    ExposureEngine,
)
from iios.investment.portfolio.allocation import (
    AllocationConstraints,
    AllocationReport,
    CapitalAllocator,
    AllocationEngine,
)
from iios.investment.portfolio.analytics import (
    PerformanceAnalysis,
    PerformanceAnalyzer,
    DiversificationAnalysis,
    DiversificationAnalyzer,
    ConcentrationAnalysis,
    ConcentrationAnalyzer,
    AllocationAnalysis,
    AllocationAnalyzer,
    PortfolioAnalytics,
    PortfolioAnalyzer,
)

__version__   = PORTFOLIO_ENGINE_VERSION
__system_id__ = PORTFOLIO_ENGINE_SYSTEM_ID

__all__ = [
    # Engine
    "PortfolioIntelligenceEngine", "get_portfolio_engine", "reset_portfolio_engine",
    # Manager
    "PortfolioManager", "get_portfolio_manager", "reset_portfolio_manager",
    # Registry
    "PortfolioRegistry", "get_portfolio_registry", "reset_portfolio_registry",
    # Factory
    "PortfolioFactory",
    # Context
    "PortfolioContextState", "get_portfolio_context", "reset_portfolio_context",
    "portfolio_session", "portfolio_stage_scope",
    # Core models
    "Position", "PositionGroup", "AssetAllocation",
    "Portfolio", "PortfolioSnapshot", "PortfolioHistory",
    "PortfolioProfile", "PortfolioStatistics", "PortfolioIntelligence",
    # Risk
    "RiskProfile", "RiskStatistics", "RiskRegistry",
    "DrawdownAnalysis", "DrawdownEngine",
    "RiskAnalyzer", "RiskEngine",
    # Exposure
    "ExposureLimits", "ExposureReport", "ExposureTracker", "ExposureEngine",
    # Allocation
    "AllocationConstraints", "AllocationReport", "CapitalAllocator", "AllocationEngine",
    # Analytics
    "PerformanceAnalysis", "PerformanceAnalyzer",
    "DiversificationAnalysis", "DiversificationAnalyzer",
    "ConcentrationAnalysis", "ConcentrationAnalyzer",
    "AllocationAnalysis", "AllocationAnalyzer",
    "PortfolioAnalytics", "PortfolioAnalyzer",
    # Enums / constants
    "AllocationStatus", "AssetClass", "DrawdownSeverity", "ExposureType",
    "PortfolioHealthStatus", "PortfolioObjective", "PortfolioStatus",
    "PortfolioType", "PositionStatus", "PositionType", "RiskCategory", "RiskLevel",
    # Exceptions
    "PortfolioIntelligenceError",
    "PortfolioNotFoundError", "PortfolioAlreadyExistsError", "PortfolioInvalidError",
    "PositionNotFoundError", "PositionAlreadyExistsError", "PositionInvalidError",
    "RiskError", "RiskLimitExceededError", "RiskAnalysisFailedError",
    "ExposureError", "ExposureLimitExceededError", "ExposureDataMissingError",
    "AllocationError", "AllocationLimitExceededError", "AllocationInvalidError",
    "DrawdownError", "DrawdownLimitExceededError",
    "PortfolioEngineError", "PortfolioEngineNotInitializedError", "PortfolioEngineAlreadyRunningError",
    "PortfolioRegistryError", "PortfolioRegistryOverflowError",
    "PortfolioRegistryItemNotFoundError", "PortfolioRegistryItemAlreadyExistsError",
]
