"""iios/execution/brokers/broker_registry.py

Instance registry: tracks live BaseBrokerAdapter objects.
(AdapterRegistry tracks classes; BrokerRegistry tracks instances.)
"""
from __future__ import annotations

import logging
import threading
from typing import Any

from iios.execution.brokers.broker_constants import DEFAULT_MAX_BROKERS
from iios.execution.brokers.broker_exceptions import (
    BrokerAlreadyExistsError,
    BrokerNotFoundError,
    BrokerRegistryOverflowError,
)
from iios.execution.brokers.core.base_broker_adapter import BaseBrokerAdapter

logger = logging.getLogger(__name__)

_registry_lock: threading.Lock = threading.Lock()
_registry_instance: BrokerRegistry | None = None


class BrokerRegistry:
    """
    Central store of live broker adapter instances.

    Thread-safe.  Supports registration, lookup, and bulk iteration.
    """

    def __init__(self, max_brokers: int = DEFAULT_MAX_BROKERS) -> None:
        self._adapters:  dict[str, BaseBrokerAdapter] = {}
        self._max_brokers = max_brokers
        self._lock       = threading.RLock()

    # ── Registration ──────────────────────────────────────────────────────────

    def register(
        self,
        adapter:   BaseBrokerAdapter,
        overwrite: bool = False,
    ) -> None:
        with self._lock:
            broker_id = adapter.broker_id
            if broker_id in self._adapters and not overwrite:
                raise BrokerAlreadyExistsError(
                    f"Adapter '{broker_id}' already registered (use overwrite=True)",
                    "BAF-012",
                )
            if len(self._adapters) >= self._max_brokers and broker_id not in self._adapters:
                raise BrokerRegistryOverflowError(
                    f"BrokerRegistry capacity reached ({self._max_brokers})",
                    "BAF-081",
                )
            self._adapters[broker_id] = adapter
            logger.debug("BrokerRegistry: registered %s", broker_id)

    def unregister(self, broker_id: str) -> None:
        with self._lock:
            removed = self._adapters.pop(broker_id, None)
        if removed:
            logger.info("BrokerRegistry: unregistered %s", broker_id)

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(self, broker_id: str) -> BaseBrokerAdapter:
        with self._lock:
            adapter = self._adapters.get(broker_id)
        if adapter is None:
            raise BrokerNotFoundError(
                f"No adapter registered for broker '{broker_id}'",
                "BAF-011",
            )
        return adapter

    def has(self, broker_id: str) -> bool:
        with self._lock:
            return broker_id in self._adapters

    def all_adapters(self) -> list[BaseBrokerAdapter]:
        with self._lock:
            return list(self._adapters.values())

    def all_broker_ids(self) -> list[str]:
        with self._lock:
            return list(self._adapters.keys())

    def size(self) -> int:
        with self._lock:
            return len(self._adapters)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "registered_adapters": len(self._adapters),
                "max_brokers":         self._max_brokers,
                "broker_ids":          list(self._adapters.keys()),
            }


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_broker_registry() -> BrokerRegistry:
    global _registry_instance
    with _registry_lock:
        if _registry_instance is None:
            _registry_instance = BrokerRegistry()
    return _registry_instance


def reset_broker_registry() -> None:
    global _registry_instance
    with _registry_lock:
        _registry_instance = None
