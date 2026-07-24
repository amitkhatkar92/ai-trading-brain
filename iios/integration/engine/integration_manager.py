"""
integration_manager.py — iios.integration.engine
--------------------------------------------------
IntegrationManager — top-level public API for the Integration Engine.

Owns an IntegrationEngine instance and provides a clean start/stop
interface with request submission, registration, and status/health access.

C15 Enterprise Integration & Connectivity — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .adapter_manager import AdapterDescriptor
from .connector_manager import ConnectorDescriptor
from .constants import DEFAULT_ENGINE_ID
from .integration_engine import IntegrationEngine
from .integration_events import IntegrationEngineEventBus
from .integration_factory import IntegrationEngineFactory
from .integration_health import EngineHealthReport
from .integration_registry import IntegrationEngineRegistry
from .integration_request import IntegrationRequest
from .integration_response import IntegrationResponse
from .integration_statistics import IntegrationEngineStatisticsReport
from .integration_status import IntegrationEngineStatus
from .integration_validation import EngineValidationReport
from .protocol_registry import ProtocolDescriptor

_log = get_logger(__name__)


class IntegrationManager:
    """
    Top-level manager for the Integration Engine.

    Provides a clean public API:
      - start() / stop()
      - submit_request()
      - register_connector() / register_adapter() / register_protocol()
      - get_status() / get_health() / get_statistics()
    """

    def __init__(
        self,
        engine_id: str                          = DEFAULT_ENGINE_ID,
        engine:    Optional[IntegrationEngine]  = None,
    ) -> None:
        self._engine_id = engine_id
        self._engine    = engine or IntegrationEngine(engine_id=engine_id)
        self._factory   = IntegrationEngineFactory()
        self._started   = False
        self._lock      = threading.Lock()

    # ----------------------------------------------------------------
    # Lifecycle
    # ----------------------------------------------------------------

    def start(self) -> None:
        with self._lock:
            if self._started:
                _log.warning(f"Manager already started: id={self._engine_id!r}")
                return
            self._started = True
        self._engine.initialize()
        _log.info(f"Integration Manager started: id={self._engine_id!r}")

    def stop(self) -> None:
        with self._lock:
            if not self._started:
                return
            self._started = False
        self._engine.stop()
        _log.info(f"Integration Manager stopped: id={self._engine_id!r}")

    # ----------------------------------------------------------------
    # Request submission
    # ----------------------------------------------------------------

    def submit_request(
        self, request: IntegrationRequest
    ) -> IntegrationResponse:
        return self._engine.dispatch(request)

    def submit_batch(
        self, requests: List[IntegrationRequest]
    ) -> List[IntegrationResponse]:
        return self._engine.dispatch_batch(requests)

    def validate_request(
        self, request: IntegrationRequest
    ) -> EngineValidationReport:
        return self._engine.validate(request)

    # ----------------------------------------------------------------
    # Registration
    # ----------------------------------------------------------------

    def register_connector(self, descriptor: ConnectorDescriptor) -> None:
        self._engine.register_connector(descriptor)
        _log.info(
            f"Manager: connector registered "
            f"type={descriptor.connector_type.value!r} "
            f"name={descriptor.name!r}"
        )

    def register_adapter(self, descriptor: AdapterDescriptor) -> None:
        self._engine.register_adapter(descriptor)
        _log.info(
            f"Manager: adapter registered "
            f"type={descriptor.adapter_type.value!r} "
            f"name={descriptor.name!r}"
        )

    def register_protocol(self, descriptor: ProtocolDescriptor) -> None:
        self._engine.register_protocol(descriptor)
        _log.info(
            f"Manager: protocol registered "
            f"type={descriptor.protocol_type.value!r} "
            f"name={descriptor.name!r}"
        )

    # ----------------------------------------------------------------
    # Status and health
    # ----------------------------------------------------------------

    def get_status(self) -> IntegrationEngineStatus:
        return self._engine.status()

    def get_health(self) -> EngineHealthReport:
        return self._engine.health()

    def get_statistics(self) -> IntegrationEngineStatisticsReport:
        return self._engine.stats.report()

    # ----------------------------------------------------------------
    # Convenience
    # ----------------------------------------------------------------

    @property
    def engine(self) -> IntegrationEngine:
        return self._engine

    @property
    def factory(self) -> IntegrationEngineFactory:
        return self._factory

    @property
    def is_started(self) -> bool:
        with self._lock:
            return self._started
