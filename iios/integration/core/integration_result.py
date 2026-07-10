"""iios/integration/core/integration_result.py

Wraps the outcome of a full integration workflow run.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.integration_constants import PipelineStatus
from iios.integration.core.data_record import DataRecord


@dataclass
class IntegrationResult:
    """Full result of an integration pipeline execution."""

    pipeline_id:    str           = ""
    request_id:     str           = ""
    provider_id:    str           = ""
    status:         PipelineStatus = PipelineStatus.PENDING
    records:        list[DataRecord] = field(default_factory=list)
    records_in:     int           = 0
    records_out:    int           = 0
    records_dropped: int          = 0
    stage_results:  list[dict[str, Any]] = field(default_factory=list)
    error:          str | None    = None
    started_at:     float         = field(default_factory=time.time)
    completed_at:   float | None  = None
    result_id:      str           = field(default_factory=lambda: str(uuid.uuid4()))
    metadata:       dict[str, Any] = field(default_factory=dict)

    def duration_ms(self) -> float:
        if self.completed_at is None:
            return 0.0
        return (self.completed_at - self.started_at) * 1_000

    def is_successful(self) -> bool:
        return self.status == PipelineStatus.COMPLETED

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id":       self.result_id,
            "pipeline_id":     self.pipeline_id,
            "request_id":      self.request_id,
            "provider_id":     self.provider_id,
            "status":          self.status.value,
            "records_in":      self.records_in,
            "records_out":     self.records_out,
            "records_dropped": self.records_dropped,
            "stage_results":   self.stage_results,
            "error":           self.error,
            "started_at":      self.started_at,
            "completed_at":    self.completed_at,
            "duration_ms":     round(self.duration_ms(), 2),
            "metadata":        self.metadata,
        }


@dataclass
class ProviderContract:
    """
    Describes what data a provider offers.

    Registered alongside the provider for discovery and routing.
    """

    provider_id:   str                = ""
    categories:    list[str]          = field(default_factory=list)   # DataCategory values
    frequencies:   list[str]          = field(default_factory=list)   # DataFrequency values
    symbol_spaces: list[str]          = field(default_factory=list)   # e.g. ["NSE", "BSE", "GLOBAL"]
    schema_version: str               = "1.0"
    version:       str                = "1.0.0"
    metadata:      dict[str, Any]     = field(default_factory=dict)

    def supports_category(self, category: str) -> bool:
        return category in self.categories

    def supports_frequency(self, frequency: str) -> bool:
        return frequency in self.frequencies

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id":   self.provider_id,
            "categories":    self.categories,
            "frequencies":   self.frequencies,
            "symbol_spaces": self.symbol_spaces,
            "schema_version": self.schema_version,
            "version":       self.version,
            "metadata":      self.metadata,
        }
