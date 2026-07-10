"""features/feature_registry.py — Thread-safe registry of FeatureDefinition objects."""
from __future__ import annotations

import threading
from typing import Any, Optional

from iios.integration.research.learning.learning_exceptions import FeatureNotFoundError
from iios.integration.research.learning.learning_constants  import FeatureType
from iios.integration.research.learning.features.feature_definition import FeatureDefinition


class FeatureRegistry:
    """
    Central in-memory store for FeatureDefinition objects.
    Thread-safe via a single RLock.
    """

    def __init__(self) -> None:
        self._by_id:   dict[str, FeatureDefinition] = {}
        self._by_name: dict[str, FeatureDefinition] = {}
        self._lock = threading.RLock()

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def register(self, feature: FeatureDefinition) -> None:
        with self._lock:
            self._by_id[feature.feature_id] = feature
            self._by_name[feature.name]     = feature

    def get_by_id(self, feature_id: str) -> FeatureDefinition:
        with self._lock:
            feat = self._by_id.get(feature_id)
        if feat is None:
            raise FeatureNotFoundError(f"Feature id {feature_id!r} not found")
        return feat

    def get_by_name(self, name: str) -> FeatureDefinition:
        with self._lock:
            feat = self._by_name.get(name)
        if feat is None:
            raise FeatureNotFoundError(f"Feature '{name}' not found")
        return feat

    def has_name(self, name: str) -> bool:
        with self._lock:
            return name in self._by_name

    def remove(self, name: str) -> None:
        with self._lock:
            feat = self._by_name.pop(name, None)
            if feat is not None:
                self._by_id.pop(feat.feature_id, None)

    # ── Queries ───────────────────────────────────────────────────────────────

    def all_features(self) -> list[FeatureDefinition]:
        with self._lock:
            return list(self._by_id.values())

    def by_type(self, feature_type: FeatureType) -> list[FeatureDefinition]:
        with self._lock:
            return [f for f in self._by_id.values() if f.feature_type == feature_type]

    def required_features(self) -> list[FeatureDefinition]:
        with self._lock:
            return [f for f in self._by_id.values() if f.required]

    def count(self) -> int:
        with self._lock:
            return len(self._by_id)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            by_type: dict[str, int] = {}
            for f in self._by_id.values():
                key = f.feature_type.value
                by_type[key] = by_type.get(key, 0) + 1
            return {
                "total":    len(self._by_id),
                "by_type":  by_type,
                "required": sum(1 for f in self._by_id.values() if f.required),
            }
