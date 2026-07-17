"""iios/execution/gateway/brokers/broker_capabilities.py
==================================================
BrokerCapabilities — immutable capability set for a broker.

Encapsulates the set of features and product types a broker
implementation exposes.  Used for capability discovery and
routing decisions.

C6 Execution Intelligence — Phase 5, Module 3
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Iterable, List

from .constants import BrokerCapability


# ── Sentinel ──────────────────────────────────────────────────────────────────

ALL_CAPABILITIES: FrozenSet[BrokerCapability] = frozenset(BrokerCapability)
"""Convenience sentinel containing every defined capability."""


# ── BrokerCapabilities ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BrokerCapabilities:
    """
    Immutable set of capabilities declared by a broker.

    Construction
    ------------
    caps = BrokerCapabilities(frozenset({
        BrokerCapability.CASH_TRADING,
        BrokerCapability.MIS,
        BrokerCapability.CNC,
        BrokerCapability.ORDER_MODIFICATION,
        BrokerCapability.ORDER_CANCELLATION,
    }))
    """

    capabilities: FrozenSet[BrokerCapability] = field(default_factory=frozenset)

    # ── Queries ───────────────────────────────────────────────────────────────

    def has(self, capability: BrokerCapability) -> bool:
        """Return True if this broker supports the given capability."""
        return capability in self.capabilities

    def supports_all(self, *capabilities: BrokerCapability) -> bool:
        """Return True if all supplied capabilities are supported."""
        return all(c in self.capabilities for c in capabilities)

    def supports_any(self, *capabilities: BrokerCapability) -> bool:
        """Return True if at least one supplied capability is supported."""
        return any(c in self.capabilities for c in capabilities)

    def missing(self, *required: BrokerCapability) -> FrozenSet[BrokerCapability]:
        """Return the subset of *required* capabilities that are absent."""
        return frozenset(c for c in required if c not in self.capabilities)

    # ── Set operations ────────────────────────────────────────────────────────

    def union(self, other: BrokerCapabilities) -> BrokerCapabilities:
        """Return a new BrokerCapabilities with the union of both sets."""
        return BrokerCapabilities(self.capabilities | other.capabilities)

    def intersection(self, other: BrokerCapabilities) -> BrokerCapabilities:
        """Return a new BrokerCapabilities with the intersection of both sets."""
        return BrokerCapabilities(self.capabilities & other.capabilities)

    def to_list(self) -> List[str]:
        """Return a sorted list of capability names."""
        return sorted(c.value for c in self.capabilities)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capabilities": self.to_list(),
            "count": len(self.capabilities),
        }

    # ── Dunder ────────────────────────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self.capabilities)

    def __contains__(self, capability: object) -> bool:
        return capability in self.capabilities

    def __repr__(self) -> str:
        return f"BrokerCapabilities({self.to_list()})"


# ── Factory helpers ───────────────────────────────────────────────────────────

def make_capabilities(*capabilities: BrokerCapability) -> BrokerCapabilities:
    """Create a BrokerCapabilities from positional capability arguments."""
    return BrokerCapabilities(frozenset(capabilities))


def make_capabilities_from_iterable(
    capabilities: Iterable[BrokerCapability],
) -> BrokerCapabilities:
    """Create a BrokerCapabilities from any iterable."""
    return BrokerCapabilities(frozenset(capabilities))


def find_brokers_by_capability(
    broker_capabilities_map: Dict[str, BrokerCapabilities],
    capability: BrokerCapability,
) -> List[str]:
    """
    Return the list of broker IDs that support the given capability.

    Parameters
    ----------
    broker_capabilities_map:
        Mapping of ``broker_id → BrokerCapabilities``.
    capability:
        The capability to search for.
    """
    return [
        bid for bid, caps in broker_capabilities_map.items()
        if caps.has(capability)
    ]
