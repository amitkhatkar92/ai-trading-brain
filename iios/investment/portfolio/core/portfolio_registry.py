"""iios/investment/portfolio/core/portfolio_registry.py

Framework-level class registry for the Institutional Portfolio Framework.
Registers portfolio CLASS OBJECTS (not instances) for discovery and factory use.

This is distinct from the parent-package portfolio_registry.py which manages
portfolio INSTANCES.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Type, TYPE_CHECKING

from iios.investment.portfolio.core.portfolio_types import (
    PortfolioCapability,
    PortfolioDomain,
)

if TYPE_CHECKING:
    from iios.investment.portfolio.core.base_portfolio import BasePortfolio


class PortfolioClassRegistrationError(ValueError):
    """Raised on duplicate or invalid class registration."""


class PortfolioClassNotFoundError(KeyError):
    """Raised when a requested portfolio class is not registered."""


@dataclass(frozen=True)
class PortfolioClassEntry:
    """
    Metadata record for a registered portfolio class.
    Immutable — a new entry is created for each version update.
    """

    entry_id:       str                         = field(default_factory=lambda: str(uuid.uuid4()))
    class_name:     str                         = ""
    module_path:    str                         = ""
    domain:         PortfolioDomain             = PortfolioDomain.CUSTOM
    version:        str                         = "1.0.0"
    description:    str                         = ""
    capabilities:   FrozenSet[PortfolioCapability] = field(default_factory=frozenset)
    tags:           FrozenSet[str]              = field(default_factory=frozenset)
    dependencies:   FrozenSet[str]              = field(default_factory=frozenset)
    is_abstract:    bool                        = False
    registered_at:  float                       = field(default_factory=time.time)
    registered_by:  str                         = "framework"
    deprecated:     bool                        = False
    replaces:       Optional[str]               = None   # name of class this supersedes

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id":      self.entry_id,
            "class_name":    self.class_name,
            "module_path":   self.module_path,
            "domain":        self.domain.value,
            "version":       self.version,
            "description":   self.description,
            "capabilities":  sorted(c.value for c in self.capabilities),
            "tags":          sorted(self.tags),
            "dependencies":  sorted(self.dependencies),
            "is_abstract":   self.is_abstract,
            "registered_at": self.registered_at,
            "deprecated":    self.deprecated,
            "replaces":      self.replaces,
        }


class PortfolioClassRegistry:
    """
    Thread-safe registry of portfolio class objects.

    Maps a registration key (typically class_name or domain+name) to:
    - The Python class object
    - Its PortfolioClassEntry metadata

    Supports versioning: registering the same class_name with a new
    version supersedes the old entry (old entry moved to _deprecated).
    """

    def __init__(self) -> None:
        self._lock:       threading.RLock                                  = threading.RLock()
        self._entries:    Dict[str, PortfolioClassEntry]                    = {}
        self._classes:    Dict[str, Type["BasePortfolio"]]                  = {}
        self._deprecated: List[PortfolioClassEntry]                         = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        cls:          Type["BasePortfolio"],
        *,
        class_name:   str                       = "",
        domain:       PortfolioDomain           = PortfolioDomain.CUSTOM,
        version:      str                       = "1.0.0",
        description:  str                       = "",
        capabilities: Optional[FrozenSet[PortfolioCapability]] = None,
        tags:         Optional[FrozenSet[str]]  = None,
        dependencies: Optional[FrozenSet[str]]  = None,
        is_abstract:  bool                      = False,
        registered_by:str                       = "framework",
        overwrite:    bool                      = False,
    ) -> PortfolioClassEntry:
        """
        Register *cls* under *class_name* (defaults to cls.__name__).
        If class_name already exists and overwrite=True, the old entry
        is moved to deprecated history.
        """
        key = class_name or cls.__name__
        entry = PortfolioClassEntry(
            class_name    = key,
            module_path   = f"{cls.__module__}.{cls.__qualname__}",
            domain        = domain,
            version       = version,
            description   = description,
            capabilities  = capabilities or frozenset(),
            tags          = tags or frozenset(),
            dependencies  = dependencies or frozenset(),
            is_abstract   = is_abstract,
            registered_by = registered_by,
        )
        with self._lock:
            if key in self._entries and not overwrite:
                raise PortfolioClassRegistrationError(
                    f"Portfolio class already registered: {key!r}. "
                    f"Use overwrite=True to supersede."
                )
            if key in self._entries:
                self._deprecated.append(self._entries[key])
            self._entries[key] = entry
            self._classes[key] = cls
        return entry

    def unregister(self, class_name: str) -> bool:
        """Remove a registration. Returns True if it existed."""
        with self._lock:
            if class_name in self._entries:
                old = self._entries.pop(class_name)
                self._classes.pop(class_name, None)
                self._deprecated.append(old)
                return True
            return False

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get_class(self, class_name: str) -> Type["BasePortfolio"]:
        with self._lock:
            if class_name not in self._classes:
                raise PortfolioClassNotFoundError(
                    f"Portfolio class not registered: {class_name!r}"
                )
            return self._classes[class_name]

    def get_entry(self, class_name: str) -> PortfolioClassEntry:
        with self._lock:
            if class_name not in self._entries:
                raise PortfolioClassNotFoundError(
                    f"Portfolio class not registered: {class_name!r}"
                )
            return self._entries[class_name]

    def get(self, class_name: str) -> Optional[Type["BasePortfolio"]]:
        with self._lock:
            return self._classes.get(class_name)

    def is_registered(self, class_name: str) -> bool:
        with self._lock:
            return class_name in self._entries

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def all_class_names(self) -> List[str]:
        with self._lock:
            return sorted(self._entries.keys())

    def by_domain(self, domain: PortfolioDomain) -> List[PortfolioClassEntry]:
        with self._lock:
            return [e for e in self._entries.values() if e.domain == domain]

    def by_capability(self, cap: PortfolioCapability) -> List[PortfolioClassEntry]:
        with self._lock:
            return [e for e in self._entries.values() if cap in e.capabilities]

    def by_tag(self, tag: str) -> List[PortfolioClassEntry]:
        with self._lock:
            return [e for e in self._entries.values() if tag in e.tags]

    def active_count(self) -> int:
        with self._lock:
            return len(self._entries)

    def all_entries(self) -> List[PortfolioClassEntry]:
        with self._lock:
            return list(self._entries.values())
