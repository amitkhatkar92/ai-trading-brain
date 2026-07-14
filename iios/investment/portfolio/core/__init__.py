"""iios/investment/portfolio/core/__init__.py

Institutional Portfolio Framework Core — public surface.
"""

# ── Existing data model ────────────────────────────────────────────────────
from iios.investment.portfolio.core.position import Position
from iios.investment.portfolio.core.position_group import PositionGroup
from iios.investment.portfolio.core.asset_allocation import AssetAllocation
from iios.investment.portfolio.core.portfolio import Portfolio
from iios.investment.portfolio.core.portfolio_snapshot import PortfolioSnapshot
from iios.investment.portfolio.core.portfolio_history import PortfolioHistory
from iios.investment.portfolio.core.portfolio_profile import PortfolioProfile
from iios.investment.portfolio.core.portfolio_statistics import PortfolioStatistics
from iios.investment.portfolio.core.portfolio_intelligence import PortfolioIntelligence

# ── Framework types ────────────────────────────────────────────────────────
from iios.investment.portfolio.core.portfolio_types import (
    PortfolioLifecycleState,
    PortfolioDomain,
    PortfolioCapability,
    FrameworkStatus,
    ValidationOutcome,
    PublishChannel,
)
from iios.investment.portfolio.core.asset_support import (
    AssetDescriptor,
    AssetSupportMatrix,
    ASSET_SUPPORT_MATRIX,
    get_asset_descriptor,
)
from iios.investment.portfolio.core.investment_style import (
    InvestmentStyle,
    InvestmentHorizon,
    ConcentrationBias,
    StyleConstraints,
    InvestmentStyleProfile,
    StyleRegistry,
    STYLE_REGISTRY,
)

# ── Metadata & configuration ───────────────────────────────────────────────
from iios.investment.portfolio.core.portfolio_metadata import (
    PortfolioMetadata,
    build_metadata,
)
from iios.investment.portfolio.core.portfolio_configuration import (
    PortfolioConfiguration,
    PortfolioConfigurationError,
    InvestmentObjective,
    CapitalLimits,
    AllocationPolicy,
    RiskPolicy,
    RebalancingPolicy,
)
from iios.investment.portfolio.core.parameter_registry import (
    ParameterDefinition,
    ParameterRegistry,
    ParameterType,
    PARAMETER_REGISTRY,
)
from iios.investment.portfolio.core.parameter_validation import (
    ValidationResult,
    ParameterValidator,
    ValidationRule,
)
from iios.investment.portfolio.core.configuration_profiles import (
    ConfigurationProfile,
    get_profile,
    get_default_profile,
    list_profiles,
    register_profile,
)
from iios.investment.portfolio.core.configuration_engine import ConfigurationEngine

# ── Runtime state ──────────────────────────────────────────────────────────
from iios.investment.portfolio.core.portfolio_state import (
    PortfolioStateSnapshot,
    PortfolioStateStore,
)

# ── Framework context ──────────────────────────────────────────────────────
from iios.investment.portfolio.core.framework_context import (
    IntegrationRefs,
    PortfolioRuntimeContext,
)

# ── Events ─────────────────────────────────────────────────────────────────
from iios.investment.portfolio.core.portfolio_events import (
    PortfolioEvent,
    PortfolioEventType,
    EventPriority,
    PortfolioRegisteredEvent,
    PortfolioInitializedEvent,
    PortfolioActivatedEvent,
    PortfolioArchivedEvent,
    PortfolioFailedEvent,
    PortfolioRebalancedEvent,
    RiskAlertEvent,
    PerformanceAlertEvent,
)
from iios.investment.portfolio.core.event_history import EventRecord, EventHistory
from iios.investment.portfolio.core.event_dispatcher import EventDispatcher

# ── Lifecycle ──────────────────────────────────────────────────────────────
from iios.investment.portfolio.core.portfolio_lifecycle import (
    PortfolioLifecycle,
    LifecycleTransition,
    LifecycleError,
)
from iios.investment.portfolio.core.portfolio_session import (
    SessionState,
    PortfolioSession,
    PortfolioSessionRecord,
    SessionManager,
)

# ── Registry / catalog / loader / factory ─────────────────────────────────
from iios.investment.portfolio.core.portfolio_registry import (
    PortfolioClassEntry,
    PortfolioClassRegistry,
    PortfolioClassNotFoundError,
)
from iios.investment.portfolio.core.portfolio_catalog import (
    CatalogEntry,
    PortfolioCatalog,
)
from iios.investment.portfolio.core.portfolio_loader import (
    LoadResult,
    PortfolioLoader,
)
from iios.investment.portfolio.core.portfolio_factory import (
    FactoryResult,
    PortfolioFactory,
)

# ── Base portfolio ─────────────────────────────────────────────────────────
from iios.investment.portfolio.core.base_portfolio import BasePortfolio

# ── Main framework ─────────────────────────────────────────────────────────
from iios.investment.portfolio.core.portfolio_framework import (
    PortfolioFramework,
    FrameworkStatistics,
)

__all__ = [
    # Data model
    "Position", "PositionGroup", "AssetAllocation",
    "Portfolio", "PortfolioSnapshot", "PortfolioHistory",
    "PortfolioProfile", "PortfolioStatistics", "PortfolioIntelligence",
    # Types
    "PortfolioLifecycleState", "PortfolioDomain", "PortfolioCapability",
    "FrameworkStatus", "ValidationOutcome", "PublishChannel",
    # Asset support
    "AssetDescriptor", "AssetSupportMatrix", "ASSET_SUPPORT_MATRIX", "get_asset_descriptor",
    # Investment style
    "InvestmentStyle", "InvestmentHorizon", "ConcentrationBias",
    "StyleConstraints", "InvestmentStyleProfile", "StyleRegistry", "STYLE_REGISTRY",
    # Metadata & configuration
    "PortfolioMetadata", "build_metadata",
    "PortfolioConfiguration", "PortfolioConfigurationError",
    "InvestmentObjective", "CapitalLimits", "AllocationPolicy",
    "RiskPolicy", "RebalancingPolicy",
    "ParameterDefinition", "ParameterRegistry", "ParameterType", "PARAMETER_REGISTRY",
    "ValidationResult", "ParameterValidator", "ValidationRule",
    "ConfigurationProfile", "get_profile", "get_default_profile", "list_profiles",
    "register_profile", "ConfigurationEngine",
    # State
    "PortfolioStateSnapshot", "PortfolioStateStore",
    # Context
    "IntegrationRefs", "PortfolioRuntimeContext",
    # Events
    "PortfolioEvent", "PortfolioEventType", "EventPriority",
    "PortfolioRegisteredEvent", "PortfolioInitializedEvent",
    "PortfolioActivatedEvent", "PortfolioArchivedEvent", "PortfolioFailedEvent",
    "PortfolioRebalancedEvent", "RiskAlertEvent", "PerformanceAlertEvent",
    "EventRecord", "EventHistory", "EventDispatcher",
    # Lifecycle
    "PortfolioLifecycle", "LifecycleTransition", "LifecycleError",
    "SessionState", "PortfolioSession", "PortfolioSessionRecord", "SessionManager",
    # Registry / factory
    "PortfolioClassEntry", "PortfolioClassRegistry", "PortfolioClassNotFoundError",
    "CatalogEntry", "PortfolioCatalog",
    "LoadResult", "PortfolioLoader",
    "FactoryResult", "PortfolioFactory",
    # Base and framework
    "BasePortfolio",
    "PortfolioFramework", "FrameworkStatistics",
]
