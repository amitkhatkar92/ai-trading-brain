"""iios/execution/brokers/broker_manager.py
==================================================
BrokerManager — IIOS v1.0 facade that owns the BrokerRegistry
and BrokerFactory.

This is the primary entry point for the Broker Abstraction Layer.
It manages broker registration, health queries, and statistics
aggregation. It does NOT perform any network I/O.

IIOS v1.0: LifecycleAwareMixin, logging, audit, error handling.

C6 Execution Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable

from iios.common.errors.error_context import ErrorContext
from iios.common.errors.error_manager import get_error_manager as _get_err_mgr
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ACTOR_MANAGER,
    ACTOR_SYSTEM,
    DEFAULT_MAX_BROKERS,
    MANAGER_SYSTEM_ID,
    VERSION,
    BrokerCapabilityCode,
    BrokerConnectionState,
    BrokerMode,
    Exchange,
    ProductType,
    TimeInForce,
)
from .exceptions import BrokerNotRunningError
from .broker_metadata import BrokerMetadata, RateLimitSpec
from .broker_capabilities import BrokerCapabilities
from .broker_health import BrokerHealthRecord
from .broker_statistics import BrokerStatistics, RegistryStatistics
from .broker_registry import BrokerRegistry, BrokerRecord
from .broker_factory import BrokerFactory
from .broker_events import BrokerEvent
from .broker_validation import BrokerValidator, BrokerValidationResult

_log   = get_logger(__name__, engine_id=MANAGER_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=MANAGER_SYSTEM_ID,
                          component="BrokerManager")

_manager_lock: threading.Lock = threading.Lock()
_manager_instance: "BrokerManager | None" = None


class BrokerManager(LifecycleAwareMixin):
    """
    IIOS v1.0 facade for the Broker Abstraction Layer.

    Owns:
      - BrokerRegistry  — stores BrokerRecord objects
      - BrokerFactory   — builds BrokerMetadata objects
      - BrokerValidator — stateless validation

    Responsibilities:
      - Register / unregister broker metadata
      - Query capabilities, health, and statistics
      - Add / remove event listeners
      - Provide the stable public API surface for M3
    """

    SYSTEM_ID = MANAGER_SYSTEM_ID
    VERSION   = VERSION

    def __init__(self, max_brokers: int = DEFAULT_MAX_BROKERS) -> None:
        self._registry  = BrokerRegistry(max_brokers=max_brokers)
        self._factory   = BrokerFactory()
        self._validator = BrokerValidator()
        self._started_at: float = 0.0

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        self._registry.start()
        self._started_at = time.time()
        _audit.log_lifecycle_event(
            self.SYSTEM_ID, "STOPPED", "RUNNING", self.VERSION
        )
        _log.info("BrokerManager started.")

    def _on_stop(self) -> None:
        if self._registry.is_running:
            self._registry.stop()
        _audit.log_lifecycle_event(
            self.SYSTEM_ID, "RUNNING", "STOPPED", self.VERSION
        )
        _log.info("BrokerManager stopped.")

    @property
    def is_running(self) -> bool:
        return self.lifecycle_state() == EngineState.RUNNING

    def _assert_running(self) -> None:
        if not self.is_running:
            raise BrokerNotRunningError(
                "BrokerManager must be started before use."
            )

    # ── Broker registration ───────────────────────────────────────────────────

    def register(
        self,
        metadata:  BrokerMetadata,
        overwrite: bool = False,
    ) -> BrokerRecord:
        """Register a broker by its metadata."""
        self._assert_running()
        validation = self._validator.validate_metadata(metadata)
        if not validation:
            raise from_validation(validation)
        record = self._registry.register(metadata, overwrite=overwrite)
        _log.info("BrokerManager: broker registered.",
                  broker_id=metadata.broker_id)
        return record

    def unregister(self, broker_id: str) -> None:
        """Remove a broker from the registry."""
        self._assert_running()
        self._registry.unregister(broker_id)

    def create_and_register(
        self,
        *,
        broker_id:           str,
        broker_name:         str,
        broker_version:      str = "1.0.0",
        supported_modes:     frozenset[BrokerMode]           | None = None,
        supported_exchanges: frozenset[Exchange]             | None = None,
        supported_products:  frozenset[ProductType]          | None = None,
        supported_tif:       frozenset[TimeInForce]          | None = None,
        capabilities:        frozenset[BrokerCapabilityCode] | None = None,
        rate_limit:          RateLimitSpec | None = None,
        description:         str = "",
        overwrite:           bool = False,
    ) -> BrokerRecord:
        """Convenience: create metadata via factory then register."""
        self._assert_running()
        metadata = self._factory.create_metadata(
            broker_id           = broker_id,
            broker_name         = broker_name,
            broker_version      = broker_version,
            supported_modes     = supported_modes,
            supported_exchanges = supported_exchanges,
            supported_products  = supported_products,
            supported_tif       = supported_tif,
            capabilities        = capabilities,
            rate_limit          = rate_limit,
            description         = description,
        )
        return self.register(metadata, overwrite=overwrite)

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_record(self, broker_id: str) -> BrokerRecord:
        self._assert_running()
        return self._registry.get(broker_id)

    def get_metadata(self, broker_id: str) -> BrokerMetadata:
        self._assert_running()
        return self._registry.get_metadata(broker_id)

    def get_capabilities(self, broker_id: str) -> BrokerCapabilities:
        self._assert_running()
        return self._registry.get_capabilities(broker_id)

    def get_health(self, broker_id: str) -> BrokerHealthRecord | None:
        self._assert_running()
        return self._registry.get_health(broker_id)

    def get_statistics(self, broker_id: str) -> BrokerStatistics:
        self._assert_running()
        return self._registry.get_statistics(broker_id)

    def all_broker_ids(self) -> list[str]:
        self._assert_running()
        return self._registry.all_broker_ids()

    def contains(self, broker_id: str) -> bool:
        self._assert_running()
        return self._registry.contains(broker_id)

    def count(self) -> int:
        self._assert_running()
        return self._registry.count()

    # ── Health ────────────────────────────────────────────────────────────────

    def record_health_update(
        self,
        broker_id:    str,
        is_healthy:   bool,
        latency_ms:   float = 0.0,
        error_message: str  = "",
    ) -> None:
        self._assert_running()
        self._registry.record_health_update(
            broker_id, is_healthy,
            latency_ms=latency_ms,
            error_message=error_message,
        )

    def set_connection_state(
        self,
        broker_id: str,
        state:     BrokerConnectionState,
    ) -> None:
        self._assert_running()
        self._registry.set_connection_state(broker_id, state)

    # ── Statistics ────────────────────────────────────────────────────────────

    def statistics(self) -> RegistryStatistics:
        self._assert_running()
        return self._registry.statistics()

    # ── Listeners ─────────────────────────────────────────────────────────────

    def add_listener(self, fn: Callable[[BrokerEvent], None]) -> None:
        self._registry.add_listener(fn)

    def remove_listener(self, fn: Callable[[BrokerEvent], None]) -> None:
        self._registry.remove_listener(fn)

    # ── Validation helpers ────────────────────────────────────────────────────

    def validate_metadata(self, metadata: BrokerMetadata) -> BrokerValidationResult:
        return self._validator.validate_metadata(metadata)

    # ── Internal ──────────────────────────────────────────────────────────────

    @property
    def uptime_sec(self) -> float:
        if self._started_at == 0.0:
            return 0.0
        return time.time() - self._started_at


# ── Helper ────────────────────────────────────────────────────────────────────

def from_validation(result: BrokerValidationResult) -> Exception:
    from .exceptions import BrokerValidationError
    return BrokerValidationError(
        "Broker metadata validation failed.",
        errors=result.errors,
    )
