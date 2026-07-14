"""iios/investment/portfolio/core/portfolio_catalog.py

Searchable catalog of registered portfolio templates and implementations.
The catalog layer sits above the registry and adds search, filtering,
and recommendation capabilities.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

from iios.investment.portfolio.core.portfolio_registry import (
    PortfolioClassEntry,
    PortfolioClassRegistry,
)
from iios.investment.portfolio.core.portfolio_types import (
    PortfolioCapability,
    PortfolioDomain,
)


@dataclass(frozen=True)
class CatalogEntry:
    """
    Enriched catalog view of a portfolio class.
    Combines registry metadata with catalog-specific attributes.
    """

    class_entry:   PortfolioClassEntry
    template_name: str                    = ""
    display_name:  str                    = ""
    summary:       str                    = ""
    use_cases:     tuple                  = field(default_factory=tuple)
    maturity:      str                    = "experimental"  # experimental | beta | stable | deprecated
    min_capital:   float                  = 0.0
    max_capital:   float                  = 1e12

    @property
    def class_name(self) -> str:
        return self.class_entry.class_name

    @property
    def domain(self) -> PortfolioDomain:
        return self.class_entry.domain

    @property
    def capabilities(self):
        return self.class_entry.capabilities

    @property
    def tags(self):
        return self.class_entry.tags

    @property
    def is_deprecated(self) -> bool:
        return self.class_entry.deprecated or self.maturity == "deprecated"

    @property
    def is_stable(self) -> bool:
        return self.maturity in ("stable",)

    def to_dict(self) -> dict[str, Any]:
        return {
            "class_name":   self.class_name,
            "template_name":self.template_name,
            "display_name": self.display_name,
            "summary":      self.summary,
            "domain":       self.domain.value,
            "maturity":     self.maturity,
            "capabilities": sorted(c.value for c in self.capabilities),
            "tags":         sorted(self.tags),
            "use_cases":    list(self.use_cases),
            "min_capital":  self.min_capital,
            "max_capital":  self.max_capital,
            "is_stable":    self.is_stable,
            "is_deprecated":self.is_deprecated,
        }


class PortfolioCatalog:
    """
    Thread-safe searchable catalog backed by a PortfolioClassRegistry.

    Supports:
    - Full-text search on name/description/tags
    - Domain filtering
    - Capability filtering
    - Maturity filtering
    - Capital suitability filtering
    """

    def __init__(self, registry: PortfolioClassRegistry) -> None:
        self._registry    = registry
        self._lock        = threading.RLock()
        self._extra:      dict[str, CatalogEntry] = {}  # class_name → additional catalog data

    # ------------------------------------------------------------------
    # Catalog entry management
    # ------------------------------------------------------------------

    def add_entry(
        self,
        class_name:   str,
        *,
        template_name:str  = "",
        display_name:  str  = "",
        summary:       str  = "",
        use_cases:     tuple = (),
        maturity:      str  = "experimental",
        min_capital:   float = 0.0,
        max_capital:   float = 1e12,
        overwrite:     bool = False,
    ) -> CatalogEntry:
        """Annotate a registered class with catalog metadata."""
        entry = self._registry.get_entry(class_name)  # raises if not registered
        ce = CatalogEntry(
            class_entry   = entry,
            template_name = template_name or class_name,
            display_name  = display_name  or class_name,
            summary       = summary,
            use_cases     = use_cases,
            maturity      = maturity,
            min_capital   = min_capital,
            max_capital   = max_capital,
        )
        with self._lock:
            if class_name in self._extra and not overwrite:
                raise ValueError(f"Catalog entry already exists: {class_name!r}")
            self._extra[class_name] = ce
        return ce

    def get_entry(self, class_name: str) -> Optional[CatalogEntry]:
        """Return catalog entry if present, else None."""
        with self._lock:
            if class_name in self._extra:
                return self._extra[class_name]
        # Fall back to registry-only entry
        try:
            reg_entry = self._registry.get_entry(class_name)
        except KeyError:
            return None
        return CatalogEntry(
            class_entry   = reg_entry,
            template_name = class_name,
            display_name  = class_name,
            maturity      = "stable",
        )

    # ------------------------------------------------------------------
    # Search / filter
    # ------------------------------------------------------------------

    def all_entries(self) -> List[CatalogEntry]:
        """Return all catalog entries (registry + enriched)."""
        results = []
        for entry in self._registry.all_entries():
            ce = self.get_entry(entry.class_name)
            if ce:
                results.append(ce)
        return results

    def search(
        self,
        query:         str                              = "",
        domain:        Optional[PortfolioDomain]        = None,
        capability:    Optional[PortfolioCapability]    = None,
        tag:           Optional[str]                    = None,
        maturity:      Optional[str]                    = None,
        min_capital:   Optional[float]                  = None,
        max_capital:   Optional[float]                  = None,
        include_deprecated: bool                        = False,
    ) -> List[CatalogEntry]:
        """
        Search the catalog.  All filters are AND-combined.
        query is matched against class_name, display_name, summary, and tags.
        """
        entries = self.all_entries()

        if not include_deprecated:
            entries = [e for e in entries if not e.is_deprecated]

        if query:
            q = query.lower()
            entries = [
                e for e in entries
                if q in e.class_name.lower()
                or q in e.display_name.lower()
                or q in e.summary.lower()
                or any(q in t.lower() for t in e.tags)
            ]

        if domain is not None:
            entries = [e for e in entries if e.domain == domain]

        if capability is not None:
            entries = [e for e in entries if capability in e.capabilities]

        if tag is not None:
            entries = [e for e in entries if tag in e.tags]

        if maturity is not None:
            entries = [e for e in entries if e.maturity == maturity]

        if min_capital is not None:
            entries = [e for e in entries if e.max_capital >= min_capital]

        if max_capital is not None:
            entries = [e for e in entries if e.min_capital <= max_capital]

        return entries

    def by_domain(self, domain: PortfolioDomain) -> List[CatalogEntry]:
        return self.search(domain=domain)

    def stable_entries(self) -> List[CatalogEntry]:
        return self.search(maturity="stable")

    def count(self) -> int:
        return len(self._registry.all_class_names())
