"""features/feature_pipeline.py — Ordered chain of FeatureTransformers."""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Optional

from iios.integration.research.learning.learning_exceptions import FeaturePipelineError
from iios.integration.research.learning.features.feature_transformer import FeatureTransformerProtocol


class FeaturePipeline:
    """
    Ordered sequence of FeatureTransformerProtocol steps.

    The pipeline applies each step to every record dict and propagates the
    output into the next step.  Steps must be fitted before transform.
    """

    def __init__(
        self,
        pipeline_id: Optional[str] = None,
        name:        str           = "default",
    ) -> None:
        self.pipeline_id = pipeline_id or f"fp_{uuid.uuid4().hex[:10]}"
        self.name        = name
        self._steps:  list[FeatureTransformerProtocol] = []
        self._fitted  = False
        self._lock    = threading.RLock()

    # ── Building ──────────────────────────────────────────────────────────────

    def add_step(self, transformer: FeatureTransformerProtocol) -> "FeaturePipeline":
        with self._lock:
            self._steps.append(transformer)
            self._fitted = False
        return self

    def remove_step(self, transformer_id: str) -> None:
        with self._lock:
            self._steps = [s for s in self._steps if s.transformer_id != transformer_id]
            self._fitted = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def fit(self, records: list[dict[str, Any]]) -> None:
        with self._lock:
            current = list(records)
            for step in self._steps:
                try:
                    step.fit(current)
                    current = [step.transform(r) for r in current]
                except Exception as exc:
                    raise FeaturePipelineError(
                        f"Step '{step.name}' failed during fit: {exc}"
                    ) from exc
            self._fitted = True

    def transform(self, record: dict[str, Any]) -> dict[str, Any]:
        if not self._fitted:
            raise FeaturePipelineError("Pipeline must be fitted before transform")
        with self._lock:
            steps = list(self._steps)
        result = dict(record)
        for step in steps:
            try:
                result = step.transform(result)
            except Exception as exc:
                raise FeaturePipelineError(
                    f"Step '{step.name}' failed during transform: {exc}"
                ) from exc
        return result

    def transform_batch(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [self.transform(r) for r in records]

    def is_fitted(self) -> bool:
        with self._lock:
            return self._fitted

    def step_count(self) -> int:
        with self._lock:
            return len(self._steps)

    def step_names(self) -> list[str]:
        with self._lock:
            return [s.name for s in self._steps]

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "pipeline_id": self.pipeline_id,
                "name":        self.name,
                "step_count":  len(self._steps),
                "is_fitted":   self._fitted,
                "steps":       [s.to_dict() for s in self._steps],
            }
