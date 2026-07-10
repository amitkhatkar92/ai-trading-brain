"""iios/integration/integration_manager.py

Orchestrates provider lifecycle, routing, and pipeline execution.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable

from iios.integration.integration_constants import DataCategory, DataFrequency, PipelineStatus
from iios.integration.integration_exceptions import (
    AllProvidersFailedError,
    ProviderCapabilityError,
)
from iios.integration.cache.cache_key import CacheKey
from iios.integration.cache.integration_cache import IntegrationCache
from iios.integration.core.data_record import DataRecord, DataRequest, DataResponse
from iios.integration.core.integration_result import IntegrationResult
from iios.integration.monitoring.provider_monitor import ProviderMonitor
from iios.integration.normalization.normalization_engine import NormalizationEngine
from iios.integration.pipeline.pipeline_builder import Pipeline
from iios.integration.pipeline.pipeline_context import PipelineContext
from iios.integration.pipeline.pipeline_engine import PipelineEngine
from iios.integration.providers.base_provider import BaseProvider
from iios.integration.providers.provider_manager import ProviderManager
from iios.integration.registry.capability_registry import CapabilityRegistry
from iios.integration.validation.validation_engine import ValidationEngine

logger = logging.getLogger(__name__)


class IntegrationManager:
    """
    High-level coordinator for the data integration layer.

    Responsibilities:
    - Register / activate / deactivate providers
    - Route requests to appropriate providers
    - Execute pipelines (extract → validate → normalize → cache → publish)
    - Aggregate results from parallel providers
    - Observe request outcomes for monitoring
    - Provide fallback when primary providers fail
    """

    def __init__(
        self,
        provider_manager:    ProviderManager,
        pipeline_engine:     PipelineEngine,
        capability_registry: CapabilityRegistry,
        validation_engine:   ValidationEngine,
        normalization_engine: NormalizationEngine,
        cache:               IntegrationCache,
        monitor:             ProviderMonitor,
    ) -> None:
        self._provider_mgr  = provider_manager
        self._pipeline      = pipeline_engine
        self._capabilities  = capability_registry
        self._validation    = validation_engine
        self._normalization = normalization_engine
        self._cache         = cache
        self._monitor       = monitor
        self._publisher: Callable[[list[DataRecord], str], None] | None = None
        self._started_at    = time.time()

    # ── Provider management ───────────────────────────────────────────────────

    async def register_provider(self, provider: BaseProvider) -> None:
        await self._provider_mgr.register(provider)

    async def activate_provider(self, provider_id: str) -> None:
        await self._provider_mgr.activate(provider_id)

    async def deactivate_provider(self, provider_id: str) -> None:
        await self._provider_mgr.deactivate(provider_id)

    async def activate_all(self) -> dict[str, str]:
        return await self._provider_mgr.activate_all()

    async def shutdown_all(self) -> None:
        await self._provider_mgr.shutdown_all()

    def set_publisher(self, publisher: Callable[[list[DataRecord], str], None]) -> None:
        """Register a callback to receive published records."""
        self._publisher = publisher

    # ── Fetch ─────────────────────────────────────────────────────────────────

    async def fetch(
        self,
        request:       DataRequest,
        pipeline_id:   str | None = None,
        use_cache:     bool = True,
        use_fallback:  bool = True,
    ) -> IntegrationResult:
        """
        Fetch data for *request*, running the full pipeline.

        Provider selection order:
          1. Explicit provider_id in request (if set)
          2. Capability-based routing (highest priority first)
          3. Fallback to next provider if primary fails
        """
        # Cache check
        if use_cache:
            cache_key = CacheKey.build(
                request.provider_id,
                request.category.value,
                request.frequency.value,
                request.symbols[0] if request.symbols else None,
            )
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache HIT for request %s", request.request_id)
                return IntegrationResult(
                    request_id=request.request_id,
                    provider_id=request.provider_id,
                    status=PipelineStatus.COMPLETED,
                    records=cached,
                    records_in=len(cached),
                    records_out=len(cached),
                    metadata={"cache_hit": True},
                )

        # Resolve provider(s)
        providers = self._resolve_providers(request, use_fallback)
        if not providers:
            raise ProviderCapabilityError(
                f"No provider available for category='{request.category.value}'"
            )

        last_error: str = ""
        for provider in providers:
            try:
                result = await self._run_pipeline(provider, request, pipeline_id)
                if result.is_successful():
                    # Cache the output
                    if use_cache and result.records:
                        ck = CacheKey.build(
                            provider.provider_id,
                            request.category.value,
                            request.frequency.value,
                            request.symbols[0] if request.symbols else None,
                        )
                        self._cache.put(ck, result.records)
                    return result
                last_error = result.error or "pipeline failed"
            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "IntegrationManager: provider '%s' failed for request %s: %s",
                    provider.provider_id, request.request_id, exc,
                )
                self._monitor.observe_error(provider.provider_id)
                if not use_fallback:
                    raise

        raise AllProvidersFailedError(
            f"All providers failed for request {request.request_id}: {last_error}"
        )

    async def fetch_parallel(
        self,
        requests: list[DataRequest],
        **kwargs: Any,
    ) -> list[IntegrationResult]:
        """Execute multiple requests concurrently."""
        tasks = [self.fetch(req, **kwargs) for req in requests]
        return list(await asyncio.gather(*tasks, return_exceptions=False))

    # ── Internals ─────────────────────────────────────────────────────────────

    def _resolve_providers(
        self,
        request:      DataRequest,
        use_fallback: bool,
    ) -> list[BaseProvider]:
        if request.provider_id:
            try:
                p = self._provider_mgr.get(request.provider_id)
                if p.is_active():
                    return [p]
            except Exception:
                pass
        providers = self._capabilities.route(
            category=request.category.value,
            frequency=request.frequency.value,
        )
        return providers if use_fallback else providers[:1]

    async def _run_pipeline(
        self,
        provider:    BaseProvider,
        request:     DataRequest,
        pipeline_id: str | None,
    ) -> IntegrationResult:
        ctx = PipelineContext(
            request=request,
            provider=provider,
            validation_engine=self._validation,
            normalization_engine=self._normalization,
            cache=self._cache,
            publisher=self._publisher,
        )
        result = await self._pipeline.run(ctx, pipeline_id)
        # Observe outcome via raw_response if available
        if ctx.raw_response is not None:
            self._monitor.observe_response(ctx.raw_response)
        return result

    # ── Stats ─────────────────────────────────────────────────────────────────

    def statistics(self) -> dict[str, Any]:
        return {
            "providers":  self._provider_mgr.statistics(),
            "pipeline":   self._pipeline.statistics(),
            "cache":      self._cache.statistics(),
            "monitor":    self._monitor.statistics(),
            "uptime_sec": round(time.time() - self._started_at, 1),
        }
