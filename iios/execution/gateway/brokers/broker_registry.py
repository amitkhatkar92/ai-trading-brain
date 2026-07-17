"""iios/execution/gateway/brokers/broker_registry.py
==================================================
BrokerRegistry — LifecycleAwareMixin store for registered broker
instances and their configurations.

Provides registration, lookup, default broker selection, and
capability-based broker search.

C6 Execution Intelligence — Phase 5, Module 3
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from .broker_capabilities import BrokerCapabilities
from .broker_configuration import BrokerConfiguration
from .broker_interface import BrokerInterface
from .constants import (
    BROKER_REGISTRY_SYSTEM_ID,
    DEFAULT_MAX_BROKERS,
    BrokerCapability,
    VERSION,
)
from .exceptions import (
    BrokerAlreadyRegisteredError,
    BrokerManagerNotRunningError,
    BrokerNotRegisteredError,
    BrokerRegistryCapacityError,
)

_log   = get_logger(__name__, engine_id=BROKER_REGISTRY_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=BROKER_REGISTRY_SYSTEM_ID)


class BrokerRegistry(LifecycleAwareMixin):
    """
    Thread-safe registry of BrokerInterface instances and configurations.

    Write operations (register, remove, set_default) require the registry
    to be running.  Read operations (get, find_by_capability, etc.) are
    permitted at any lifecycle state.
    """

    def __init__(self, max_brokers: int = DEFAULT_MAX_BROKERS) -> None:
        super().__init__()
        self._max_brokers   = max(1, max_brokers)
        self._brokers:       Dict[str, BrokerInterface]     = {}
        self._configurations: Dict[str, BrokerConfiguration] = {}
        self._capabilities:   Dict[str, BrokerCapabilities]  = {}
        self._default_id:     Optional[str]                  = None
        self._lock            = threading.Lock()

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise BrokerManagerNotRunningError()

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(
            BROKER_REGISTRY_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        _log.info("BrokerRegistry started.", version=VERSION)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            BROKER_REGISTRY_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        _log.info(
            "BrokerRegistry stopped.",
            registered_count=len(self._brokers),
        )

    # ── Registration ─────────────────────────────────────────────────────────

    def register(
        self,
        broker:   BrokerInterface,
        config:   BrokerConfiguration,
        caps:     BrokerCapabilities,
    ) -> None:
        """
        Register a broker.

        Parameters
        ----------
        broker:
            The broker implementation instance.
        config:
            Configuration for this broker.
        caps:
            Declared capabilities.

        Raises
        ------
        BrokerManagerNotRunningError:
            If the registry is not running.
        BrokerRegistryCapacityError:
            If the registry is at maximum capacity.
        BrokerAlreadyRegisteredError:
            If a broker with the same ID is already registered.
        """
        self._assert_running()
        with self._lock:
            if len(self._brokers) >= self._max_brokers:
                raise BrokerRegistryCapacityError(self._max_brokers)
            if broker.broker_id in self._brokers:
                raise BrokerAlreadyRegisteredError(broker.broker_id)
            self._brokers[broker.broker_id]        = broker
            self._configurations[broker.broker_id] = config
            self._capabilities[broker.broker_id]   = caps
            if self._default_id is None:
                self._default_id = broker.broker_id
        _log.info(
            "Broker registered.",
            broker_id=broker.broker_id,
            broker_name=broker.broker_name,
        )

    def remove(self, broker_id: str) -> None:
        """
        Remove a registered broker.

        Raises BrokerNotRegisteredError if the broker_id is unknown.
        """
        self._assert_running()
        with self._lock:
            if broker_id not in self._brokers:
                raise BrokerNotRegisteredError(broker_id)
            del self._brokers[broker_id]
            del self._configurations[broker_id]
            del self._capabilities[broker_id]
            if self._default_id == broker_id:
                self._default_id = next(iter(self._brokers), None)
        _log.info("Broker removed.", broker_id=broker_id)

    def set_default(self, broker_id: str) -> None:
        """Set the default broker.  Raises BrokerNotRegisteredError if absent."""
        self._assert_running()
        with self._lock:
            if broker_id not in self._brokers:
                raise BrokerNotRegisteredError(broker_id)
            self._default_id = broker_id
        _log.info("Default broker set.", broker_id=broker_id)

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(self, broker_id: str) -> BrokerInterface:
        """Return the broker.  Raises BrokerNotRegisteredError if absent."""
        with self._lock:
            broker = self._brokers.get(broker_id)
        if broker is None:
            raise BrokerNotRegisteredError(broker_id)
        return broker

    def get_optional(self, broker_id: str) -> Optional[BrokerInterface]:
        with self._lock:
            return self._brokers.get(broker_id)

    def get_config(self, broker_id: str) -> BrokerConfiguration:
        with self._lock:
            config = self._configurations.get(broker_id)
        if config is None:
            raise BrokerNotRegisteredError(broker_id)
        return config

    def get_capabilities(self, broker_id: str) -> BrokerCapabilities:
        with self._lock:
            caps = self._capabilities.get(broker_id)
        if caps is None:
            raise BrokerNotRegisteredError(broker_id)
        return caps

    def default(self) -> Optional[BrokerInterface]:
        """Return the default broker, or None if no brokers are registered."""
        with self._lock:
            if self._default_id is None:
                return None
            return self._brokers.get(self._default_id)

    def default_id(self) -> Optional[str]:
        with self._lock:
            return self._default_id

    def exists(self, broker_id: str) -> bool:
        with self._lock:
            return broker_id in self._brokers

    # ── Enumeration ───────────────────────────────────────────────────────────

    def all_brokers(self) -> List[BrokerInterface]:
        with self._lock:
            return list(self._brokers.values())

    def all_broker_ids(self) -> List[str]:
        with self._lock:
            return list(self._brokers.keys())

    def all_configurations(self) -> List[BrokerConfiguration]:
        with self._lock:
            return list(self._configurations.values())

    # ── Capability search ─────────────────────────────────────────────────────

    def find_by_capability(
        self,
        capability: BrokerCapability,
    ) -> List[BrokerInterface]:
        """Return all brokers that support the given capability."""
        with self._lock:
            return [
                self._brokers[bid]
                for bid, caps in self._capabilities.items()
                if caps.has(capability)
            ]

    def find_ids_by_capability(
        self,
        capability: BrokerCapability,
    ) -> List[str]:
        with self._lock:
            return [
                bid
                for bid, caps in self._capabilities.items()
                if caps.has(capability)
            ]

    def capabilities_map(self) -> Dict[str, BrokerCapabilities]:
        """Return a snapshot mapping broker_id → BrokerCapabilities."""
        with self._lock:
            return dict(self._capabilities)

    # ── Counts ────────────────────────────────────────────────────────────────

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._brokers)

    @property
    def capacity(self) -> int:
        return self._max_brokers
