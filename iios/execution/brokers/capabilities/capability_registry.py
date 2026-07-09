"""iios/execution/brokers/capabilities/capability_registry.py"""
from __future__ import annotations

import threading
from typing import Any

from iios.execution.brokers.broker_constants import BrokerCapabilityType
from iios.execution.brokers.broker_exceptions import BrokerNotFoundError
from iios.execution.brokers.core.broker_capability import BrokerCapabilitySet


class CapabilityRegistry:
    """
    Maps broker_id → BrokerCapabilitySet.

    Supports dynamic registration and capability discovery across all adapters.
    Thread-safe.
    """

    def __init__(self) -> None:
        self._registry: dict[str, BrokerCapabilitySet] = {}
        self._lock = threading.RLock()

    def register(self, broker_id: str, capability_set: BrokerCapabilitySet) -> None:
        with self._lock:
            self._registry[broker_id] = capability_set

    def get(self, broker_id: str) -> BrokerCapabilitySet:
        with self._lock:
            caps = self._registry.get(broker_id)
        if caps is None:
            raise BrokerNotFoundError(
                f"No capabilities registered for broker '{broker_id}'",
                "BAF-011",
            )
        return caps

    def has(self, broker_id: str) -> bool:
        with self._lock:
            return broker_id in self._registry

    def unregister(self, broker_id: str) -> None:
        with self._lock:
            self._registry.pop(broker_id, None)

    def all_broker_ids(self) -> list[str]:
        with self._lock:
            return list(self._registry.keys())

    def discover(self, broker_id: str) -> list[BrokerCapabilityType]:
        """Return all supported capability types for *broker_id*."""
        return self.get(broker_id).all_supported()

    def brokers_with_capability(
        self, capability_type: BrokerCapabilityType
    ) -> list[str]:
        """Return all broker_ids that support the given capability."""
        with self._lock:
            return [
                bid
                for bid, caps in self._registry.items()
                if caps.supports(capability_type)
            ]

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {"registered_brokers": len(self._registry)}
