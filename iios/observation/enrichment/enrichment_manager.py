"""
iios/observation/enrichment/enrichment_manager.py
=================================================
Top-level orchestrator: classify → enrich → update lifecycle.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..models.observation        import Observation
from ..observation_constants     import LifecycleEvent
from .enrichment_constants       import MAX_ENRICHMENT_HISTORY
from .enrichment_engine          import (
    EnrichmentEngine, EnrichmentOutput, get_enrichment_engine,
    reset_enrichment_engine,
)
from .enrichment_registry        import get_enricher_registry, reset_enricher_registry

__all__ = [
    "ProcessingResult",
    "EnrichmentManager",
    "get_enrichment_manager",
    "reset_enrichment_manager",
]

_LOG     = logging.getLogger("iios.observation.enrichment.manager")
_lock    = threading.Lock()
_manager: Optional["EnrichmentManager"] = None


@dataclass
class ProcessingResult:
    """Full result of classify + enrich pipeline for one observation."""
    obs_id:              str
    classification_used: bool
    enrichment_output:   Optional[EnrichmentOutput]
    success:             bool
    error:               Optional[str]
    duration_ms:         float

    def to_dict(self) -> dict[str, Any]:
        return {
            "obs_id":              self.obs_id,
            "classification_used": self.classification_used,
            "success":             self.success,
            "error":               self.error,
            "duration_ms":         round(self.duration_ms, 3),
            "enrichment_output":   self.enrichment_output.to_dict() if self.enrichment_output else None,
        }


class EnrichmentManager:
    """
    Orchestrates classification (optional) and enrichment for observations.

    Usage
    -----
    manager = get_enrichment_manager()
    result  = manager.process(obs)                         # enrich only
    result  = manager.process(obs, classification_output)  # classify + enrich
    results = manager.process_batch(observations)
    """

    def __init__(
        self,
        engine:      Optional[EnrichmentEngine] = None,
        max_history: int                         = MAX_ENRICHMENT_HISTORY,
    ) -> None:
        self._engine      = engine or get_enrichment_engine()
        self._max_history = max_history
        self._history:    list[ProcessingResult] = []
        self._total       = 0
        self._successful  = 0
        self._failed      = 0
        self._lock        = threading.RLock()

    def process(
        self,
        obs:                Observation,
        classification_ctx: Any = None,
    ) -> ProcessingResult:
        """Run enrichment pipeline; optionally forward classification context."""
        t0 = time.perf_counter()
        try:
            enrichment_output   = self._engine.enrich(obs, classification_ctx)
            success             = True
            error               = None
        except Exception as exc:
            _LOG.warning("Enrichment failed for %s: %s", obs.uid[:8], exc)
            enrichment_output   = None
            success             = False
            error               = str(exc)

        result = ProcessingResult(
            obs_id              = obs.id,
            classification_used = classification_ctx is not None,
            enrichment_output   = enrichment_output,
            success             = success,
            error               = error,
            duration_ms         = (time.perf_counter() - t0) * 1_000.0,
        )
        self._record(result)
        return result

    def process_batch(
        self,
        observations:       list[Observation],
        classification_ctx: Any = None,
    ) -> list[ProcessingResult]:
        return [self.process(obs, classification_ctx) for obs in observations]

    def _record(self, result: ProcessingResult) -> None:
        with self._lock:
            self._total += 1
            if result.success:
                self._successful += 1
            else:
                self._failed += 1
            self._history.append(result)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total":        self._total,
                "successful":   self._successful,
                "failed":       self._failed,
                "success_rate": round(self._successful / self._total, 4) if self._total else 0.0,
            }

    def history(self, limit: Optional[int] = None) -> list[ProcessingResult]:
        with self._lock:
            h = list(self._history)
        return h[-limit:] if limit else h

    def engine(self) -> EnrichmentEngine:
        return self._engine


def get_enrichment_manager() -> EnrichmentManager:
    global _manager
    if _manager is None:
        with _lock:
            if _manager is None:
                _manager = EnrichmentManager()
    return _manager


def reset_enrichment_manager() -> None:
    global _manager
    with _lock:
        _manager = None
    reset_enrichment_engine()
    reset_enricher_registry()
