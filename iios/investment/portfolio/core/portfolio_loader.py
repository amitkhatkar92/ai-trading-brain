"""iios/investment/portfolio/core/portfolio_loader.py

Dynamic portfolio class loader for the Institutional Portfolio Framework.
Loads portfolio implementations from Python modules at runtime and
registers them with the class registry.
"""
from __future__ import annotations

import importlib
import inspect
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Type

from iios.investment.portfolio.core.portfolio_registry import (
    PortfolioClassEntry,
    PortfolioClassRegistry,
)
from iios.investment.portfolio.core.portfolio_types import PortfolioDomain

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoadResult:
    """Outcome of a single portfolio class load operation."""

    result_id:   str               = field(default_factory=lambda: str(uuid.uuid4()))
    class_name:  str               = ""
    module_path: str               = ""
    success:     bool              = False
    entry:       Optional[PortfolioClassEntry] = None
    error:       str               = ""
    duration_ms: float             = 0.0
    loaded_at:   float             = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "result_id":   self.result_id,
            "class_name":  self.class_name,
            "module_path": self.module_path,
            "success":     self.success,
            "error":       self.error,
            "duration_ms": self.duration_ms,
        }


class PortfolioLoader:
    """
    Dynamically loads portfolio classes from Python modules.

    Provides:
    - Load a single class by dotted path (e.g. 'myapp.portfolios.SwingPortfolio')
    - Scan a module for all BasePortfolio subclasses
    - Batch loading with per-item error isolation
    """

    def __init__(self, registry: PortfolioClassRegistry) -> None:
        self._registry = registry

    # ------------------------------------------------------------------
    # Load one class
    # ------------------------------------------------------------------

    def load_class(
        self,
        dotted_path:  str,
        *,
        domain:       PortfolioDomain = PortfolioDomain.CUSTOM,
        version:      str             = "1.0.0",
        description:  str             = "",
        overwrite:    bool            = False,
    ) -> LoadResult:
        """
        Load a portfolio class from its fully-qualified dotted path.
        E.g.: 'myapp.portfolios.equity.LongTermPortfolio'
        """
        t0 = time.time()
        parts = dotted_path.rsplit(".", 1)
        if len(parts) != 2:
            return LoadResult(
                class_name  = dotted_path,
                module_path = dotted_path,
                success     = False,
                error       = f"Invalid dotted path: {dotted_path!r}",
                duration_ms = (time.time() - t0) * 1_000,
            )

        module_path, class_name = parts
        try:
            module = importlib.import_module(module_path)
        except ImportError as exc:
            return LoadResult(
                class_name  = class_name,
                module_path = module_path,
                success     = False,
                error       = f"ImportError: {exc}",
                duration_ms = (time.time() - t0) * 1_000,
            )

        cls = getattr(module, class_name, None)
        if cls is None:
            return LoadResult(
                class_name  = class_name,
                module_path = module_path,
                success     = False,
                error       = f"Class {class_name!r} not found in module {module_path!r}",
                duration_ms = (time.time() - t0) * 1_000,
            )

        if not self._is_portfolio_class(cls):
            return LoadResult(
                class_name  = class_name,
                module_path = module_path,
                success     = False,
                error       = f"{class_name!r} is not a BasePortfolio subclass",
                duration_ms = (time.time() - t0) * 1_000,
            )

        try:
            entry = self._registry.register(
                cls,
                class_name  = class_name,
                domain      = domain,
                version     = version,
                description = description,
                overwrite   = overwrite,
            )
            log.info("Loaded portfolio class: %s from %s", class_name, module_path)
            return LoadResult(
                class_name  = class_name,
                module_path = module_path,
                success     = True,
                entry       = entry,
                duration_ms = (time.time() - t0) * 1_000,
            )
        except Exception as exc:
            return LoadResult(
                class_name  = class_name,
                module_path = module_path,
                success     = False,
                error       = str(exc),
                duration_ms = (time.time() - t0) * 1_000,
            )

    # ------------------------------------------------------------------
    # Scan a module for all portfolio classes
    # ------------------------------------------------------------------

    def scan_module(
        self,
        module_path:  str,
        *,
        domain:       PortfolioDomain = PortfolioDomain.CUSTOM,
        skip_abstract:bool            = True,
        overwrite:    bool            = False,
    ) -> List[LoadResult]:
        """
        Import *module_path* and register all non-abstract BasePortfolio
        subclasses found in it.
        """
        t0 = time.time()
        try:
            module = importlib.import_module(module_path)
        except ImportError as exc:
            return [LoadResult(
                module_path = module_path,
                success     = False,
                error       = f"ImportError: {exc}",
                duration_ms = (time.time() - t0) * 1_000,
            )]

        results: List[LoadResult] = []
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if not self._is_portfolio_class(obj):
                continue
            if obj.__module__ != module_path:
                continue  # skip imported-from-elsewhere classes
            if skip_abstract and inspect.isabstract(obj):
                continue
            res = self.load_class(
                f"{module_path}.{name}",
                domain    = domain,
                overwrite = overwrite,
            )
            results.append(res)

        return results

    # ------------------------------------------------------------------
    # Batch loading
    # ------------------------------------------------------------------

    def load_many(self, specs: List[dict]) -> List[LoadResult]:
        """
        Load multiple classes from a list of spec dicts.
        Each spec: {"path": "...", "domain": "...", "version": "..."}
        """
        results = []
        for spec in specs:
            path    = spec.get("path", "")
            domain  = PortfolioDomain(spec.get("domain", "custom"))
            version = spec.get("version", "1.0.0")
            description = spec.get("description", "")
            overwrite   = spec.get("overwrite", False)
            res = self.load_class(
                path,
                domain      = domain,
                version     = version,
                description = description,
                overwrite   = overwrite,
            )
            results.append(res)
        return results

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _is_portfolio_class(cls: type) -> bool:
        """Return True if cls is a non-abstract subclass of BasePortfolio."""
        try:
            from iios.investment.portfolio.core.base_portfolio import BasePortfolio
            return (
                isinstance(cls, type)
                and issubclass(cls, BasePortfolio)
                and cls is not BasePortfolio
            )
        except ImportError:
            return False
