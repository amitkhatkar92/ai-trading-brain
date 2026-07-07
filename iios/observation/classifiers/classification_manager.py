"""
iios/observation/classifiers/classification_manager.py
=======================================================
High-level manager: exposes process() and process_batch() APIs,
keeps stats, and manages history.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..models.observation       import Observation
from .classification_constants  import MAX_CLASSIFIER_HISTORY
from .classification_engine     import (
    ClassificationEngine, ClassificationOutput, get_classification_engine,
    reset_classification_engine,
)
from .classification_registry   import get_classifier_registry, reset_classifier_registry

__all__ = [
    "ClassificationManagerResult",
    "ClassificationManager",
    "get_classification_manager",
    "reset_classification_manager",
]

_LOG    = logging.getLogger("iios.observation.classification.manager")
_lock   = threading.Lock()
_manager: Optional["ClassificationManager"] = None


@dataclass
class ClassificationManagerResult:
    obs_id:     str
    output:     ClassificationOutput
    success:    bool
    error:      Optional[str]
    duration_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "obs_id":      self.obs_id,
            "success":     self.success,
            "error":       self.error,
            "duration_ms": round(self.duration_ms, 3),
            "output":      self.output.to_dict() if self.output else None,
        }


class ClassificationManager:
    """Orchestrates the classification pipeline for single or batch observations."""

    def __init__(
        self,
        engine:      Optional[ClassificationEngine] = None,
        max_history: int                             = MAX_CLASSIFIER_HISTORY,
    ) -> None:
        self._engine      = engine or get_classification_engine()
        self._max_history = max_history
        self._history:    list[ClassificationManagerResult] = []
        self._total       = 0
        self._successful  = 0
        self._failed      = 0
        self._lock        = threading.RLock()

    def process(self, obs: Observation) -> ClassificationManagerResult:
        t0 = time.perf_counter()
        try:
            output  = self._engine.classify(obs)
            success = True
            error   = None
        except Exception as exc:
            _LOG.warning("Classification failed for %s: %s", obs.uid[:8], exc)
            output  = None   # type: ignore[assignment]
            success = False
            error   = str(exc)

        result = ClassificationManagerResult(
            obs_id      = obs.id,
            output      = output,
            success     = success,
            error       = error,
            duration_ms = (time.perf_counter() - t0) * 1_000.0,
        )
        with self._lock:
            self._total += 1
            if success:
                self._successful += 1
            else:
                self._failed += 1
            self._history.append(result)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]
        return result

    def process_batch(
        self, observations: list[Observation]
    ) -> list[ClassificationManagerResult]:
        return [self.process(obs) for obs in observations]

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total":        self._total,
                "successful":   self._successful,
                "failed":       self._failed,
                "success_rate": round(self._successful / self._total, 4) if self._total else 0.0,
            }

    def history(self, limit: Optional[int] = None) -> list[ClassificationManagerResult]:
        with self._lock:
            h = list(self._history)
        return h[-limit:] if limit else h

    def engine(self) -> ClassificationEngine:
        return self._engine


def get_classification_manager() -> ClassificationManager:
    global _manager
    if _manager is None:
        with _lock:
            if _manager is None:
                _manager = ClassificationManager()
    return _manager


def reset_classification_manager() -> None:
    global _manager
    with _lock:
        _manager = None
    reset_classification_engine()
    reset_classifier_registry()
