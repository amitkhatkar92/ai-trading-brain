"""iios/integration/pipeline/pipeline_stage.py

Abstract pipeline stage and concrete stage implementations.
"""
from __future__ import annotations

import abc
import time
from dataclasses import dataclass, field
from typing import Any

from iios.integration.integration_constants import PipelineStageStatus, PipelineStageType


@dataclass
class PipelineStageResult:
    """Outcome of one pipeline stage execution."""

    stage_type:   PipelineStageType  = PipelineStageType.EXTRACT
    status:       PipelineStageStatus = PipelineStageStatus.COMPLETED
    records_in:   int                = 0
    records_out:  int                = 0
    latency_ms:   float              = 0.0
    errors:       list[str]          = field(default_factory=list)
    warnings:     list[str]          = field(default_factory=list)
    metadata:     dict[str, Any]     = field(default_factory=dict)

    def is_successful(self) -> bool:
        return self.status == PipelineStageStatus.COMPLETED

    def records_dropped(self) -> int:
        return max(0, self.records_in - self.records_out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_type":   self.stage_type.value,
            "status":       self.status.value,
            "records_in":   self.records_in,
            "records_out":  self.records_out,
            "records_dropped": self.records_dropped(),
            "latency_ms":   round(self.latency_ms, 2),
            "errors":       self.errors,
            "warnings":     self.warnings,
            "metadata":     self.metadata,
        }


class PipelineStage(abc.ABC):
    """
    Abstract pipeline stage.

    Stages are composable, ordered units of processing.
    Each stage receives a PipelineContext and returns a PipelineStageResult.
    """

    @property
    @abc.abstractmethod
    def stage_type(self) -> PipelineStageType:
        """The type of this stage."""

    @property
    def name(self) -> str:
        return self.stage_type.value

    @abc.abstractmethod
    async def process(self, context: "PipelineContext") -> PipelineStageResult:
        """
        Execute the stage.

        Mutates context.records in place and returns a result summary.
        """

    def to_dict(self) -> dict[str, Any]:
        return {"stage_type": self.stage_type.value, "name": self.name}


# ── Concrete stages (thin wrappers; real logic lives in sub-engines) ──────────

class ExtractionStage(PipelineStage):
    """Calls the provider to fetch raw data."""

    @property
    def stage_type(self) -> PipelineStageType:
        return PipelineStageType.EXTRACT

    async def process(self, context: "PipelineContext") -> PipelineStageResult:
        from iios.integration.integration_exceptions import ProviderFetchError
        t0 = time.perf_counter()
        try:
            response = await context.provider.fetch(context.request)
            context.records = list(response.records)
            context.raw_response = response
            return PipelineStageResult(
                stage_type=self.stage_type,
                records_in=0,
                records_out=len(context.records),
                latency_ms=(time.perf_counter() - t0) * 1_000,
            )
        except Exception as exc:
            return PipelineStageResult(
                stage_type=self.stage_type,
                status=PipelineStageStatus.FAILED,
                errors=[str(exc)],
                latency_ms=(time.perf_counter() - t0) * 1_000,
            )


class ValidationStage(PipelineStage):
    """Validates records; drops or flags those that fail."""

    def __init__(self, drop_invalid: bool = False) -> None:
        self._drop_invalid = drop_invalid

    @property
    def stage_type(self) -> PipelineStageType:
        return PipelineStageType.VALIDATE

    async def process(self, context: "PipelineContext") -> PipelineStageResult:
        t0     = time.perf_counter()
        before = len(context.records)
        if context.validation_engine:
            report = context.validation_engine.validate_batch(context.records)
            if self._drop_invalid:
                context.records = report.valid_records
        return PipelineStageResult(
            stage_type=self.stage_type,
            records_in=before,
            records_out=len(context.records),
            latency_ms=(time.perf_counter() - t0) * 1_000,
        )


class NormalizationStage(PipelineStage):
    """Normalizes records to the canonical schema."""

    @property
    def stage_type(self) -> PipelineStageType:
        return PipelineStageType.NORMALIZE

    async def process(self, context: "PipelineContext") -> PipelineStageResult:
        t0     = time.perf_counter()
        before = len(context.records)
        if context.normalization_engine:
            context.records = context.normalization_engine.normalize_batch(context.records)
        return PipelineStageResult(
            stage_type=self.stage_type,
            records_in=before,
            records_out=len(context.records),
            latency_ms=(time.perf_counter() - t0) * 1_000,
        )


class TransformationStage(PipelineStage):
    """Applies caller-supplied transform functions to records."""

    @property
    def stage_type(self) -> PipelineStageType:
        return PipelineStageType.TRANSFORM

    async def process(self, context: "PipelineContext") -> PipelineStageResult:
        t0     = time.perf_counter()
        before = len(context.records)
        if context.transformers:
            for fn in context.transformers:
                context.records = [fn(r) for r in context.records if r is not None]
        return PipelineStageResult(
            stage_type=self.stage_type,
            records_in=before,
            records_out=len(context.records),
            latency_ms=(time.perf_counter() - t0) * 1_000,
        )


class EnrichmentStage(PipelineStage):
    """Adds derived or augmented fields."""

    @property
    def stage_type(self) -> PipelineStageType:
        return PipelineStageType.ENRICH

    async def process(self, context: "PipelineContext") -> PipelineStageResult:
        t0     = time.perf_counter()
        before = len(context.records)
        if context.enrichers:
            for fn in context.enrichers:
                context.records = [fn(r) for r in context.records if r is not None]
        return PipelineStageResult(
            stage_type=self.stage_type,
            records_in=before,
            records_out=len(context.records),
            latency_ms=(time.perf_counter() - t0) * 1_000,
        )


class CacheStage(PipelineStage):
    """Writes results to cache."""

    @property
    def stage_type(self) -> PipelineStageType:
        return PipelineStageType.CACHE

    async def process(self, context: "PipelineContext") -> PipelineStageResult:
        t0     = time.perf_counter()
        before = len(context.records)
        if context.cache and context.cache_key:
            context.cache.put(context.cache_key, context.records)
        return PipelineStageResult(
            stage_type=self.stage_type,
            records_in=before,
            records_out=before,
            latency_ms=(time.perf_counter() - t0) * 1_000,
        )


class PublishStage(PipelineStage):
    """Dispatches records to registered listeners."""

    @property
    def stage_type(self) -> PipelineStageType:
        return PipelineStageType.PUBLISH

    async def process(self, context: "PipelineContext") -> PipelineStageResult:
        t0     = time.perf_counter()
        before = len(context.records)
        if context.publisher:
            context.publisher(context.records, context.pipeline_id)
        return PipelineStageResult(
            stage_type=self.stage_type,
            records_in=before,
            records_out=before,
            latency_ms=(time.perf_counter() - t0) * 1_000,
        )


# Import guard for forward reference
from iios.integration.pipeline.pipeline_context import PipelineContext  # noqa: E402
