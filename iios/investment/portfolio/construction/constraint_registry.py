"""iios/investment/portfolio/construction/constraint_registry.py

Thread-safe registry of ConstraintDefinition objects.
"""
from __future__ import annotations

import threading
from typing import Dict, Iterator, List, Optional, Type

from iios.investment.portfolio.construction.construction_constraints import ConstraintDefinition
from iios.investment.portfolio.construction.construction_types import (
    ConstraintSeverity,
    ConstraintType,
)


class ConstraintRegistryError(ValueError):
    pass


class ConstraintRegistry:
    """
    Thread-safe, named registry of ConstraintDefinition instances.

    Portfolios register their applicable constraints here; the
    ConstraintEngine reads from this registry when evaluating a blueprint.
    """

    __slots__ = ("_store", "_lock")

    def __init__(self) -> None:
        self._store: Dict[str, ConstraintDefinition] = {}
        self._lock  = threading.RLock()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def register(
        self,
        constraint: ConstraintDefinition,
        *,
        overwrite: bool = False,
    ) -> ConstraintDefinition:
        """Register a constraint.  Raises ConstraintRegistryError on duplicate unless overwrite=True."""
        with self._lock:
            if constraint.name in self._store and not overwrite:
                raise ConstraintRegistryError(
                    f"Constraint '{constraint.name}' already registered. Use overwrite=True."
                )
            self._store[constraint.name] = constraint
        return constraint

    def unregister(self, name: str) -> bool:
        """Remove a constraint by name.  Returns True if it existed."""
        with self._lock:
            return self._store.pop(name, None) is not None

    def enable(self, name: str) -> None:
        """Enable a previously registered constraint (no-op if not found)."""
        # ConstraintDefinitions are frozen; we must replace.
        with self._lock:
            c = self._store.get(name)
            if c and not c.enabled:
                import dataclasses as _dc
                self._store[name] = _dc.replace(c, enabled=True)

    def disable(self, name: str) -> None:
        with self._lock:
            c = self._store.get(name)
            if c and c.enabled:
                import dataclasses as _dc
                self._store[name] = _dc.replace(c, enabled=False)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, name: str) -> Optional[ConstraintDefinition]:
        with self._lock:
            return self._store.get(name)

    def all(self) -> List[ConstraintDefinition]:
        with self._lock:
            return list(self._store.values())

    def active(self) -> List[ConstraintDefinition]:
        """Return only enabled constraints."""
        with self._lock:
            return [c for c in self._store.values() if c.enabled]

    def by_type(self, ctype: ConstraintType) -> List[ConstraintDefinition]:
        with self._lock:
            return [c for c in self._store.values() if c.constraint_type == ctype]

    def by_severity(self, severity: ConstraintSeverity) -> List[ConstraintDefinition]:
        with self._lock:
            return [c for c in self._store.values() if c.severity == severity]

    def hard_constraints(self) -> List[ConstraintDefinition]:
        return self.by_severity(ConstraintSeverity.HARD)

    def soft_constraints(self) -> List[ConstraintDefinition]:
        return self.by_severity(ConstraintSeverity.SOFT)

    def is_registered(self, name: str) -> bool:
        with self._lock:
            return name in self._store

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for c in self._store.values() if c.enabled)

    def names(self) -> List[str]:
        with self._lock:
            return sorted(self._store.keys())

    def reset(self) -> None:
        with self._lock:
            self._store.clear()

    def __iter__(self) -> Iterator[ConstraintDefinition]:
        with self._lock:
            return iter(list(self._store.values()))

    def __len__(self) -> int:
        return self.count()
