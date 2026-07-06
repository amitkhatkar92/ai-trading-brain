"""
iios/configuration/__init__.py
================================
IIOS Configuration Management System — public API.

This package provides:
  - ``ConfigurationManager``   — main orchestrator
  - ``IIOSConfiguration``      — typed root config model
  - All 18 section config dataclasses
  - All exception types
  - ``get_configuration_manager()`` singleton factory

Architecture Reference: IIOS-CIS-001 INFRA-CFG-001
Wave: 2 — Configuration Management System
"""

from __future__ import annotations

__status__  = "implemented"
__wave__    = 2
__version__ = "1.0.0"

# ---------------------------------------------------------------------------
# Manager & Singleton
# ---------------------------------------------------------------------------
from .configuration_manager import (
    ConfigurationManager,
    get_configuration_manager,
    _reset_singleton,
)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
from .configuration_models import (
    IIOSConfiguration,
    ConfigurationMetadata,
    SystemConfiguration,
    InfrastructureConfiguration,
    DatabaseConfiguration,
    KnowledgeConfiguration,
    OntologyConfiguration,
    AIConfiguration,
    ObservationConfiguration,
    ReasoningConfiguration,
    DecisionConfiguration,
    StrategyConfiguration,
    PortfolioConfiguration,
    RiskConfiguration,
    ExecutionConfiguration,
    MonitoringConfiguration,
    LoggingConfiguration,
    NotificationConfiguration,
    SecurityConfiguration,
    PluginConfiguration,
)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
from .configuration_exception import (
    ConfigurationError,
    ConfigurationLoadError,
    ConfigurationValidationError,
    ConfigurationNotFoundError,
    ConfigurationTypeError,
    ConfigurationRangeError,
    ConfigurationMergeError,
    ConfigurationEncryptionError,
    ConfigurationWatcherError,
    ConfigurationReloadError,
    ConfigurationSchemaError,
    ConfigurationProviderError,
    FieldValidationError,
    SectionValidationError,
)

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
from .configuration_schema import (
    FieldSpec,
    SectionSchema,
    IIOS_SCHEMA,
)

# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------
from .configuration_provider import (
    ConfigurationProvider,
    EnvironmentVariableProvider,
    DotEnvFileProvider,
    JSONFileProvider,
    TOMLFileProvider,
    YAMLFileProvider,
    INIFileProvider,
    PythonModuleProvider,
    DefaultsProvider,
    DictionaryProvider,
)

# ---------------------------------------------------------------------------
# Supporting components
# ---------------------------------------------------------------------------
from .configuration_cache import ConfigurationCache, CacheSnapshot
from .configuration_merger import ConfigurationMerger, ArrayMergeStrategy
from .configuration_resolver import ConfigurationResolver
from .configuration_validator import ConfigurationValidator, ValidationReport, ValidationIssue
from .configuration_registry import ConfigurationRegistry
from .configuration_watcher import ConfigurationWatcher
from .configuration_encryption import ConfigurationEncryption
from .configuration_loader import (
    ConfigurationSource,
    EnvVarsSource,
    DotEnvFileSource,
    JSONFileSource,
    TOMLFileSource,
    YAMLFileSource,
    INIFileSource,
    PythonModuleSource,
    DefaultsSource,
    DictionarySource,
)
from .configuration_constants import (
    ConfigSource,
    ConfigSection,
    IIOS_ARCHITECTURE_CONSTANTS,
    SOURCE_PRIORITY,
    ENCRYPTED_MARKER,
    SENSITIVE_KEY_PATTERNS,
    CERTIFIED_WIN_RATE_MIN,
    CERTIFIED_SHARPE_MIN,
    CERTIFIED_MAX_DRAWDOWN,
)

__all__ = [
    # Manager
    "ConfigurationManager",
    "get_configuration_manager",
    # Models
    "IIOSConfiguration",
    "ConfigurationMetadata",
    "SystemConfiguration",
    "InfrastructureConfiguration",
    "DatabaseConfiguration",
    "KnowledgeConfiguration",
    "OntologyConfiguration",
    "AIConfiguration",
    "ObservationConfiguration",
    "ReasoningConfiguration",
    "DecisionConfiguration",
    "StrategyConfiguration",
    "PortfolioConfiguration",
    "RiskConfiguration",
    "ExecutionConfiguration",
    "MonitoringConfiguration",
    "LoggingConfiguration",
    "NotificationConfiguration",
    "SecurityConfiguration",
    "PluginConfiguration",
    # Exceptions
    "ConfigurationError",
    "ConfigurationLoadError",
    "ConfigurationValidationError",
    "ConfigurationNotFoundError",
    "ConfigurationTypeError",
    "ConfigurationRangeError",
    "ConfigurationMergeError",
    "ConfigurationEncryptionError",
    "ConfigurationWatcherError",
    "ConfigurationReloadError",
    "ConfigurationSchemaError",
    "ConfigurationProviderError",
    "FieldValidationError",
    "SectionValidationError",
    # Schema
    "FieldSpec",
    "SectionSchema",
    "IIOS_SCHEMA",
    # Providers
    "ConfigurationProvider",
    "EnvironmentVariableProvider",
    "DotEnvFileProvider",
    "JSONFileProvider",
    "TOMLFileProvider",
    "YAMLFileProvider",
    "INIFileProvider",
    "PythonModuleProvider",
    "DefaultsProvider",
    "DictionaryProvider",
    # Components
    "ConfigurationCache",
    "CacheSnapshot",
    "ConfigurationMerger",
    "ArrayMergeStrategy",
    "ConfigurationResolver",
    "ConfigurationValidator",
    "ValidationReport",
    "ValidationIssue",
    "ConfigurationRegistry",
    "ConfigurationWatcher",
    "ConfigurationEncryption",
    # Loader sources
    "ConfigurationSource",
    "EnvVarsSource",
    "DotEnvFileSource",
    "JSONFileSource",
    "TOMLFileSource",
    "YAMLFileSource",
    "INIFileSource",
    "PythonModuleSource",
    "DefaultsSource",
    "DictionarySource",
    # Constants
    "ConfigSource",
    "ConfigSection",
    "IIOS_ARCHITECTURE_CONSTANTS",
    "SOURCE_PRIORITY",
    "ENCRYPTED_MARKER",
    "SENSITIVE_KEY_PATTERNS",
    "CERTIFIED_WIN_RATE_MIN",
    "CERTIFIED_SHARPE_MIN",
    "CERTIFIED_MAX_DRAWDOWN",
]
