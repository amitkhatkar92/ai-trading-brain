"""iios/integration/integration_exceptions.py

Exception hierarchy for the Data Integration Layer.
Error code prefix: DI-
"""
from __future__ import annotations


class IntegrationError(Exception):
    """Root exception for all Data Integration Layer errors. [DI-000]"""

    def __init__(self, message: str, code: str = "DI-000") -> None:
        super().__init__(message)
        self.code    = code
        self.message = message

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.code}: {self.message})"


# ── Provider errors ───────────────────────────────────────────────────────────

class ProviderError(IntegrationError):
    """Base class for provider errors. [DI-010]"""
    def __init__(self, message: str, code: str = "DI-010") -> None:
        super().__init__(message, code)


class ProviderNotFoundError(ProviderError):
    """Provider not registered. [DI-011]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "DI-011")


class ProviderAlreadyRegisteredError(ProviderError):
    """Provider already registered under the same ID. [DI-012]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "DI-012")


class ProviderInitializationError(ProviderError):
    """Provider failed to initialize. [DI-013]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "DI-013")


class ProviderFetchError(ProviderError):
    """Provider fetch operation failed. [DI-014]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "DI-014")


class ProviderTimeoutError(ProviderError):
    """Provider fetch timed out. [DI-015]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "DI-015")


class ProviderUnavailableError(ProviderError):
    """Provider is not available (circuit open, shutting down, etc.). [DI-016]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "DI-016")


class ProviderCapabilityError(ProviderError):
    """Requested capability not supported by this provider. [DI-017]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "DI-017")


class AllProvidersFailedError(ProviderError):
    """All providers for a request have failed. [DI-018]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "DI-018")


# ── Pipeline errors ───────────────────────────────────────────────────────────

class PipelineError(IntegrationError):
    """Base class for pipeline errors. [DI-020]"""
    def __init__(self, message: str, code: str = "DI-020") -> None:
        super().__init__(message, code)


class PipelineStageError(PipelineError):
    """A pipeline stage failed. [DI-021]"""
    def __init__(self, message: str, stage: str = "") -> None:
        super().__init__(message, "DI-021")
        self.stage = stage


class PipelineNotFoundError(PipelineError):
    """Named pipeline not found. [DI-022]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "DI-022")


class PipelineConfigurationError(PipelineError):
    """Pipeline mis-configured. [DI-023]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "DI-023")


class PipelineExecutionError(PipelineError):
    """Pipeline execution failed. [DI-024]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "DI-024")


# ── Validation errors ─────────────────────────────────────────────────────────

class ValidationError(IntegrationError):
    """Base class for validation errors. [DI-030]"""
    def __init__(self, message: str, code: str = "DI-030") -> None:
        super().__init__(message, code)


class SchemaValidationError(ValidationError):
    """Record does not conform to the expected schema. [DI-031]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "DI-031")


class RequiredFieldMissingError(ValidationError):
    """A required field is absent. [DI-032]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "DI-032")


class RangeValidationError(ValidationError):
    """A field value falls outside the allowed range. [DI-033]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "DI-033")


class QualityBelowThresholdError(ValidationError):
    """Data quality score is below the minimum threshold. [DI-034]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "DI-034")


# ── Normalization errors ──────────────────────────────────────────────────────

class NormalizationError(IntegrationError):
    """Base class for normalization errors. [DI-040]"""
    def __init__(self, message: str, code: str = "DI-040") -> None:
        super().__init__(message, code)


class FieldMappingError(NormalizationError):
    """Cannot map a source field to the canonical schema. [DI-041]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "DI-041")


class UnitConversionError(NormalizationError):
    """Unit conversion failed. [DI-042]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "DI-042")


class TimestampNormalizationError(NormalizationError):
    """Timestamp cannot be normalized to UTC. [DI-043]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "DI-043")


class SchemaMapperNotFoundError(NormalizationError):
    """No schema mapper registered for this provider/category. [DI-044]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "DI-044")


# ── Cache errors ──────────────────────────────────────────────────────────────

class CacheError(IntegrationError):
    """Base class for cache errors. [DI-050]"""
    def __init__(self, message: str, code: str = "DI-050") -> None:
        super().__init__(message, code)


class CacheOverflowError(CacheError):
    """Cache capacity exceeded. [DI-051]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "DI-051")


# ── Registry errors ───────────────────────────────────────────────────────────

class RegistryError(IntegrationError):
    """Base class for registry errors. [DI-060]"""
    def __init__(self, message: str, code: str = "DI-060") -> None:
        super().__init__(message, code)


class RegistryCapacityError(RegistryError):
    """Registry is at maximum capacity. [DI-061]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "DI-061")


# ── Engine errors ─────────────────────────────────────────────────────────────

class IntegrationEngineNotInitializedError(IntegrationError):
    """Engine called before initialization. [DI-070]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "DI-070")


class IntegrationEngineAlreadyRunningError(IntegrationError):
    """Engine is already running. [DI-071]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "DI-071")


class CircuitBreakerOpenError(IntegrationError):
    """Request blocked — circuit breaker is open. [DI-072]"""
    def __init__(self, message: str) -> None:
        super().__init__(message, "DI-072")
