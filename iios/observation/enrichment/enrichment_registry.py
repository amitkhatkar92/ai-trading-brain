"""
iios/observation/enrichment/enrichment_registry.py
===================================================
EnricherRegistry + BaseEnricher ABC.
"""
from __future__ import annotations

import logging
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from ..models.observation      import Observation
from .enrichment_constants     import (
    EnricherCategory, EnricherStage, MAX_ENRICHMENT_HISTORY,
)
from .enrichment_exceptions    import (
    EnricherAlreadyRegisteredError, EnricherNotFoundError,
)

__all__ = [
    "EnrichmentRecord",
    "BaseEnricher",
    "EnricherRegistry",
    "get_enricher_registry",
    "reset_enricher_registry",
]

_LOG     = logging.getLogger("iios.observation.enrichment.registry")
_lock    = threading.Lock()
_registry: Optional["EnricherRegistry"] = None


@dataclass
class EnrichmentRecord:
    """Record of changes made by a single enricher."""
    enricher_name:   str
    stage:           EnricherStage
    category:        EnricherCategory
    tags_added:      list[str]              = field(default_factory=list)
    labels_added:    dict[str, str]         = field(default_factory=dict)
    attributes_set:  dict[str, Any]         = field(default_factory=dict)
    links_added:     list[dict[str, Any]]   = field(default_factory=list)
    duration_ms:     float                  = 0.0
    success:         bool                   = True
    error:           Optional[str]          = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "enricher_name":  self.enricher_name,
            "stage":          self.stage.value,
            "category":       self.category.value,
            "tags_added":     self.tags_added,
            "labels_added":   self.labels_added,
            "attributes_set": list(self.attributes_set.keys()),
            "links_added":    len(self.links_added),
            "duration_ms":    round(self.duration_ms, 3),
            "success":        self.success,
            "error":          self.error,
        }


class BaseEnricher(ABC):
    """Abstract base for all observation enrichers."""

    name:        str
    stage:       EnricherStage
    category:    EnricherCategory
    weight:      float
    enabled:     bool
    description: str

    def __init__(
        self,
        name:        str,
        stage:       EnricherStage,
        category:    EnricherCategory,
        weight:      float = 1.0,
        enabled:     bool  = True,
        description: str   = "",
    ) -> None:
        self.name        = name
        self.stage       = stage
        self.category    = category
        self.weight      = weight
        self.enabled     = enabled
        self.description = description

    def enrich(
        self,
        obs:                Observation,
        classification_ctx: Optional[Any] = None,
    ) -> EnrichmentRecord:
        t0     = time.perf_counter()
        record = EnrichmentRecord(
            enricher_name = self.name,
            stage         = self.stage,
            category      = self.category,
        )
        try:
            self._enrich(obs, record, classification_ctx)
            record.duration_ms = (time.perf_counter() - t0) * 1_000.0
        except Exception as exc:
            record.success     = False
            record.error       = str(exc)
            record.duration_ms = (time.perf_counter() - t0) * 1_000.0
            _LOG.debug("Enricher %r error: %s", self.name, exc)
        return record

    @abstractmethod
    def _enrich(
        self,
        obs:    Observation,
        record: EnrichmentRecord,
        ctx:    Optional[Any],
    ) -> None:
        """Mutate obs in-place; update record with changes made."""

    def __repr__(self) -> str:
        return f"<{type(self).__name__} name={self.name!r} stage={self.stage.value}>"


class EnricherRegistry:
    """Thread-safe registry of enrichers."""

    def __init__(self) -> None:
        self._enrichers: dict[str, BaseEnricher] = {}
        self._lock = threading.RLock()

    def register(self, enricher: BaseEnricher, overwrite: bool = False) -> None:
        with self._lock:
            if enricher.name in self._enrichers and not overwrite:
                raise EnricherAlreadyRegisteredError(enricher.name)
            self._enrichers[enricher.name] = enricher

    def register_many(self, enrichers: list[BaseEnricher], overwrite: bool = False) -> None:
        for e in enrichers:
            self.register(e, overwrite=overwrite)

    def unregister(self, name: str) -> None:
        with self._lock:
            if name not in self._enrichers:
                raise EnricherNotFoundError(name)
            del self._enrichers[name]

    def get(self, name: str) -> BaseEnricher:
        with self._lock:
            if name not in self._enrichers:
                raise EnricherNotFoundError(name)
            return self._enrichers[name]

    def get_or_none(self, name: str) -> Optional[BaseEnricher]:
        with self._lock:
            return self._enrichers.get(name)

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._enrichers

    def all(self) -> list[BaseEnricher]:
        with self._lock:
            return list(self._enrichers.values())

    def enabled(self) -> list[BaseEnricher]:
        with self._lock:
            return [e for e in self._enrichers.values() if e.enabled]

    def by_stage(self, stage: EnricherStage) -> list[BaseEnricher]:
        with self._lock:
            return sorted(
                [e for e in self._enrichers.values() if e.stage == stage],
                key=lambda e: e.name,
            )

    def by_category(self, category: EnricherCategory) -> list[BaseEnricher]:
        with self._lock:
            return [e for e in self._enrichers.values() if e.category == category]

    def ordered(self) -> list[BaseEnricher]:
        """Return enabled enrichers sorted by stage pipeline order."""
        order = [
            EnricherStage.PRE, EnricherStage.SEMANTIC, EnricherStage.CONTEXT,
            EnricherStage.LINKING, EnricherStage.POST,
        ]
        with self._lock:
            enabled = [e for e in self._enrichers.values() if e.enabled]
        result: list[BaseEnricher] = []
        for stage in order:
            result.extend([e for e in enabled if e.stage == stage])
        return result

    def enable(self, name: str) -> None:
        self.get(name).enabled = True

    def disable(self, name: str) -> None:
        self.get(name).enabled = False

    def clear(self) -> None:
        with self._lock:
            self._enrichers.clear()

    def names(self) -> list[str]:
        with self._lock:
            return sorted(self._enrichers.keys())

    def count(self) -> int:
        with self._lock:
            return len(self._enrichers)

    def stages_present(self) -> list[EnricherStage]:
        with self._lock:
            return sorted({e.stage for e in self._enrichers.values()}, key=lambda s: s.value)

    def __len__(self) -> int:
        return self.count()

    def __contains__(self, name: str) -> bool:
        return self.has(name)


def get_enricher_registry() -> EnricherRegistry:
    global _registry
    if _registry is None:
        with _lock:
            if _registry is None:
                from .enrichment_engine import DEFAULT_ENRICHERS
                _registry = EnricherRegistry()
                _registry.register_many(DEFAULT_ENRICHERS())
    return _registry


def reset_enricher_registry() -> None:
    global _registry
    with _lock:
        _registry = None
