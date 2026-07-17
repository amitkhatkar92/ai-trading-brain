"""iios/execution/gateway/routing/routing_candidate.py
==================================================
RoutingCandidate — mutable routing profile for a single broker.

Candidates are registered with the RoutingRegistry and updated
as broker health and connection state changes.

C6 Execution Intelligence — Phase 5, Module 4
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, FrozenSet, Optional

from iios.execution.gateway.brokers.broker_capabilities import BrokerCapabilities
from iios.execution.gateway.brokers.constants import BrokerCapability, ProductType

from .constants import CandidateStatus


class RoutingCandidate:
    """
    Thread-safe routing profile for a single broker.

    Updated externally as broker state changes (health checks,
    connection events).  The routing engine evaluates candidates
    without communicating with brokers.
    """

    __slots__ = (
        "_broker_id",
        "_broker_name",
        "_is_connected",
        "_is_authenticated",
        "_capabilities",
        "_health_score",
        "_routing_priority",
        "_weight",
        "_is_blacklisted",
        "_supported_exchanges",
        "_supported_products",
        "_registered_at",
        "_last_updated_at",
        "_lock",
    )

    def __init__(
        self,
        broker_id:           str,
        broker_name:         str,
        capabilities:        BrokerCapabilities,
        *,
        is_connected:        bool                   = False,
        is_authenticated:    bool                   = False,
        health_score:        float                  = 1.0,
        routing_priority:    int                    = 0,
        weight:              float                  = 1.0,
        supported_exchanges: FrozenSet[str]         = frozenset(),
        supported_products:  FrozenSet[ProductType] = frozenset(),
    ) -> None:
        self._broker_id         = broker_id
        self._broker_name       = broker_name
        self._is_connected      = is_connected
        self._is_authenticated  = is_authenticated
        self._capabilities      = capabilities
        self._health_score      = max(0.0, min(1.0, health_score))
        self._routing_priority  = routing_priority
        self._weight            = max(0.0, weight)
        self._is_blacklisted    = False
        self._supported_exchanges: FrozenSet[str]         = supported_exchanges
        self._supported_products:  FrozenSet[ProductType] = supported_products
        self._registered_at     = time.time()
        self._last_updated_at   = time.time()
        self._lock              = threading.RLock()

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    def broker_id(self) -> str:
        return self._broker_id

    @property
    def broker_name(self) -> str:
        return self._broker_name

    # ── Status ────────────────────────────────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        with self._lock:
            return self._is_connected

    @property
    def is_authenticated(self) -> bool:
        with self._lock:
            return self._is_authenticated

    @property
    def is_blacklisted(self) -> bool:
        with self._lock:
            return self._is_blacklisted

    @property
    def is_available(self) -> bool:
        """True when connected, authenticated, and not blacklisted."""
        with self._lock:
            return (
                self._is_connected
                and self._is_authenticated
                and not self._is_blacklisted
            )

    @property
    def status(self) -> CandidateStatus:
        with self._lock:
            if self._is_blacklisted:
                return CandidateStatus.BLACKLISTED
            if not self._is_connected or not self._is_authenticated:
                return CandidateStatus.UNAVAILABLE
            if self._health_score < 0.5:
                return CandidateStatus.DEGRADED
            return CandidateStatus.AVAILABLE

    # ── Capabilities ──────────────────────────────────────────────────────────

    @property
    def capabilities(self) -> BrokerCapabilities:
        return self._capabilities

    def supports_capability(self, cap: BrokerCapability) -> bool:
        return self._capabilities.has(cap)

    def supports_exchange(self, exchange: str) -> bool:
        with self._lock:
            return (
                not self._supported_exchanges          # empty = all exchanges
                or exchange in self._supported_exchanges
            )

    def supports_product(self, product: ProductType) -> bool:
        with self._lock:
            return (
                not self._supported_products           # empty = all products
                or product in self._supported_products
            )

    # ── Metrics ───────────────────────────────────────────────────────────────

    @property
    def health_score(self) -> float:
        with self._lock:
            return self._health_score

    @property
    def routing_priority(self) -> int:
        with self._lock:
            return self._routing_priority

    @property
    def weight(self) -> float:
        with self._lock:
            return self._weight

    @property
    def supported_exchanges(self) -> FrozenSet[str]:
        with self._lock:
            return self._supported_exchanges

    @property
    def supported_products(self) -> FrozenSet[ProductType]:
        with self._lock:
            return self._supported_products

    @property
    def registered_at(self) -> float:
        return self._registered_at

    @property
    def last_updated_at(self) -> float:
        with self._lock:
            return self._last_updated_at

    # ── Mutations ─────────────────────────────────────────────────────────────

    def update_health(self, health_score: float) -> None:
        with self._lock:
            self._health_score    = max(0.0, min(1.0, health_score))
            self._last_updated_at = time.time()

    def update_status(self, is_connected: bool, is_authenticated: bool) -> None:
        with self._lock:
            self._is_connected     = is_connected
            self._is_authenticated = is_authenticated
            self._last_updated_at  = time.time()

    def update_priority(self, priority: int) -> None:
        with self._lock:
            self._routing_priority = priority
            self._last_updated_at  = time.time()

    def update_weight(self, weight: float) -> None:
        with self._lock:
            self._weight          = max(0.0, weight)
            self._last_updated_at = time.time()

    def blacklist(self) -> None:
        with self._lock:
            self._is_blacklisted  = True
            self._last_updated_at = time.time()

    def unblacklist(self) -> None:
        with self._lock:
            self._is_blacklisted  = False
            self._last_updated_at = time.time()

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "broker_id":          self._broker_id,
                "broker_name":        self._broker_name,
                "is_connected":       self._is_connected,
                "is_authenticated":   self._is_authenticated,
                "is_available":       self.is_available,
                "is_blacklisted":     self._is_blacklisted,
                "health_score":       self._health_score,
                "routing_priority":   self._routing_priority,
                "weight":             self._weight,
                "capabilities":       self._capabilities.to_list(),
                "supported_exchanges": sorted(self._supported_exchanges),
                "supported_products":  sorted(p.value for p in self._supported_products),
                "status":             self.status.value,
                "registered_at":      self._registered_at,
                "last_updated_at":    self._last_updated_at,
            }

    def __repr__(self) -> str:
        return (
            f"RoutingCandidate("
            f"broker_id={self._broker_id!r}, "
            f"available={self.is_available}, "
            f"health={self._health_score:.2f}"
            f")"
        )
