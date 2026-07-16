"""iios/execution/brokers/broker_metadata.py
==================================================
BrokerMetadata — static description of a broker's identity,
supported products, exchanges, order types, and rate limits.

C6 Execution Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.brokers.constants import (
    BrokerCapabilityCode,
    BrokerMode,
    Exchange,
    ProductType,
    TimeInForce,
    VERSION,
)


@dataclass(frozen=True)
class RateLimitSpec:
    """Describes a single rate-limit bucket."""

    requests_per_second: float = 10.0
    requests_per_minute: int   = 300
    requests_per_day:    int   = 100_000
    concurrent_requests: int   = 5

    def to_dict(self) -> dict[str, Any]:
        return {
            "requests_per_second": self.requests_per_second,
            "requests_per_minute": self.requests_per_minute,
            "requests_per_day":    self.requests_per_day,
            "concurrent_requests": self.concurrent_requests,
        }


@dataclass(frozen=True)
class BrokerMetadata:
    """
    Immutable description of a broker's identity and capabilities.

    Populated once during broker registration and never mutated.
    """

    broker_id:           str
    broker_name:         str
    broker_version:      str = "1.0.0"
    framework_version:   str = VERSION

    supported_modes:     frozenset[BrokerMode]            = field(
        default_factory=lambda: frozenset({BrokerMode.PAPER})
    )
    supported_exchanges: frozenset[Exchange]              = field(
        default_factory=frozenset
    )
    supported_products:  frozenset[ProductType]           = field(
        default_factory=frozenset
    )
    supported_tif:       frozenset[TimeInForce]           = field(
        default_factory=frozenset
    )
    capabilities:        frozenset[BrokerCapabilityCode]  = field(
        default_factory=frozenset
    )

    rate_limit:          RateLimitSpec = field(
        default_factory=RateLimitSpec
    )

    description: str = ""
    homepage:    str = ""
    contact:     str = ""
    metadata:    dict[str, Any] = field(default_factory=dict)

    registered_at: float = field(default_factory=time.time)
    metadata_id:   str   = field(default_factory=lambda: str(uuid.uuid4()))

    # ── Queries ───────────────────────────────────────────────────────────────

    def supports_mode(self, mode: BrokerMode) -> bool:
        return mode in self.supported_modes

    def supports_exchange(self, exchange: Exchange) -> bool:
        return exchange in self.supported_exchanges

    def supports_product(self, product: ProductType) -> bool:
        return product in self.supported_products

    def supports_tif(self, tif: TimeInForce) -> bool:
        return tif in self.supported_tif

    def has_capability(self, cap: BrokerCapabilityCode) -> bool:
        return cap in self.capabilities

    def missing_capabilities(
        self,
        required: frozenset[BrokerCapabilityCode],
    ) -> frozenset[BrokerCapabilityCode]:
        return required - self.capabilities

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "broker_id":           self.broker_id,
            "broker_name":         self.broker_name,
            "broker_version":      self.broker_version,
            "framework_version":   self.framework_version,
            "supported_modes":     sorted(m.value for m in self.supported_modes),
            "supported_exchanges": sorted(e.value for e in self.supported_exchanges),
            "supported_products":  sorted(p.value for p in self.supported_products),
            "supported_tif":       sorted(t.value for t in self.supported_tif),
            "capabilities":        sorted(c.value for c in self.capabilities),
            "rate_limit":          self.rate_limit.to_dict(),
            "description":         self.description,
            "registered_at":       self.registered_at,
            "metadata_id":         self.metadata_id,
        }

    def __repr__(self) -> str:
        caps = len(self.capabilities)
        modes = ", ".join(m.value for m in self.supported_modes)
        return (
            f"BrokerMetadata(id={self.broker_id!r}, name={self.broker_name!r}, "
            f"modes=[{modes}], capabilities={caps})"
        )
