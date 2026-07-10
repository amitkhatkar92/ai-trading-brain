"""iios/integration/data_integration_engine.py

Top-level facade and module-level singleton for the Data Integration Layer.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any, Callable

from iios.integration.integration_constants import (
    INTEGRATION_ENGINE_SYSTEM_ID,
    INTEGRATION_ENGINE_VERSION,
    IntegrationEngineStatus,
)
from iios.integration.integration_exceptions import (
    IntegrationEngineAlreadyRunningError,
    IntegrationEngineNotInitializedError,
)
from iios.integration.integration_factory import IntegrationFactory
from iios.integration.integration_manager import IntegrationManager
from iios.integration.core.data_record import DataRecord, DataRequest, DataResponse
from iios.integration.core.integration_result import IntegrationResult
from iios.integration.providers.base_provider import BaseProvider

logger = logging.getLogger(__name__)


class DataIntegrationEngine:
    """
    Single entry point for the entire Data Integration Layer.

    Usage::

        engine = get_data_integration_engine(auto_start=True)
        await engine.register_provider(my_provider)
        result = await engine.fetch(request)
    """

    def __init__(self, manager: IntegrationManager) -> None:
        self._manager    = manager
        self._status     = IntegrationEngineStatus.STOPPED
        self._started_at: float | None = None
        self._lock        = threading.RLock()
        logger.info(
            "DataIntegrationEngine v%s initialised (%s)",
            INTEGRATION_ENGINE_VERSION,
            INTEGRATION_ENGINE_SYSTEM_ID,
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        with self._lock:
            if self._status == IntegrationEngineStatus.RUNNING:
                raise IntegrationEngineAlreadyRunningError(
                    "DataIntegrationEngine is already running"
                )
            self._status     = IntegrationEngineStatus.RUNNING
            self._started_at = time.time()
        await self._manager.activate_all()
        logger.info("DataIntegrationEngine started")

    async def stop(self) -> None:
        with self._lock:
            self._status = IntegrationEngineStatus.STOPPING
        await self._manager.shutdown_all()
        with self._lock:
            self._status = IntegrationEngineStatus.STOPPED
        logger.info("DataIntegrationEngine stopped")

    @property
    def status(self) -> IntegrationEngineStatus:
        return self._status

    def is_running(self) -> bool:
        return self._status == IntegrationEngineStatus.RUNNING

    def _assert_running(self) -> None:
        if self._status != IntegrationEngineStatus.RUNNING:
            raise IntegrationEngineNotInitializedError(
                "DataIntegrationEngine is not running — call start() first"
            )

    # ── Provider management ───────────────────────────────────────────────────

    async def register_provider(self, provider: BaseProvider) -> None:
        self._assert_running()
        await self._manager.register_provider(provider)

    async def activate_provider(self, provider_id: str) -> None:
        self._assert_running()
        await self._manager.activate_provider(provider_id)

    async def deactivate_provider(self, provider_id: str) -> None:
        self._assert_running()
        await self._manager.deactivate_provider(provider_id)

    def set_publisher(self, publisher: Callable[[list[DataRecord], str], None]) -> None:
        self._manager.set_publisher(publisher)

    # ── Data access ───────────────────────────────────────────────────────────

    async def fetch(
        self,
        request:     DataRequest,
        pipeline_id: str | None = None,
        use_cache:   bool = True,
    ) -> IntegrationResult:
        self._assert_running()
        return await self._manager.fetch(request, pipeline_id=pipeline_id, use_cache=use_cache)

    async def fetch_parallel(
        self,
        requests: list[DataRequest],
        use_cache: bool = True,
    ) -> list[IntegrationResult]:
        self._assert_running()
        return await self._manager.fetch_parallel(requests, use_cache=use_cache)

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def summary(self) -> dict[str, Any]:
        s = self._manager.statistics()
        s.update({
            "version":    INTEGRATION_ENGINE_VERSION,
            "system_id":  INTEGRATION_ENGINE_SYSTEM_ID,
            "status":     self._status.value,
            "started_at": self._started_at,
        })
        return s

    @property
    def manager(self) -> IntegrationManager:
        return self._manager


# ── Singleton ────────────────────────────────────────────────────────────────

_engine_instance: DataIntegrationEngine | None = None
_engine_lock = threading.Lock()


def get_data_integration_engine(auto_start: bool = False) -> DataIntegrationEngine:
    """Return (or create) the module-level singleton."""
    global _engine_instance
    if _engine_instance is None:
        with _engine_lock:
            if _engine_instance is None:
                factory   = IntegrationFactory
                p_registry = factory.create_provider_registry()
                p_manager  = factory.create_provider_manager(p_registry)
                pipeline   = factory.create_pipeline_engine()
                cap_reg    = factory.create_capability_registry(p_registry)
                validation = factory.create_validation_engine()
                norm_eng   = factory.create_normalization_engine()
                cache      = factory.create_cache()
                monitor    = factory.create_provider_monitor(p_registry)
                manager    = IntegrationManager(
                    provider_manager=p_manager,
                    pipeline_engine=pipeline,
                    capability_registry=cap_reg,
                    validation_engine=validation,
                    normalization_engine=norm_eng,
                    cache=cache,
                    monitor=monitor,
                )
                _engine_instance = DataIntegrationEngine(manager)
                if auto_start:
                    # Fire-and-forget in sync context
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            loop.create_task(_engine_instance.start())
                        else:
                            loop.run_until_complete(_engine_instance.start())
                    except RuntimeError:
                        pass
    return _engine_instance


def reset_data_integration_engine() -> None:
    """Reset singleton — for testing."""
    global _engine_instance
    with _engine_lock:
        _engine_instance = None
