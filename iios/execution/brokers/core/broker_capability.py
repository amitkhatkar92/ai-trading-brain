"""iios/execution/brokers/core/broker_capability.py"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.execution.brokers.broker_constants import BrokerCapabilityType


@dataclass
class BrokerCapability:
    """A single capability declaration for a broker adapter."""

    capability_type: BrokerCapabilityType
    is_supported:   bool = True
    description:    str  = ""
    constraints:    dict[str, Any] = field(default_factory=dict)
    metadata:       dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_type": self.capability_type.value,
            "is_supported":    self.is_supported,
            "description":     self.description,
            "constraints":     self.constraints,
            "metadata":        self.metadata,
        }


class BrokerCapabilitySet:
    """Immutable-by-convention set of capabilities for a single broker."""

    def __init__(self, capabilities: list[BrokerCapability] | None = None) -> None:
        self._capabilities: dict[BrokerCapabilityType, BrokerCapability] = {}
        for cap in (capabilities or []):
            self._capabilities[cap.capability_type] = cap

    # ── Queries ───────────────────────────────────────────────────────────────

    def supports(self, capability_type: BrokerCapabilityType) -> bool:
        cap = self._capabilities.get(capability_type)
        return cap is not None and cap.is_supported

    def get(self, capability_type: BrokerCapabilityType) -> BrokerCapability | None:
        return self._capabilities.get(capability_type)

    def all_supported(self) -> list[BrokerCapabilityType]:
        return [ct for ct, cap in self._capabilities.items() if cap.is_supported]

    def all_capabilities(self) -> list[BrokerCapability]:
        return list(self._capabilities.values())

    # ── Mutation ──────────────────────────────────────────────────────────────

    def add(self, capability: BrokerCapability) -> None:
        self._capabilities[capability.capability_type] = capability

    def remove(self, capability_type: BrokerCapabilityType) -> None:
        self._capabilities.pop(capability_type, None)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "capabilities": [c.to_dict() for c in self._capabilities.values()],
            "supported_count": len(self.all_supported()),
        }

    def __len__(self) -> int:
        return len(self._capabilities)

    def __contains__(self, capability_type: BrokerCapabilityType) -> bool:
        return self.supports(capability_type)
