"""iios/execution/brokers/broker_capabilities.py
==================================================
BrokerCapabilities — capability set for a registered broker,
with query and intersection helpers.

C6 Execution Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.execution.brokers.constants import (
    BrokerCapabilityCode,
    Exchange,
    ProductType,
    TimeInForce,
)


@dataclass(frozen=True)
class BrokerCapabilities:
    """
    Immutable capability descriptor for a single broker.

    Created from BrokerMetadata when a broker is registered.
    """

    broker_id:           str
    capabilities:        frozenset[BrokerCapabilityCode] = field(default_factory=frozenset)
    supported_exchanges: frozenset[Exchange]             = field(default_factory=frozenset)
    supported_products:  frozenset[ProductType]          = field(default_factory=frozenset)
    supported_tif:       frozenset[TimeInForce]          = field(default_factory=frozenset)

    # ── Single-item queries ───────────────────────────────────────────────────

    def has(self, cap: BrokerCapabilityCode) -> bool:
        """Return True if this broker has the given capability."""
        return cap in self.capabilities

    def supports_exchange(self, exchange: Exchange) -> bool:
        return exchange in self.supported_exchanges

    def supports_product(self, product: ProductType) -> bool:
        return product in self.supported_products

    def supports_tif(self, tif: TimeInForce) -> bool:
        return tif in self.supported_tif

    # ── Set queries ───────────────────────────────────────────────────────────

    def has_all(self, required: frozenset[BrokerCapabilityCode]) -> bool:
        """Return True if this broker has every capability in *required*."""
        return required.issubset(self.capabilities)

    def missing(
        self,
        required: frozenset[BrokerCapabilityCode],
    ) -> frozenset[BrokerCapabilityCode]:
        """Return the subset of *required* that this broker is missing."""
        return required - self.capabilities

    def intersection(
        self,
        other: "BrokerCapabilities",
    ) -> frozenset[BrokerCapabilityCode]:
        """Return capabilities common to both brokers."""
        return self.capabilities & other.capabilities

    def union(
        self,
        other: "BrokerCapabilities",
    ) -> frozenset[BrokerCapabilityCode]:
        """Return combined capabilities from both brokers."""
        return self.capabilities | other.capabilities

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "broker_id":           self.broker_id,
            "capabilities":        sorted(c.value for c in self.capabilities),
            "supported_exchanges": sorted(e.value for e in self.supported_exchanges),
            "supported_products":  sorted(p.value for p in self.supported_products),
            "supported_tif":       sorted(t.value for t in self.supported_tif),
        }

    def __repr__(self) -> str:
        return (
            f"BrokerCapabilities(broker_id={self.broker_id!r}, "
            f"capabilities={len(self.capabilities)})"
        )


def capabilities_from_metadata(metadata: Any) -> "BrokerCapabilities":
    """
    Build a BrokerCapabilities from a BrokerMetadata object.

    Accepts any object with the matching attributes so callers do not
    need a hard import of BrokerMetadata here (avoids circular imports).
    """
    return BrokerCapabilities(
        broker_id           = metadata.broker_id,
        capabilities        = metadata.capabilities,
        supported_exchanges = metadata.supported_exchanges,
        supported_products  = metadata.supported_products,
        supported_tif       = metadata.supported_tif,
    )
