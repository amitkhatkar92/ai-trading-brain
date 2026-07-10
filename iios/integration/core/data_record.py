"""iios/integration/core/data_record.py

Canonical data types flowing through the integration pipeline.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.integration_constants import (
    DataCategory,
    DataFrequency,
    DataQualityLevel,
    CANONICAL_SCHEMA_VERSION,
)


@dataclass
class DataRecord:
    """
    The atomic unit of data flowing through the integration layer.

    All providers produce DataRecord objects; all consumers receive them.
    The payload is a dict in the canonical schema for its category.
    """

    provider_id:     str              = ""
    category:        DataCategory     = DataCategory.MARKET_DATA
    frequency:       DataFrequency    = DataFrequency.ON_DEMAND
    symbol:          str | None       = None
    timestamp:       float            = 0.0     # data timestamp (UTC epoch)
    received_at:     float            = field(default_factory=time.time)
    payload:         dict[str, Any]   = field(default_factory=dict)
    schema_version:  str              = CANONICAL_SCHEMA_VERSION
    quality:         DataQualityLevel = DataQualityLevel.UNKNOWN
    quality_score:   float            = 0.0     # 0.0–1.0
    record_id:       str              = field(default_factory=lambda: str(uuid.uuid4()))
    pipeline_id:     str | None       = None
    request_id:      str | None       = None
    metadata:        dict[str, Any]   = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id":      self.record_id,
            "provider_id":    self.provider_id,
            "category":       self.category.value,
            "frequency":      self.frequency.value,
            "symbol":         self.symbol,
            "timestamp":      self.timestamp,
            "received_at":    self.received_at,
            "payload":        self.payload,
            "schema_version": self.schema_version,
            "quality":        self.quality.value,
            "quality_score":  self.quality_score,
            "pipeline_id":    self.pipeline_id,
            "request_id":     self.request_id,
            "metadata":       self.metadata,
        }


@dataclass
class DataRequest:
    """
    A request for data from a provider.

    The integration layer constructs DataRequests and passes them to providers.
    """

    provider_id:  str              = ""
    category:     DataCategory     = DataCategory.MARKET_DATA
    symbols:      list[str]        = field(default_factory=list)
    frequency:    DataFrequency    = DataFrequency.ON_DEMAND
    start_time:   float | None     = None   # UTC epoch
    end_time:     float | None     = None
    parameters:   dict[str, Any]   = field(default_factory=dict)
    timeout_sec:  float            = 15.0
    max_records:  int              = 100_000
    request_id:   str              = field(default_factory=lambda: str(uuid.uuid4()))
    created_at:   float            = field(default_factory=time.time)
    metadata:     dict[str, Any]   = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id":  self.request_id,
            "provider_id": self.provider_id,
            "category":    self.category.value,
            "symbols":     self.symbols,
            "frequency":   self.frequency.value,
            "start_time":  self.start_time,
            "end_time":    self.end_time,
            "timeout_sec": self.timeout_sec,
            "parameters":  self.parameters,
            "created_at":  self.created_at,
        }


@dataclass
class DataResponse:
    """
    The result of a DataRequest, produced by a provider.
    """

    request_id:  str              = ""
    provider_id: str              = ""
    records:     list[DataRecord] = field(default_factory=list)
    success:     bool             = True
    error:       str | None       = None
    error_code:  str | None       = None
    latency_ms:  float            = 0.0
    fetched_at:  float            = field(default_factory=time.time)
    partial:     bool             = False   # True if only some data returned
    metadata:    dict[str, Any]   = field(default_factory=dict)

    def record_count(self) -> int:
        return len(self.records)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id":   self.request_id,
            "provider_id":  self.provider_id,
            "record_count": self.record_count(),
            "success":      self.success,
            "error":        self.error,
            "latency_ms":   round(self.latency_ms, 2),
            "fetched_at":   self.fetched_at,
            "partial":      self.partial,
            "metadata":     self.metadata,
        }
