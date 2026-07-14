"""iios/investment/strategy/migration/adapter_registry.py
Thread-safe registry of all created strategy adapters.
"""
from __future__ import annotations

import threading
from collections import defaultdict
from typing import Dict, Iterator, List, Optional

from iios.investment.strategy.migration.strategy_adapter import (
    LegacyStrategyAdapter,
    AdaptationMode,
)
from iios.investment.strategy.migration.legacy_metadata import LegacyStrategySource


class AdapterRegistry:
    """
    Thread-safe store of strategy_id → LegacyStrategyAdapter.
    Supports lookup by name, source, and adaptation mode.
    """

    def __init__(self) -> None:
        self._adapters:  Dict[str, LegacyStrategyAdapter] = {}    # id → adapter
        self._by_name:   Dict[str, LegacyStrategyAdapter] = {}    # name → adapter
        self._lock       = threading.RLock()

    def register(self, adapter: LegacyStrategyAdapter) -> None:
        with self._lock:
            sid  = adapter.strategy_id
            name = adapter.name
            self._adapters[sid]  = adapter
            self._by_name[name]  = adapter

    def get(self, strategy_id: str) -> Optional[LegacyStrategyAdapter]:
        with self._lock:
            return self._adapters.get(strategy_id)

    def get_by_name(self, name: str) -> Optional[LegacyStrategyAdapter]:
        with self._lock:
            return self._by_name.get(name)

    def all(self) -> List[LegacyStrategyAdapter]:
        with self._lock:
            return list(self._adapters.values())

    def by_source(self, source: LegacyStrategySource) -> List[LegacyStrategyAdapter]:
        with self._lock:
            return [
                a for a in self._adapters.values()
                if a.metadata.source == source
            ]

    def by_mode(self, mode: AdaptationMode) -> List[LegacyStrategyAdapter]:
        with self._lock:
            return [
                a for a in self._adapters.values()
                if a.adaptation_mode == mode
            ]

    def approved_only(self) -> List[LegacyStrategyAdapter]:
        with self._lock:
            return [
                a for a in self._adapters.values()
                if a.metadata.is_approved
            ]

    def remove(self, strategy_id: str) -> bool:
        with self._lock:
            adapter = self._adapters.pop(strategy_id, None)
            if adapter:
                self._by_name.pop(adapter.name, None)
                return True
            return False

    def count(self) -> int:
        with self._lock:
            return len(self._adapters)

    def contains(self, strategy_id: str) -> bool:
        with self._lock:
            return strategy_id in self._adapters

    def contains_name(self, name: str) -> bool:
        with self._lock:
            return name in self._by_name

    def names(self) -> List[str]:
        with self._lock:
            return list(self._by_name.keys())

    def __iter__(self) -> Iterator[LegacyStrategyAdapter]:
        with self._lock:
            return iter(list(self._adapters.values()))
