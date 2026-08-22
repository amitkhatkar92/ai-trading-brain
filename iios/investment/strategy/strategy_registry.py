"""iios/investment/strategy/strategy_registry.py
Thread-safe registry of StrategyDefinitions and their profiles.
"""
from __future__ import annotations

import threading
from typing import Any

from iios.investment.strategy.strategy_constants import (
    DEFAULT_MAX_STRATEGIES,
    StrategyCategory,
    StrategyStatus,
)
from iios.investment.strategy.strategy_exceptions import (
    StrategyAlreadyExistsError,
    StrategyNotFoundError,
    StrategyRegistryOverflowError,
)
from iios.investment.strategy.core.strategy_definition import StrategyDefinition
from iios.investment.strategy.core.strategy_profile import StrategyProfile


class StrategyRegistry:
    """
    Central registry for StrategyDefinitions.

    The registry knows about definitions and basic lookup (by id, category).
    Full profile state is managed by StrategyManager which holds StrategyProfile
    objects.  The registry and manager share the same profile dict reference to
    avoid duplication.
    """

    def __init__(
        self,
        max_strategies: int = DEFAULT_MAX_STRATEGIES,
    ) -> None:
        self._lock            = threading.RLock()
        self._max             = max_strategies
        self._definitions:    dict[str, StrategyDefinition] = {}

    # ── registration ─────────────────────────────────────────────────────────

    def register(self, definition: StrategyDefinition) -> None:
        """Register a StrategyDefinition. Raises if already registered or full."""
        with self._lock:
            sid = definition.strategy_id
            if sid in self._definitions:
                raise StrategyAlreadyExistsError(
                    f"Strategy already registered: {sid!r}",
                    strategy_id=sid,
                )
            if len(self._definitions) >= self._max:
                raise StrategyRegistryOverflowError(
                    f"Registry full (max={self._max})",
                    capacity=self._max,
                    current=len(self._definitions),
                )
            self._definitions[sid] = definition

    def is_registered(self, strategy_id: str) -> bool:
        with self._lock:
            return strategy_id in self._definitions

    def get_definition(self, strategy_id: str) -> StrategyDefinition:
        with self._lock:
            if strategy_id not in self._definitions:
                raise StrategyNotFoundError(
                    f"Strategy not found: {strategy_id!r}",
                    strategy_id=strategy_id,
                )
            return self._definitions[strategy_id]

    def all_strategy_ids(self) -> list[str]:
        with self._lock:
            return list(self._definitions.keys())

    def by_category(self, category: StrategyCategory) -> list[str]:
        with self._lock:
            return [
                sid for sid, defn in self._definitions.items()
                if defn.category == category
            ]

    def by_asset_class(self, asset_class: str) -> list[str]:
        with self._lock:
            return [
                sid for sid, defn in self._definitions.items()
                if defn.asset_class.value == asset_class
            ]

    def search(self, **kwargs: Any) -> list[str]:
        """
        Generic search by definition attributes.
        e.g. search(category="momentum", risk_level="moderate")
        """
        with self._lock:
            results = []
            for sid, defn in self._definitions.items():
                match = all(
                    getattr(defn, k, None) == v
                    or getattr(getattr(defn, k, None), "value", None) == v
                    for k, v in kwargs.items()
                )
                if match:
                    results.append(sid)
            return results

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            by_cat: dict[str, int] = {}
            for defn in self._definitions.values():
                by_cat[defn.category.value] = by_cat.get(defn.category.value, 0) + 1
            return {
                "registered_strategies": len(self._definitions),
                "max_strategies":        self._max,
                "by_category":           by_cat,
            }


# ── module-level singleton ────────────────────────────────────────────────────

_registry_lock:     threading.Lock                 = threading.Lock()
_registry_instance: StrategyRegistry | None        = None


def get_strategy_registry() -> StrategyRegistry:
    global _registry_instance
    with _registry_lock:
        if _registry_instance is None:
            _registry_instance = StrategyRegistry()
        return _registry_instance


def reset_strategy_registry() -> None:
    global _registry_instance
    with _registry_lock:
        _registry_instance = None
