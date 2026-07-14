"""iios/investment/portfolio/core/portfolio_state.py

Runtime state management for the Institutional Portfolio Framework.
PortfolioStateStore is the mutable, thread-safe state container.
PortfolioStateSnapshot is the immutable point-in-time view.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.investment.portfolio.core.portfolio_types import PortfolioLifecycleState


@dataclass(frozen=True)
class PortfolioStateSnapshot:
    """
    Immutable snapshot of portfolio runtime state.
    Created by PortfolioStateStore.snapshot() for safe sharing.
    """

    snapshot_id:      str                    = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:     str                    = ""
    lifecycle_state:  PortfolioLifecycleState= PortfolioLifecycleState.REGISTERED
    version:          int                    = 0
    is_configured:    bool                   = False
    is_validated:     bool                   = False
    is_prepared:      bool                   = False
    is_constructed:   bool                   = False

    # Operational metrics (framework-tracked, not computed by analytics)
    last_initialize_at:  Optional[float] = None
    last_construct_at:   Optional[float] = None
    last_allocate_at:    Optional[float] = None
    last_rebalance_at:   Optional[float] = None
    last_evaluate_at:    Optional[float] = None
    last_monitor_at:     Optional[float] = None
    last_publish_at:     Optional[float] = None

    # Counters
    initialize_count:    int = 0
    rebalance_count:     int = 0
    evaluate_count:      int = 0
    monitor_count:       int = 0
    error_count:         int = 0

    # Timestamps
    created_at:          float = field(default_factory=time.time)
    updated_at:          float = field(default_factory=time.time)

    # Error tracking
    last_error:          Optional[str] = None
    last_error_at:       Optional[float] = None

    # Custom state bag (serialisable values only)
    attributes:          dict[str, Any] = field(default_factory=dict)

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at

    @property
    def seconds_since_rebalance(self) -> Optional[float]:
        if self.last_rebalance_at is None:
            return None
        return time.time() - self.last_rebalance_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id":       self.snapshot_id,
            "portfolio_id":      self.portfolio_id,
            "lifecycle_state":   self.lifecycle_state.value,
            "version":           self.version,
            "is_configured":     self.is_configured,
            "is_validated":      self.is_validated,
            "is_prepared":       self.is_prepared,
            "is_constructed":    self.is_constructed,
            "rebalance_count":   self.rebalance_count,
            "evaluate_count":    self.evaluate_count,
            "error_count":       self.error_count,
            "last_error":        self.last_error,
            "created_at":        self.created_at,
            "updated_at":        self.updated_at,
            "attributes":        dict(self.attributes),
        }


class PortfolioStateStore:
    """
    Mutable, thread-safe container for a single portfolio's runtime state.
    All mutations are version-incremented and timestamped.
    """

    __slots__ = (
        "_lock", "_portfolio_id", "_lifecycle_state", "_version",
        "_is_configured", "_is_validated", "_is_prepared", "_is_constructed",
        "_last_initialize_at", "_last_construct_at", "_last_allocate_at",
        "_last_rebalance_at", "_last_evaluate_at", "_last_monitor_at", "_last_publish_at",
        "_initialize_count", "_rebalance_count", "_evaluate_count", "_monitor_count",
        "_error_count", "_created_at", "_updated_at",
        "_last_error", "_last_error_at", "_attributes",
    )

    def __init__(self, portfolio_id: str) -> None:
        self._lock            = threading.RLock()
        self._portfolio_id    = portfolio_id
        self._lifecycle_state = PortfolioLifecycleState.REGISTERED
        self._version         = 0
        self._is_configured   = False
        self._is_validated    = False
        self._is_prepared     = False
        self._is_constructed  = False

        self._last_initialize_at: Optional[float] = None
        self._last_construct_at:  Optional[float] = None
        self._last_allocate_at:   Optional[float] = None
        self._last_rebalance_at:  Optional[float] = None
        self._last_evaluate_at:   Optional[float] = None
        self._last_monitor_at:    Optional[float] = None
        self._last_publish_at:    Optional[float] = None

        self._initialize_count = 0
        self._rebalance_count  = 0
        self._evaluate_count   = 0
        self._monitor_count    = 0
        self._error_count      = 0

        self._created_at       = time.time()
        self._updated_at       = time.time()
        self._last_error:      Optional[str]   = None
        self._last_error_at:   Optional[float] = None
        self._attributes:      dict[str, Any]  = {}

    # ------------------------------------------------------------------
    # Setters
    # ------------------------------------------------------------------

    def set_lifecycle_state(self, state: PortfolioLifecycleState) -> None:
        with self._lock:
            self._lifecycle_state = state
            self._bump()

    def mark_configured(self) -> None:
        with self._lock:
            self._is_configured = True
            self._bump()

    def mark_validated(self) -> None:
        with self._lock:
            self._is_validated = True
            self._bump()

    def mark_prepared(self) -> None:
        with self._lock:
            self._is_prepared = True
            self._bump()

    def mark_constructed(self) -> None:
        with self._lock:
            self._is_constructed = True
            self._last_construct_at = time.time()
            self._bump()

    def record_initialize(self) -> None:
        with self._lock:
            self._initialize_count += 1
            self._last_initialize_at = time.time()
            self._bump()

    def record_rebalance(self) -> None:
        with self._lock:
            self._rebalance_count += 1
            self._last_rebalance_at = time.time()
            self._bump()

    def record_evaluate(self) -> None:
        with self._lock:
            self._evaluate_count += 1
            self._last_evaluate_at = time.time()
            self._bump()

    def record_monitor(self) -> None:
        with self._lock:
            self._monitor_count += 1
            self._last_monitor_at = time.time()
            self._bump()

    def record_publish(self) -> None:
        with self._lock:
            self._last_publish_at = time.time()
            self._bump()

    def record_allocate(self) -> None:
        with self._lock:
            self._last_allocate_at = time.time()
            self._bump()

    def record_error(self, message: str) -> None:
        with self._lock:
            self._error_count  += 1
            self._last_error    = message
            self._last_error_at = time.time()
            self._bump()

    def set_attribute(self, key: str, value: Any) -> None:
        with self._lock:
            self._attributes[key] = value
            self._bump()

    def clear_error(self) -> None:
        with self._lock:
            self._last_error    = None
            self._last_error_at = None
            self._bump()

    # ------------------------------------------------------------------
    # Getters
    # ------------------------------------------------------------------

    @property
    def lifecycle_state(self) -> PortfolioLifecycleState:
        with self._lock:
            return self._lifecycle_state

    @property
    def version(self) -> int:
        with self._lock:
            return self._version

    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    def snapshot(self) -> PortfolioStateSnapshot:
        with self._lock:
            return PortfolioStateSnapshot(
                portfolio_id       = self._portfolio_id,
                lifecycle_state    = self._lifecycle_state,
                version            = self._version,
                is_configured      = self._is_configured,
                is_validated       = self._is_validated,
                is_prepared        = self._is_prepared,
                is_constructed     = self._is_constructed,
                last_initialize_at = self._last_initialize_at,
                last_construct_at  = self._last_construct_at,
                last_allocate_at   = self._last_allocate_at,
                last_rebalance_at  = self._last_rebalance_at,
                last_evaluate_at   = self._last_evaluate_at,
                last_monitor_at    = self._last_monitor_at,
                last_publish_at    = self._last_publish_at,
                initialize_count   = self._initialize_count,
                rebalance_count    = self._rebalance_count,
                evaluate_count     = self._evaluate_count,
                monitor_count      = self._monitor_count,
                error_count        = self._error_count,
                created_at         = self._created_at,
                updated_at         = self._updated_at,
                last_error         = self._last_error,
                last_error_at      = self._last_error_at,
                attributes         = dict(self._attributes),
            )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _bump(self) -> None:
        self._version    += 1
        self._updated_at  = time.time()
