"""iios/investment/strategy/migration/legacy_catalog.py
Aggregated catalog view of all discovered legacy strategies.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.migration.legacy_metadata import (
    LegacyStrategyMetadata,
    LegacyStrategySource,
    LegacyStrategyType,
    LegacyHealthStatus,
)


@dataclass
class CatalogStats:
    """Aggregated statistics over all catalogued strategies."""
    total:               int = 0
    by_source:           Dict[str, int] = field(default_factory=dict)
    by_type:             Dict[str, int] = field(default_factory=dict)
    by_category:         Dict[str, int] = field(default_factory=dict)
    by_health:           Dict[str, int] = field(default_factory=dict)
    approved_count:      int = 0
    json_with_conditions: int = 0
    code_based_count:    int = 0
    last_updated:        Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total":                self.total,
            "by_source":            self.by_source,
            "by_type":              self.by_type,
            "by_category":          self.by_category,
            "by_health":            self.by_health,
            "approved_count":       self.approved_count,
            "json_with_conditions": self.json_with_conditions,
            "code_based_count":     self.code_based_count,
            "last_updated":         self.last_updated.isoformat() if self.last_updated else None,
        }


class LegacyCatalog:
    """
    Read-only aggregated view of all legacy strategies.
    Maintains indices for fast lookup by source, type, category, and tag.
    """

    def __init__(self) -> None:
        self._strategies: List[LegacyStrategyMetadata] = []
        self._by_name:    Dict[str, LegacyStrategyMetadata] = {}
        self._by_id:      Dict[str, LegacyStrategyMetadata] = {}
        self._lock        = threading.RLock()

    def ingest(self, strategies: List[LegacyStrategyMetadata]) -> None:
        """Bulk-load strategies into the catalog."""
        with self._lock:
            for meta in strategies:
                if meta.strategy_name not in self._by_name:
                    self._strategies.append(meta)
                    self._by_name[meta.strategy_name] = meta
                    self._by_id[meta.strategy_id]     = meta

    def add(self, meta: LegacyStrategyMetadata) -> None:
        with self._lock:
            if meta.strategy_name not in self._by_name:
                self._strategies.append(meta)
                self._by_name[meta.strategy_name] = meta
                self._by_id[meta.strategy_id]     = meta

    def get(self, name: str) -> Optional[LegacyStrategyMetadata]:
        with self._lock:
            return self._by_name.get(name)

    def get_by_id(self, strategy_id: str) -> Optional[LegacyStrategyMetadata]:
        with self._lock:
            return self._by_id.get(strategy_id)

    def all(self) -> List[LegacyStrategyMetadata]:
        with self._lock:
            return list(self._strategies)

    def filter(
        self,
        source:       Optional[LegacyStrategySource]   = None,
        strategy_type: Optional[LegacyStrategyType]    = None,
        category:     Optional[str]                    = None,
        health:       Optional[LegacyHealthStatus]     = None,
        approved_only: bool                            = False,
    ) -> List[LegacyStrategyMetadata]:
        with self._lock:
            results = list(self._strategies)
        if source:
            results = [m for m in results if m.source == source]
        if strategy_type:
            results = [m for m in results if m.strategy_type == strategy_type]
        if category:
            results = [m for m in results if m.category == category]
        if health:
            results = [m for m in results if m.health_status == health]
        if approved_only:
            results = [m for m in results if m.is_approved]
        return results

    def by_regime(self, regime: str) -> List[LegacyStrategyMetadata]:
        with self._lock:
            regime_lower = regime.lower()
            return [
                m for m in self._strategies
                if regime_lower in (r.lower() for r in m.preferred_regimes)
            ]

    def with_entry_conditions(self) -> List[LegacyStrategyMetadata]:
        with self._lock:
            return [m for m in self._strategies if m.entry_conditions]

    def search(self, query: str) -> List[LegacyStrategyMetadata]:
        """Case-insensitive search by name, description, or tags."""
        with self._lock:
            q = query.lower()
            return [
                m for m in self._strategies
                if q in m.strategy_name.lower()
                or q in m.description.lower()
                or any(q in t.lower() for t in m.tags)
            ]

    def stats(self) -> CatalogStats:
        with self._lock:
            strategies = list(self._strategies)

        by_source: Dict[str, int] = {}
        by_type:   Dict[str, int] = {}
        by_cat:    Dict[str, int] = {}
        by_health: Dict[str, int] = {}
        approved = 0
        json_cond = 0
        code_based = 0

        for m in strategies:
            by_source[m.source.value]       = by_source.get(m.source.value, 0) + 1
            by_type[m.strategy_type.value]  = by_type.get(m.strategy_type.value, 0) + 1
            by_cat[m.category]              = by_cat.get(m.category, 0) + 1
            by_health[m.health_status.value] = by_health.get(m.health_status.value, 0) + 1
            if m.is_approved:   approved   += 1
            if m.entry_conditions: json_cond += 1
            if m.strategy_type == LegacyStrategyType.CODE_BASED: code_based += 1

        return CatalogStats(
            total=len(strategies),
            by_source=by_source,
            by_type=by_type,
            by_category=by_cat,
            by_health=by_health,
            approved_count=approved,
            json_with_conditions=json_cond,
            code_based_count=code_based,
            last_updated=datetime.now(timezone.utc),
        )

    def names(self) -> List[str]:
        with self._lock:
            return list(self._by_name.keys())

    def count(self) -> int:
        with self._lock:
            return len(self._strategies)
