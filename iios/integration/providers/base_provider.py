"""iios/integration/providers/base_provider.py

Abstract base class for all data providers.
Every external data source plugin must subclass BaseProvider.
"""
from __future__ import annotations

import asyncio
import logging
import time
import abc
from typing import Any

from iios.integration.integration_constants import (
    DataCategory,
    DataFrequency,
    ProviderPriority,
    ProviderStatus,
    DEFAULT_FETCH_TIMEOUT_SEC,
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_BACKOFF_SEC,
    DEFAULT_RETRY_MAX_BACKOFF_SEC,
)
from iios.integration.integration_exceptions import (
    ProviderFetchError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from iios.integration.core.data_record import DataRecord, DataRequest, DataResponse
from iios.integration.providers.provider_capabilities import ProviderCapabilities
from iios.integration.providers.provider_health import CircuitBreaker, ProviderHealth
from iios.integration.providers.provider_metadata import ProviderMetadata

logger = logging.getLogger(__name__)


class BaseProvider(abc.ABC):
    """
    Abstract base for all IIOS data providers.

    Concrete providers implement:
      - provider_id   (property)
      - capabilities  (property)
      - fetch()       (async method)
      - health_check() (async method)

    The base class provides:
      - Retry with exponential back-off
      - Circuit breaker integration
      - Metadata tracking
      - Structured logging
    """

    def __init__(
        self,
        priority:           ProviderPriority  = ProviderPriority.NORMAL,
        retry_attempts:     int               = DEFAULT_RETRY_ATTEMPTS,
        retry_backoff_sec:  float             = DEFAULT_RETRY_BACKOFF_SEC,
        circuit_threshold:  int               = 5,
        circuit_reset_sec:  float             = 60.0,
    ) -> None:
        self._priority         = priority
        self._retry_attempts   = retry_attempts
        self._retry_backoff    = retry_backoff_sec
        self._status           = ProviderStatus.INACTIVE
        self._circuit          = CircuitBreaker(circuit_threshold, circuit_reset_sec)
        self._metadata: ProviderMetadata | None = None  # lazily initialized

    # ── Identity (must override) ──────────────────────────────────────────────

    @property
    @abc.abstractmethod
    def provider_id(self) -> str:
        """Unique provider identifier (e.g. 'yahoo_finance', 'nse_live')."""

    @property
    @abc.abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Declares what this provider can fetch."""

    # ── Fetch (must override) ─────────────────────────────────────────────────

    @abc.abstractmethod
    async def _do_fetch(self, request: DataRequest) -> DataResponse:
        """
        Provider-specific fetch implementation.
        Called by fetch() after circuit-breaker and retry wrappers.
        """

    @abc.abstractmethod
    async def health_check(self) -> ProviderHealth:
        """
        Lightweight probe of the provider's reachability.
        Should complete within DEFAULT_HEALTH_CHECK_TIMEOUT_SEC.
        """

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """One-time setup (e.g. auth, connection pool). Override if needed."""
        self._status = ProviderStatus.ACTIVE
        self.metadata.status = ProviderStatus.ACTIVE
        self.metadata.activated_at = time.time()
        logger.info("Provider '%s' initialized", self.provider_id)

    async def shutdown(self) -> None:
        """Graceful teardown. Override if needed."""
        self._status = ProviderStatus.SHUTTING_DOWN
        self.metadata.status = ProviderStatus.SHUTTING_DOWN
        logger.info("Provider '%s' shut down", self.provider_id)

    # ── Public fetch with retry + circuit breaker ─────────────────────────────

    async def fetch(self, request: DataRequest) -> DataResponse:
        if not self._circuit.allow_request():
            raise ProviderUnavailableError(
                f"Provider '{self.provider_id}' circuit breaker is OPEN"
            )
        last_exc: Exception | None = None
        backoff = self._retry_backoff
        for attempt in range(1, self._retry_attempts + 1):
            try:
                t0 = time.perf_counter()
                response = await asyncio.wait_for(
                    self._do_fetch(request),
                    timeout=request.timeout_sec or DEFAULT_FETCH_TIMEOUT_SEC,
                )
                response.latency_ms = (time.perf_counter() - t0) * 1_000
                self._circuit.record_success()
                self.metadata.mark_fetched()
                return response
            except asyncio.TimeoutError as exc:
                last_exc = ProviderTimeoutError(
                    f"Provider '{self.provider_id}' timed out "
                    f"(attempt {attempt}/{self._retry_attempts})"
                )
                logger.warning(str(last_exc))
                self._circuit.record_failure()
                self.metadata.mark_error(str(last_exc))
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "Provider '%s' attempt %d/%d failed: %s",
                    self.provider_id, attempt, self._retry_attempts, exc,
                )
                self._circuit.record_failure()
                self.metadata.mark_error(str(exc))
            if attempt < self._retry_attempts:
                await asyncio.sleep(min(backoff, DEFAULT_RETRY_MAX_BACKOFF_SEC))
                backoff *= 2.0
        raise ProviderFetchError(
            f"Provider '{self.provider_id}' failed after {self._retry_attempts} attempts: {last_exc}"
        )

    # ── Accessors ─────────────────────────────────────────────────────────────

    @property
    def status(self) -> ProviderStatus:
        return self._status

    @property
    def metadata(self) -> ProviderMetadata:
        if self._metadata is None:
            self._metadata = ProviderMetadata(
                provider_id=self.provider_id,
                priority=self._priority,
                status=self._status,
            )
        return self._metadata

    @property
    def priority(self) -> ProviderPriority:
        return self._priority

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        return self._circuit

    def is_active(self) -> bool:
        return self._status == ProviderStatus.ACTIVE

    def can_handle(self, category: str, frequency: str | None = None) -> bool:
        caps = self.capabilities
        if not caps.supports_category(category):
            return False
        if frequency and not caps.supports_frequency(frequency):
            return False
        return True

    def statistics(self) -> dict[str, Any]:
        return {
            "provider_id":  self.provider_id,
            "status":       self._status.value,
            "circuit":      self._circuit.to_dict(),
            "metadata":     self._metadata.to_dict(),
            "capabilities": self.capabilities.to_dict(),
        }
