"""
market_component_registry.py — iios.market.integration
========================================================
Registry that tracks the Market Intelligence subsystem component instances.

Provides a single source of truth for which components are registered,
their current availability, and their lifecycle state.

C12 Market Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Optional

from .constants import ComponentStatus


class ComponentRecord:
    """Lightweight record for a single registered component."""

    __slots__ = ("name", "component", "status", "registered_at")

    def __init__(self, name: str, component: Any) -> None:
        self.name:          str             = name
        self.component:     Any             = component
        self.status:        ComponentStatus = ComponentStatus.AVAILABLE
        self.registered_at: float           = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":          self.name,
            "status":        self.status.value,
            "type":          type(self.component).__name__,
            "registered_at": self.registered_at,
        }


class MarketComponentRegistry:
    """
    Thread-safe registry of Market Intelligence subsystem component instances.

    Components are registered by name (see ``constants.COMPONENT_*`` constants).
    The registry does NOT start or stop components — the engine manages that.
    """

    def __init__(self) -> None:
        self._lock:    threading.RLock            = threading.RLock()
        self._records: Dict[str, ComponentRecord] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, name: str, component: Any) -> None:
        """Register a component instance under *name*."""
        with self._lock:
            self._records[name] = ComponentRecord(name, component)

    def unregister(self, name: str) -> bool:
        with self._lock:
            if name in self._records:
                del self._records[name]
                return True
            return False

    def set_status(self, name: str, status: ComponentStatus) -> None:
        with self._lock:
            if name in self._records:
                self._records[name].status = status

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get(self, name: str) -> Optional[Any]:
        with self._lock:
            record = self._records.get(name)
            return record.component if record else None

    def is_registered(self, name: str) -> bool:
        with self._lock:
            return name in self._records

    def is_available(self, name: str) -> bool:
        with self._lock:
            record = self._records.get(name)
            return (
                record is not None
                and record.status == ComponentStatus.AVAILABLE
            )

    def status(self, name: str) -> ComponentStatus:
        with self._lock:
            record = self._records.get(name)
            return record.status if record else ComponentStatus.UNKNOWN

    def all_names(self) -> List[str]:
        with self._lock:
            return list(self._records.keys())

    def all_components(self) -> Dict[str, Any]:
        with self._lock:
            return {name: rec.component for name, rec in self._records.items()}

    def health_summary(self) -> Dict[str, str]:
        """Return a dict of component_name → status_value string."""
        with self._lock:
            return {
                name: rec.status.value
                for name, rec in self._records.items()
            }

    def count(self) -> int:
        with self._lock:
            return len(self._records)

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
