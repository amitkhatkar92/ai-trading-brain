"""iios/investment/portfolio/portfolio_registry.py
Thread-safe registry of managed portfolios and associated analyzers.
"""
from __future__ import annotations

import threading
from typing import Any

from iios.investment.portfolio.portfolio_constants import DEFAULT_MAX_PORTFOLIOS
from iios.investment.portfolio.portfolio_exceptions import (
    PortfolioAlreadyExistsError,
    PortfolioNotFoundError,
    PortfolioRegistryItemAlreadyExistsError,
    PortfolioRegistryItemNotFoundError,
    PortfolioRegistryOverflowError,
)


class PortfolioRegistry:
    """
    Central registry for:
    - Portfolio descriptors (portfolio_id → info dict)
    - Named analyzers
    - Named providers
    """

    def __init__(self, max_portfolios: int = DEFAULT_MAX_PORTFOLIOS) -> None:
        self._lock:        threading.RLock         = threading.RLock()
        self._max          = max_portfolios
        self._portfolios:  dict[str, dict[str, Any]] = {}
        self._analyzers:   dict[str, Any]           = {}
        self._providers:   dict[str, Any]           = {}

    # ── portfolios ────────────────────────────────────────────────────────────

    def register(
        self,
        portfolio_id:   str,
        name:           str,
        portfolio_type: str = "unknown",
        **kwargs: Any,
    ) -> None:
        with self._lock:
            if portfolio_id in self._portfolios:
                raise PortfolioAlreadyExistsError(
                    portfolio_id=portfolio_id
                )
            if len(self._portfolios) >= self._max:
                raise PortfolioRegistryOverflowError(
                    capacity=self._max, current=len(self._portfolios)
                )
            self._portfolios[portfolio_id] = {
                "portfolio_id":   portfolio_id,
                "name":           name,
                "portfolio_type": portfolio_type,
                **kwargs,
            }

    def is_registered(self, portfolio_id: str) -> bool:
        with self._lock:
            return portfolio_id in self._portfolios

    def get_info(self, portfolio_id: str) -> dict[str, Any]:
        with self._lock:
            if portfolio_id not in self._portfolios:
                raise PortfolioNotFoundError(portfolio_id=portfolio_id)
            return dict(self._portfolios[portfolio_id])

    def all_portfolios(self) -> list[str]:
        with self._lock:
            return list(self._portfolios.keys())

    # ── analyzers ────────────────────────────────────────────────────────────

    def register_analyzer(
        self, analyzer_id: str, analyzer: Any, *, overwrite: bool = False
    ) -> None:
        with self._lock:
            if analyzer_id in self._analyzers and not overwrite:
                raise PortfolioRegistryItemAlreadyExistsError(item_id=analyzer_id)
            self._analyzers[analyzer_id] = analyzer

    def get_analyzer(self, analyzer_id: str) -> Any:
        with self._lock:
            if analyzer_id not in self._analyzers:
                raise PortfolioRegistryItemNotFoundError(item_id=analyzer_id)
            return self._analyzers[analyzer_id]

    def has_analyzer(self, analyzer_id: str) -> bool:
        with self._lock:
            return analyzer_id in self._analyzers

    # ── providers ────────────────────────────────────────────────────────────

    def register_provider(
        self, provider_id: str, provider: Any, *, overwrite: bool = False
    ) -> None:
        with self._lock:
            if provider_id in self._providers and not overwrite:
                raise PortfolioRegistryItemAlreadyExistsError(item_id=provider_id)
            self._providers[provider_id] = provider

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "registered_portfolios": len(self._portfolios),
                "max_portfolios":        self._max,
                "registered_analyzers":  len(self._analyzers),
                "registered_providers":  len(self._providers),
            }


# ── singleton ─────────────────────────────────────────────────────────────────

_registry_lock:     threading.Lock             = threading.Lock()
_registry_instance: PortfolioRegistry | None   = None


def get_portfolio_registry() -> PortfolioRegistry:
    global _registry_instance
    with _registry_lock:
        if _registry_instance is None:
            _registry_instance = PortfolioRegistry()
        return _registry_instance


def reset_portfolio_registry() -> None:
    global _registry_instance
    with _registry_lock:
        _registry_instance = None
