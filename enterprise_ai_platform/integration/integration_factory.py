"""enterprise_ai_platform/integration/integration_factory.py

Factory for constructing the integration layer's object graph.
"""
from __future__ import annotations

from enterprise_ai_platform.integration.cache.integration_cache import IntegrationCache
from enterprise_ai_platform.integration.monitoring.availability_monitor import AvailabilityMonitor
from enterprise_ai_platform.integration.monitoring.health_monitor import HealthMonitor
from enterprise_ai_platform.integration.monitoring.latency_monitor import LatencyMonitor
from enterprise_ai_platform.integration.monitoring.provider_monitor import ProviderMonitor
from enterprise_ai_platform.integration.normalization.normalization_engine import NormalizationEngine
from enterprise_ai_platform.integration.normalization.schema_mapper import SchemaMapperRegistry
from enterprise_ai_platform.integration.normalization.timestamp_normalizer import TimestampNormalizer
from enterprise_ai_platform.integration.normalization.unit_converter import UnitConverter
from enterprise_ai_platform.integration.pipeline.pipeline_engine import PipelineEngine
from enterprise_ai_platform.integration.providers.provider_manager import ProviderManager
from enterprise_ai_platform.integration.providers.provider_registry import ProviderRegistry
from enterprise_ai_platform.integration.registry.capability_registry import CapabilityRegistry
from enterprise_ai_platform.integration.validation.integrity_checker import IntegrityChecker
from enterprise_ai_platform.integration.validation.quality_checker import QualityChecker
from enterprise_ai_platform.integration.validation.schema_validator import SchemaValidator
from enterprise_ai_platform.integration.validation.validation_engine import ValidationEngine


class IntegrationFactory:
    """
    Constructs fully-wired integration subsystem instances.
    All methods return new objects unless the singleton pattern is needed.
    """

    @staticmethod
    def create_provider_registry(**kw) -> ProviderRegistry:
        return ProviderRegistry(**kw)

    @staticmethod
    def create_provider_manager(registry: ProviderRegistry | None = None) -> ProviderManager:
        return ProviderManager(registry=registry or IntegrationFactory.create_provider_registry())

    @staticmethod
    def create_pipeline_engine() -> PipelineEngine:
        return PipelineEngine()

    @staticmethod
    def create_normalization_engine(
        schema_registry: SchemaMapperRegistry | None = None,
    ) -> NormalizationEngine:
        return NormalizationEngine(
            schema_registry=schema_registry or SchemaMapperRegistry(),
            timestamp_normalizer=TimestampNormalizer(),
            unit_converter=UnitConverter(),
        )

    @staticmethod
    def create_validation_engine() -> ValidationEngine:
        return ValidationEngine(
            schema_validator=SchemaValidator(),
            integrity_checker=IntegrityChecker(),
            quality_checker=QualityChecker(),
        )

    @staticmethod
    def create_cache(**kw) -> IntegrationCache:
        return IntegrationCache(**kw)

    @staticmethod
    def create_provider_monitor(
        provider_registry: ProviderRegistry | None = None,
    ) -> ProviderMonitor:
        health = HealthMonitor(registry=provider_registry)
        return ProviderMonitor(
            health_monitor=health,
            latency_monitor=LatencyMonitor(),
            availability_monitor=AvailabilityMonitor(),
        )

    @staticmethod
    def create_capability_registry(
        provider_registry: ProviderRegistry | None = None,
    ) -> CapabilityRegistry:
        return CapabilityRegistry(
            provider_registry or IntegrationFactory.create_provider_registry()
        )
