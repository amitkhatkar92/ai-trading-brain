"""iios/integration/pipeline/pipeline_context.py

Mutable context passed through all pipeline stages.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from iios.integration.core.data_record import DataRecord, DataRequest, DataResponse


@dataclass
class PipelineContext:
    """
    Mutable bag of data that flows through the pipeline.

    Stages read and write this object instead of passing data as arguments,
    which allows stages to be added/removed without signature changes.
    """

    # Identity
    pipeline_id:  str = field(default_factory=lambda: str(uuid.uuid4()))
    request:      DataRequest = field(default_factory=DataRequest)
    provider:     Any = None   # BaseProvider — typed as Any to avoid circular

    # Data — stages mutate this list
    records:      list[DataRecord] = field(default_factory=list)
    raw_response: DataResponse | None = None

    # Pluggable sub-engines (all optional)
    validation_engine:    Any | None = None
    normalization_engine: Any | None = None
    cache:                Any | None = None
    cache_key:            str | None = None
    publisher:            Callable[[list[DataRecord], str], None] | None = None
    transformers:         list[Callable[[DataRecord], DataRecord]] = field(default_factory=list)
    enrichers:            list[Callable[[DataRecord], DataRecord]] = field(default_factory=list)

    # Telemetry
    started_at:   float = field(default_factory=time.time)
    metadata:     dict[str, Any] = field(default_factory=dict)

    def elapsed_ms(self) -> float:
        return (time.time() - self.started_at) * 1_000

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_id":  self.pipeline_id,
            "provider_id":  self.request.provider_id,
            "record_count": len(self.records),
            "started_at":   self.started_at,
            "elapsed_ms":   round(self.elapsed_ms(), 2),
            "metadata":     self.metadata,
        }
