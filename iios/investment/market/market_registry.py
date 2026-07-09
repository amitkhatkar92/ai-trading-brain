"""iios/investment/market/market_registry.py
Pluggable component registry for the Market Intelligence Engine.
"""
from __future__ import annotations

import threading
from typing import Any

from iios.investment.market.market_constants import DEFAULT_MAX_ANALYZERS, DEFAULT_MAX_MARKETS
from iios.investment.market.market_exceptions import (
    MarketRegistryItemAlreadyExistsError,
    MarketRegistryItemNotFoundError,
    MarketRegistryOverflowError,
)
from iios.investment.market.regime.regime_classifier import (
    DefaultRegimeClassifier,
    RegimeClassifier,
)


class MarketRegistry:
    """
    Central registry for pluggable Market Intelligence components:
      - Markets        (identifiers + metadata)
      - Regime classifiers
      - Custom analyzers
      - Data providers
    """

    def __init__(
        self,
        max_markets:   int = DEFAULT_MAX_MARKETS,
        max_analyzers: int = DEFAULT_MAX_ANALYZERS,
    ) -> None:
        self._lock:          threading.RLock              = threading.RLock()
        self._max_markets:   int                          = max_markets
        self._max_analyzers: int                          = max_analyzers
        self._markets:       dict[str, dict[str, Any]]   = {}
        self._classifiers:   dict[str, RegimeClassifier] = {}
        self._analyzers:     dict[str, Any]               = {}
        self._providers:     dict[str, Any]               = {}

    # ── markets ───────────────────────────────────────────────────────────────

    def register_market(
        self,
        market_id: str,
        name:      str                   = "",
        metadata:  dict[str, Any] | None = None,
        *,
        overwrite: bool                  = False,
    ) -> None:
        with self._lock:
            if not overwrite and market_id in self._markets:
                raise MarketRegistryItemAlreadyExistsError(market_id)
            if len(self._markets) >= self._max_markets and market_id not in self._markets:
                raise MarketRegistryOverflowError(self._max_markets)
            self._markets[market_id] = {
                "market_id": market_id,
                "name":      name or market_id,
                "metadata":  metadata or {},
            }

    def is_registered(self, market_id: str) -> bool:
        with self._lock:
            return market_id in self._markets

    def get_market_info(self, market_id: str) -> dict[str, Any]:
        with self._lock:
            if market_id not in self._markets:
                raise MarketRegistryItemNotFoundError(market_id)
            return dict(self._markets[market_id])

    def all_markets(self) -> list[str]:
        with self._lock:
            return list(self._markets.keys())

    # ── regime classifiers ────────────────────────────────────────────────────

    def register_classifier(
        self,
        classifier: RegimeClassifier,
        *,
        overwrite:  bool = False,
    ) -> None:
        with self._lock:
            key = classifier.classifier_id
            if not overwrite and key in self._classifiers:
                raise MarketRegistryItemAlreadyExistsError(key)
            self._classifiers[key] = classifier

    def get_classifier(self, classifier_id: str) -> RegimeClassifier:
        with self._lock:
            if classifier_id not in self._classifiers:
                raise MarketRegistryItemNotFoundError(classifier_id)
            return self._classifiers[classifier_id]

    def has_classifier(self, classifier_id: str) -> bool:
        with self._lock:
            return classifier_id in self._classifiers

    def default_classifier(self) -> RegimeClassifier:
        with self._lock:
            return self._classifiers.get("default", DefaultRegimeClassifier())

    # ── custom analyzers ──────────────────────────────────────────────────────

    def register_analyzer(
        self,
        analyzer_id: str,
        analyzer:    Any,
        *,
        overwrite:   bool = False,
    ) -> None:
        with self._lock:
            if not overwrite and analyzer_id in self._analyzers:
                raise MarketRegistryItemAlreadyExistsError(analyzer_id)
            if len(self._analyzers) >= self._max_analyzers and analyzer_id not in self._analyzers:
                raise MarketRegistryOverflowError(self._max_analyzers)
            self._analyzers[analyzer_id] = analyzer

    def get_analyzer(self, analyzer_id: str) -> Any:
        with self._lock:
            if analyzer_id not in self._analyzers:
                raise MarketRegistryItemNotFoundError(analyzer_id)
            return self._analyzers[analyzer_id]

    def has_analyzer(self, analyzer_id: str) -> bool:
        with self._lock:
            return analyzer_id in self._analyzers

    # ── data providers ────────────────────────────────────────────────────────

    def register_provider(
        self,
        provider_id: str,
        provider:    Any,
        *,
        overwrite:   bool = False,
    ) -> None:
        with self._lock:
            if not overwrite and provider_id in self._providers:
                raise MarketRegistryItemAlreadyExistsError(provider_id)
            self._providers[provider_id] = provider

    def get_provider(self, provider_id: str) -> Any:
        with self._lock:
            if provider_id not in self._providers:
                raise MarketRegistryItemNotFoundError(provider_id)
            return self._providers[provider_id]

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "markets":     len(self._markets),
                "classifiers": len(self._classifiers),
                "analyzers":   len(self._analyzers),
                "providers":   len(self._providers),
            }


# ── singleton ─────────────────────────────────────────────────────────────────

_singleton_lock: threading.Lock        = threading.Lock()
_instance:       MarketRegistry | None = None


def get_market_registry() -> MarketRegistry:
    global _instance  # noqa: PLW0603
    if _instance is None:
        with _singleton_lock:
            if _instance is None:
                _instance = MarketRegistry()
    return _instance


def reset_market_registry() -> None:
    global _instance  # noqa: PLW0603
    with _singleton_lock:
        _instance = None
