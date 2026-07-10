"""iios/integration/__init__.py

Data Integration Layer — single gateway for all external data access in IIOS.

No module outside this package should communicate directly with external APIs.
"""
from __future__ import annotations

# ── Engine ────────────────────────────────────────────────────────────────────
from iios.integration.data_integration_engine import (
    DataIntegrationEngine,
    get_data_integration_engine,
    reset_data_integration_engine,
)

# ── Manager / Factory / Registry / Context ────────────────────────────────────
from iios.integration.integration_factory import IntegrationFactory
from iios.integration.integration_manager import IntegrationManager
from iios.integration.integration_registry import (
    IntegrationRegistry,
    get_integration_registry,
    reset_integration_registry,
)
from iios.integration.integration_context import (
    IntegrationContextState,
    integration_operation_context,
)

# ── Core models ───────────────────────────────────────────────────────────────
from iios.integration.core import (
    DataRecord,
    DataRequest,
    DataResponse,
    IntegrationEvent,
    IntegrationResult,
    ProviderContract,
)

# ── Providers ─────────────────────────────────────────────────────────────────
from iios.integration.providers import (
    BaseProvider,
    CircuitBreaker,
    ProviderCapabilities,
    ProviderHealth,
    ProviderManager,
    ProviderMetadata,
    ProviderRegistry,
)

# ── Pipeline ──────────────────────────────────────────────────────────────────
from iios.integration.pipeline import (
    Pipeline,
    PipelineBuilder,
    PipelineContext,
    PipelineEngine,
    PipelineExecutor,
    PipelineStage,
    PipelineStageResult,
)

# ── Normalization ─────────────────────────────────────────────────────────────
from iios.integration.normalization import (
    FieldMapper,
    FieldMapping,
    NormalizationEngine,
    SchemaMapper,
    SchemaMapperRegistry,
    SimpleSchemaMapper,
    TimestampNormalizer,
    UnitConverter,
)

# ── Validation ────────────────────────────────────────────────────────────────
from iios.integration.validation import (
    FieldSpec,
    IntegrityChecker,
    QualityChecker,
    SchemaValidator,
    ValidationEngine,
    ValidationIssue,
    ValidationReport,
)

# ── Monitoring ────────────────────────────────────────────────────────────────
from iios.integration.monitoring import (
    AvailabilityMonitor,
    HealthMonitor,
    LatencyMonitor,
    ProviderMonitor,
    ProviderStatistics,
    RollingProviderStats,
)

# ── Cache ─────────────────────────────────────────────────────────────────────
from iios.integration.cache import CacheEntry, CacheKey, IntegrationCache

# ── Registry ──────────────────────────────────────────────────────────────────
from iios.integration.registry import CapabilityRegistry

# ── Constants & Enums ────────────────────────────────────────────────────────
from iios.integration.integration_constants import (
    CacheStrategy,
    CircuitBreakerState,
    DataCategory,
    DataFrequency,
    DataQualityLevel,
    HealthStatus,
    IntegrationEngineStatus,
    IntegrationEventType,
    NormalizationStatus,
    PipelineStageType,
    PipelineStatus,
    ProviderPriority,
    ProviderStatus,
    ValidationSeverity,
    ValidationStatus,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from iios.integration.integration_exceptions import (
    AllProvidersFailedError,
    CacheError,
    CacheOverflowError,
    CircuitBreakerOpenError,
    FieldMappingError,
    IntegrationEngineAlreadyRunningError,
    IntegrationEngineNotInitializedError,
    IntegrationError,
    NormalizationError,
    PipelineConfigurationError,
    PipelineError,
    PipelineExecutionError,
    PipelineNotFoundError,
    PipelineStageError,
    ProviderAlreadyRegisteredError,
    ProviderCapabilityError,
    ProviderError,
    ProviderFetchError,
    ProviderInitializationError,
    ProviderNotFoundError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    QualityBelowThresholdError,
    RegistryCapacityError,
    RegistryError,
    RequiredFieldMissingError,
    SchemaMapperNotFoundError,
    SchemaValidationError,
    TimestampNormalizationError,
    UnitConversionError,
    ValidationError,
)

__version__ = "1.0.0"

__all__ = [
    # Engine
    "DataIntegrationEngine",
    "get_data_integration_engine",
    "reset_data_integration_engine",
    # Manager / Factory / Registry
    "IntegrationFactory",
    "IntegrationManager",
    "IntegrationRegistry",
    "get_integration_registry",
    "reset_integration_registry",
    "IntegrationContextState",
    "integration_operation_context",
    # Core
    "DataRecord",
    "DataRequest",
    "DataResponse",
    "IntegrationEvent",
    "IntegrationResult",
    "ProviderContract",
    # Providers
    "BaseProvider",
    "CircuitBreaker",
    "ProviderCapabilities",
    "ProviderHealth",
    "ProviderManager",
    "ProviderMetadata",
    "ProviderRegistry",
    # Pipeline
    "Pipeline",
    "PipelineBuilder",
    "PipelineContext",
    "PipelineEngine",
    "PipelineExecutor",
    "PipelineStage",
    "PipelineStageResult",
    # Normalization
    "FieldMapper",
    "FieldMapping",
    "NormalizationEngine",
    "SchemaMapper",
    "SchemaMapperRegistry",
    "SimpleSchemaMapper",
    "TimestampNormalizer",
    "UnitConverter",
    # Validation
    "FieldSpec",
    "IntegrityChecker",
    "QualityChecker",
    "SchemaValidator",
    "ValidationEngine",
    "ValidationIssue",
    "ValidationReport",
    # Monitoring
    "AvailabilityMonitor",
    "HealthMonitor",
    "LatencyMonitor",
    "ProviderMonitor",
    "ProviderStatistics",
    "RollingProviderStats",
    # Cache
    "CacheEntry",
    "CacheKey",
    "IntegrationCache",
    # Registry
    "CapabilityRegistry",
    # Enums
    "CacheStrategy",
    "CircuitBreakerState",
    "DataCategory",
    "DataFrequency",
    "DataQualityLevel",
    "HealthStatus",
    "IntegrationEngineStatus",
    "IntegrationEventType",
    "NormalizationStatus",
    "PipelineStageType",
    "PipelineStatus",
    "ProviderPriority",
    "ProviderStatus",
    "ValidationSeverity",
    "ValidationStatus",
    # Exceptions
    "IntegrationError",
    "ProviderError",
    "ProviderNotFoundError",
    "ProviderAlreadyRegisteredError",
    "ProviderInitializationError",
    "ProviderFetchError",
    "ProviderTimeoutError",
    "ProviderUnavailableError",
    "ProviderCapabilityError",
    "AllProvidersFailedError",
    "PipelineError",
    "PipelineStageError",
    "PipelineNotFoundError",
    "PipelineConfigurationError",
    "PipelineExecutionError",
    "ValidationError",
    "SchemaValidationError",
    "RequiredFieldMissingError",
    "RangeValidationError",
    "QualityBelowThresholdError",
    "NormalizationError",
    "FieldMappingError",
    "UnitConversionError",
    "TimestampNormalizationError",
    "SchemaMapperNotFoundError",
    "CacheError",
    "CacheOverflowError",
    "RegistryError",
    "RegistryCapacityError",
    "IntegrationEngineNotInitializedError",
    "IntegrationEngineAlreadyRunningError",
    "CircuitBreakerOpenError",
]
