"""iios/integration/pipeline/pipeline_builder.py

Fluent builder for constructing Pipeline stage sequences.
"""
from __future__ import annotations

from typing import Any, Callable

from iios.integration.integration_constants import PipelineStageType
from iios.integration.integration_exceptions import PipelineConfigurationError
from iios.integration.pipeline.pipeline_stage import (
    CacheStage,
    EnrichmentStage,
    ExtractionStage,
    NormalizationStage,
    PipelineStage,
    PublishStage,
    TransformationStage,
    ValidationStage,
)


class Pipeline:
    """
    An ordered sequence of PipelineStages with optional configuration.
    """

    def __init__(
        self,
        pipeline_id:  str,
        stages:       list[PipelineStage],
        drop_invalid: bool = False,
        metadata:     dict[str, Any] | None = None,
    ) -> None:
        self.pipeline_id  = pipeline_id
        self.stages       = stages
        self.drop_invalid = drop_invalid
        self.metadata     = metadata or {}

    def stage_types(self) -> list[str]:
        return [s.stage_type.value for s in self.stages]

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_id":  self.pipeline_id,
            "stages":       self.stage_types(),
            "drop_invalid": self.drop_invalid,
            "metadata":     self.metadata,
        }


class PipelineBuilder:
    """
    Fluent builder for Pipeline objects.

    Usage::

        pipeline = (
            PipelineBuilder("my-pipeline")
            .extract()
            .validate(drop_invalid=True)
            .normalize()
            .transform(lambda r: r)
            .cache()
            .publish()
            .build()
        )
    """

    def __init__(self, pipeline_id: str) -> None:
        self._pipeline_id  = pipeline_id
        self._stages:  list[PipelineStage] = []
        self._drop_invalid = False
        self._metadata:    dict[str, Any]  = {}

    def extract(self) -> "PipelineBuilder":
        self._stages.append(ExtractionStage())
        return self

    def validate(self, drop_invalid: bool = False) -> "PipelineBuilder":
        self._drop_invalid = drop_invalid
        self._stages.append(ValidationStage(drop_invalid=drop_invalid))
        return self

    def normalize(self) -> "PipelineBuilder":
        self._stages.append(NormalizationStage())
        return self

    def transform(
        self,
        *fns: Callable,
    ) -> "PipelineBuilder":
        stage = TransformationStage()
        self._stages.append(stage)
        # transformers are injected into context at runtime; stored here as hint
        self._metadata.setdefault("transformers", []).extend(
            [f.__name__ if hasattr(f, "__name__") else str(f) for f in fns]
        )
        return self

    def enrich(self) -> "PipelineBuilder":
        self._stages.append(EnrichmentStage())
        return self

    def cache(self) -> "PipelineBuilder":
        self._stages.append(CacheStage())
        return self

    def publish(self) -> "PipelineBuilder":
        self._stages.append(PublishStage())
        return self

    def add_stage(self, stage: PipelineStage) -> "PipelineBuilder":
        self._stages.append(stage)
        return self

    def meta(self, **kwargs: Any) -> "PipelineBuilder":
        self._metadata.update(kwargs)
        return self

    def build(self) -> Pipeline:
        if not self._stages:
            raise PipelineConfigurationError(
                f"Pipeline '{self._pipeline_id}' has no stages"
            )
        return Pipeline(
            pipeline_id=self._pipeline_id,
            stages=list(self._stages),
            drop_invalid=self._drop_invalid,
            metadata=self._metadata,
        )
