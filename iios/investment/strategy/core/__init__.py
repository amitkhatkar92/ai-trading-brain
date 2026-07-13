"""iios/investment/strategy/core/__init__.py"""
# ── Existing exports (strategy intelligence subsystem) ────────────────────────
from iios.investment.strategy.core.strategy_definition import StrategyDefinition
from iios.investment.strategy.core.strategy_metadata import StrategyMetadata
from iios.investment.strategy.core.strategy_snapshot import StrategySnapshot
from iios.investment.strategy.core.strategy_profile import StrategyProfile
from iios.investment.strategy.core.strategy_history import StrategyHistory
from iios.investment.strategy.core.base_strategy import BaseStrategy

# ── Institutional Framework exports ───────────────────────────────────────────
from iios.investment.strategy.core.strategy_state import StrategyState, validate_transition
from iios.investment.strategy.core.strategy_capabilities import StrategyCapability
from iios.investment.strategy.core.asset_support import SupportedAssetClass, AssetSupport
from iios.investment.strategy.core.market_support import SupportedMarketType, SupportedExchangeZone, MarketSupport
from iios.investment.strategy.core.timeframe_support import SupportedTimeframe, TradingStyle, TimeframeSupport
from iios.investment.strategy.core.strategy_descriptor import StrategyVersion, StrategyDescriptor
from iios.investment.strategy.core.strategy_configuration import ParameterSpec, StrategyConfiguration, ConfigurationError
from iios.investment.strategy.core.strategy_context import StrategyContext
from iios.investment.strategy.core.institutional_base_strategy import (
    Signal, Candidate, ExecutionPlan,
    StrategyError, SignalGenerationError, RiskValidationError,
    InstitutionalBaseStrategy,
)
from iios.investment.strategy.core.strategy_events import StrategyEventType, StrategyEvent
from iios.investment.strategy.core.event_history import EventHistory
from iios.investment.strategy.core.event_dispatcher import EventDispatcher
from iios.investment.strategy.core.strategy_lifecycle import StrategyLifecycle, LifecycleError
from iios.investment.strategy.core.strategy_session import SessionMetrics, StrategySession
from iios.investment.strategy.core.execution_history import ExecutionHistory
from iios.investment.strategy.core.strategy_registry import InstitutionalStrategyRegistry, RegistrationError
from iios.investment.strategy.core.strategy_factory import InstitutionalStrategyFactory, FactoryError
from iios.investment.strategy.core.strategy_loader import StrategyLoader, LoaderError
from iios.investment.strategy.core.strategy_catalog import InstitutionalStrategyCatalog
from iios.investment.strategy.core.parameter_registry import ParameterRegistry
from iios.investment.strategy.core.parameter_validation import ParameterValidator, ValidationResult
from iios.investment.strategy.core.configuration_version import ConfigVersion, ConfigurationVersionStore
from iios.investment.strategy.core.configuration_engine import ConfigurationEngine
from iios.investment.strategy.core.strategy_framework import StrategyFramework

__all__ = [
    # Existing
    "StrategyDefinition",
    "StrategyMetadata",
    "StrategySnapshot",
    "StrategyProfile",
    "StrategyHistory",
    "BaseStrategy",
    # Institutional framework
    "StrategyState", "validate_transition",
    "StrategyCapability",
    "SupportedAssetClass", "AssetSupport",
    "SupportedMarketType", "SupportedExchangeZone", "MarketSupport",
    "SupportedTimeframe", "TradingStyle", "TimeframeSupport",
    "StrategyVersion", "StrategyDescriptor",
    "ParameterSpec", "StrategyConfiguration", "ConfigurationError",
    "StrategyContext",
    "Signal", "Candidate", "ExecutionPlan",
    "StrategyError", "SignalGenerationError", "RiskValidationError",
    "InstitutionalBaseStrategy",
    "StrategyEventType", "StrategyEvent",
    "EventHistory", "EventDispatcher",
    "StrategyLifecycle", "LifecycleError",
    "SessionMetrics", "StrategySession",
    "ExecutionHistory",
    "InstitutionalStrategyRegistry", "RegistrationError",
    "InstitutionalStrategyFactory", "FactoryError",
    "StrategyLoader", "LoaderError",
    "InstitutionalStrategyCatalog",
    "ParameterRegistry", "ParameterValidator", "ValidationResult",
    "ConfigVersion", "ConfigurationVersionStore",
    "ConfigurationEngine",
    "StrategyFramework",
]
