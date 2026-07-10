"""features/feature_engine.py — Orchestrates feature pipelines and validation."""
from __future__ import annotations

import threading
import time
from typing import Any, Optional

from iios.integration.research.learning.learning_exceptions import (
    FeatureError,
    FeaturePipelineError,
    FeatureValidationError,
)
from iios.integration.research.learning.features.feature_definition  import FeatureDefinition
from iios.integration.research.learning.features.feature_registry    import FeatureRegistry
from iios.integration.research.learning.features.feature_pipeline    import FeaturePipeline
from iios.integration.research.learning.features.feature_store       import FeatureStore
from iios.integration.research.learning.features.feature_validator   import FeatureValidator
from iios.integration.research.learning.features.feature_statistics  import FeatureStatistics


class FeatureEngine:
    """
    Top-level orchestrator for feature engineering in the Learning Framework.

    Responsibilities:
    - Register and retrieve feature definitions
    - Manage multiple named FeaturePipelines
    - Apply pipelines to records and batches
    - Serve pre-computed vectors from FeatureStore
    - Compute feature statistics for drift detection
    """

    def __init__(self) -> None:
        self._registry  = FeatureRegistry()
        self._pipelines: dict[str, FeaturePipeline] = {}
        self._store     = FeatureStore()
        self._lock      = threading.RLock()
        self._processed = 0

    # ── Features ──────────────────────────────────────────────────────────────

    def define_feature(self, feature: FeatureDefinition) -> None:
        self._registry.register(feature)

    def get_feature(self, name: str) -> FeatureDefinition:
        return self._registry.get_by_name(name)

    def all_features(self) -> list[FeatureDefinition]:
        return self._registry.all_features()

    # ── Pipelines ─────────────────────────────────────────────────────────────

    def add_pipeline(self, pipeline: FeaturePipeline) -> None:
        with self._lock:
            self._pipelines[pipeline.pipeline_id] = pipeline

    def get_pipeline(self, pipeline_id: str) -> FeaturePipeline:
        with self._lock:
            pipe = self._pipelines.get(pipeline_id)
        if pipe is None:
            raise FeatureError(f"Pipeline '{pipeline_id}' not found")
        return pipe

    def pipeline_ids(self) -> list[str]:
        with self._lock:
            return list(self._pipelines.keys())

    # ── Transformation ────────────────────────────────────────────────────────

    def fit_pipeline(self, pipeline_id: str, records: list[dict[str, Any]]) -> None:
        pipe = self.get_pipeline(pipeline_id)
        pipe.fit(records)

    def transform(self, pipeline_id: str, record: dict[str, Any]) -> dict[str, Any]:
        pipe = self.get_pipeline(pipeline_id)
        result = pipe.transform(record)
        with self._lock:
            self._processed += 1
        return result

    def transform_batch(
        self,
        pipeline_id: str,
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        pipe = self.get_pipeline(pipeline_id)
        results = pipe.transform_batch(records)
        with self._lock:
            self._processed += len(records)
        return results

    # ── Feature Store ─────────────────────────────────────────────────────────

    def store(self, entity_id: str, features: dict[str, Any], *, ttl_sec: Optional[float] = None) -> None:
        self._store.put(entity_id, features, ttl_sec=ttl_sec)

    def lookup(self, entity_id: str) -> dict[str, Any]:
        return self._store.get(entity_id)

    # ── Validation ────────────────────────────────────────────────────────────

    def validate_record(self, record: dict[str, Any], required_names: list[str]) -> list[str]:
        validator = FeatureValidator(self._registry, required_names)
        return validator.validate_record(record)

    # ── Statistics ────────────────────────────────────────────────────────────

    def compute_feature_stats(
        self,
        records:      list[dict[str, Any]],
        feature_name: str,
    ) -> FeatureStatistics:
        values = [r[feature_name] for r in records
                  if feature_name in r and isinstance(r[feature_name], (int, float))]
        return FeatureStatistics.compute(feature_name, values)

    def stats(self) -> dict[str, Any]:
        return {
            "features_registered": self._registry.count(),
            "pipelines":           len(self._pipelines),
            "store_entries":       self._store.count(),
            "records_processed":   self._processed,
        }
