"""
iios/observation/classifiers/classification_registry.py
========================================================
ClassifierRegistry + BaseClassifier ABC.

Every dimension classifier must subclass BaseClassifier and implement
``_classify(obs) -> tuple[Any, float, str]``.
"""
from __future__ import annotations

import logging
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from ..models.observation         import Observation
from .classification_constants    import (
    DEFAULT_CLASSIFIER_WEIGHT, MIN_CLASSIFICATION_CONFIDENCE, SYSTEM_CLASSIFIER,
)
from .classification_exceptions   import (
    ClassifierAlreadyRegisteredError, ClassifierNotFoundError,
)

__all__ = [
    "ClassificationLabel",
    "BaseClassifier",
    "ClassifierRegistry",
    "get_classifier_registry",
    "reset_classifier_registry",
]

_LOG  = logging.getLogger("iios.observation.classification.registry")
_lock = threading.Lock()
_registry: Optional["ClassifierRegistry"] = None


@dataclass
class ClassificationLabel:
    """Single dimension classification result."""
    dimension:   str           # e.g. "entity_type", "asset_class"
    value:       Any           # enum or str value assigned
    confidence:  float = 1.0   # [0, 1]
    method:      str   = "rule_based"
    reason:      str   = ""
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        v = self.value.value if hasattr(self.value, "value") else self.value
        return {
            "dimension":   self.dimension,
            "value":       v,
            "confidence":  round(self.confidence, 4),
            "method":      self.method,
            "reason":      self.reason,
            "duration_ms": round(self.duration_ms, 3),
        }


class BaseClassifier(ABC):
    """Abstract base for all dimension classifiers."""

    dimension:   str    # label to store result under
    name:        str
    weight:      float
    enabled:     bool
    description: str

    def __init__(
        self,
        dimension:   str,
        name:        str,
        weight:      float = DEFAULT_CLASSIFIER_WEIGHT,
        enabled:     bool  = True,
        description: str   = "",
    ) -> None:
        self.dimension   = dimension
        self.name        = name
        self.weight      = weight
        self.enabled     = enabled
        self.description = description

    def classify(self, obs: Observation) -> ClassificationLabel:
        t0 = time.perf_counter()
        try:
            value, confidence, reason = self._classify(obs)
        except Exception as exc:
            _LOG.debug("Classifier %r error for %s: %s", self.name, obs.uid[:8], exc)
            value, confidence, reason = None, 0.0, f"error: {exc}"
        return ClassificationLabel(
            dimension   = self.dimension,
            value       = value,
            confidence  = max(0.0, min(1.0, confidence)),
            reason      = reason,
            duration_ms = (time.perf_counter() - t0) * 1_000.0,
        )

    @abstractmethod
    def _classify(self, obs: Observation) -> tuple[Any, float, str]:
        """Return ``(value, confidence_in_0_1, reason_str)``."""

    def __repr__(self) -> str:
        return f"<{type(self).__name__} dimension={self.dimension!r}>"


class ClassifierRegistry:
    """Thread-safe registry of dimension classifiers."""

    def __init__(self) -> None:
        self._classifiers: dict[str, BaseClassifier] = {}
        self._lock = threading.RLock()

    def register(self, clf: BaseClassifier, overwrite: bool = False) -> None:
        with self._lock:
            if clf.name in self._classifiers and not overwrite:
                raise ClassifierAlreadyRegisteredError(clf.name)
            self._classifiers[clf.name] = clf

    def register_many(self, clfs: list[BaseClassifier], overwrite: bool = False) -> None:
        for c in clfs:
            self.register(c, overwrite=overwrite)

    def unregister(self, name: str) -> None:
        with self._lock:
            if name not in self._classifiers:
                raise ClassifierNotFoundError(name)
            del self._classifiers[name]

    def get(self, name: str) -> BaseClassifier:
        with self._lock:
            if name not in self._classifiers:
                raise ClassifierNotFoundError(name)
            return self._classifiers[name]

    def get_or_none(self, name: str) -> Optional[BaseClassifier]:
        with self._lock:
            return self._classifiers.get(name)

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._classifiers

    def all(self) -> list[BaseClassifier]:
        with self._lock:
            return list(self._classifiers.values())

    def enabled(self) -> list[BaseClassifier]:
        with self._lock:
            return [c for c in self._classifiers.values() if c.enabled]

    def by_dimension(self, dimension: str) -> list[BaseClassifier]:
        with self._lock:
            return [c for c in self._classifiers.values() if c.dimension == dimension]

    def enable(self, name: str) -> None:
        self.get(name).enabled = True

    def disable(self, name: str) -> None:
        self.get(name).enabled = False

    def clear(self) -> None:
        with self._lock:
            self._classifiers.clear()

    def names(self) -> list[str]:
        with self._lock:
            return sorted(self._classifiers.keys())

    def count(self) -> int:
        with self._lock:
            return len(self._classifiers)

    def dimensions(self) -> list[str]:
        with self._lock:
            return sorted({c.dimension for c in self._classifiers.values()})

    def __len__(self) -> int:
        return self.count()

    def __contains__(self, name: str) -> bool:
        return self.has(name)


def get_classifier_registry() -> ClassifierRegistry:
    global _registry
    if _registry is None:
        with _lock:
            if _registry is None:
                from .classification_engine import DEFAULT_CLASSIFIERS
                _registry = ClassifierRegistry()
                _registry.register_many(DEFAULT_CLASSIFIERS())
    return _registry


def reset_classifier_registry() -> None:
    global _registry
    with _lock:
        _registry = None
