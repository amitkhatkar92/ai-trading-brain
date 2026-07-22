"""
portfolio_component_registry.py — iios.portfolio.integration
=============================================================
PortfolioComponentRegistry — thread-safe registry for the five
integrated portfolio subsystem components.

C10 Portfolio Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from typing import Any, Dict, Optional, TYPE_CHECKING

from .constants import ComponentType

# Use TYPE_CHECKING to avoid circular imports at runtime
if TYPE_CHECKING:
    from iios.portfolio.lifecycle import PortfolioLifecycle
    from iios.portfolio.engine import PortfolioEngine
    from iios.portfolio.policies import PortfolioPolicyEngine
    from iios.portfolio.optimization import PortfolioOptimizationEngine
    from iios.portfolio.snapshot import PortfolioSnapshotRegistry


class PortfolioComponentRegistry:
    """
    Thread-safe registry that holds references to all five integrated
    portfolio subsystem components.

    Components are optional; callers must check ``is_available(component_type)``
    before use.  The integration engine skips unavailable components and
    records partial results.
    """

    def __init__(self) -> None:
        self._lock         = threading.Lock()
        self._lifecycle    = None   # Optional[PortfolioLifecycle]
        self._engine       = None   # Optional[PortfolioEngine]
        self._policy       = None   # Optional[PortfolioPolicyEngine]
        self._optimization = None   # Optional[PortfolioOptimizationEngine]
        self._snapshot     = None   # Optional[PortfolioSnapshotRegistry]

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_lifecycle(self, component: Any) -> None:
        with self._lock:
            self._lifecycle = component

    def register_engine(self, component: Any) -> None:
        with self._lock:
            self._engine = component

    def register_policy(self, component: Any) -> None:
        with self._lock:
            self._policy = component

    def register_optimization(self, component: Any) -> None:
        with self._lock:
            self._optimization = component

    def register_snapshot(self, component: Any) -> None:
        with self._lock:
            self._snapshot = component

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_lifecycle(self) -> Optional[Any]:
        with self._lock:
            return self._lifecycle

    def get_engine(self) -> Optional[Any]:
        with self._lock:
            return self._engine

    def get_policy(self) -> Optional[Any]:
        with self._lock:
            return self._policy

    def get_optimization(self) -> Optional[Any]:
        with self._lock:
            return self._optimization

    def get_snapshot_registry(self) -> Optional[Any]:
        with self._lock:
            return self._snapshot

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    def is_available(self, component_type: ComponentType) -> bool:
        with self._lock:
            return self._get_raw(component_type) is not None

    def is_ready(self) -> bool:
        """
        True when all five components are registered and running.

        A component is considered running when its
        ``lifecycle_state().value == "running"`` is True.
        Components without a ``lifecycle_state`` method are considered
        running if they are non-None.
        """
        with self._lock:
            for comp in (
                self._lifecycle,
                self._engine,
                self._policy,
                self._optimization,
                self._snapshot,
            ):
                if comp is None:
                    return False
                if hasattr(comp, "lifecycle_state"):
                    try:
                        if comp.lifecycle_state().value != "running":
                            return False
                    except Exception:
                        return False
        return True

    def available_count(self) -> int:
        with self._lock:
            return sum(
                1 for c in (
                    self._lifecycle, self._engine, self._policy,
                    self._optimization, self._snapshot,
                )
                if c is not None
            )

    def status_dict(self) -> Dict[str, bool]:
        """Return dict of component_type → is_available."""
        with self._lock:
            return {
                ComponentType.LIFECYCLE.value:    self._lifecycle is not None,
                ComponentType.ENGINE.value:       self._engine is not None,
                ComponentType.POLICY.value:       self._policy is not None,
                ComponentType.OPTIMIZATION.value: self._optimization is not None,
                ComponentType.SNAPSHOT.value:     self._snapshot is not None,
            }

    def clear(self) -> None:
        with self._lock:
            self._lifecycle    = None
            self._engine       = None
            self._policy       = None
            self._optimization = None
            self._snapshot     = None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_raw(self, component_type: ComponentType) -> Optional[Any]:
        """Return raw component reference (caller must hold _lock)."""
        return {
            ComponentType.LIFECYCLE:    self._lifecycle,
            ComponentType.ENGINE:       self._engine,
            ComponentType.POLICY:       self._policy,
            ComponentType.OPTIMIZATION: self._optimization,
            ComponentType.SNAPSHOT:     self._snapshot,
        }.get(component_type)
