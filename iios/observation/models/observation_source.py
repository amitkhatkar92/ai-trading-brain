"""
iios/observation/models/observation_source.py
=============================================
Source descriptor — captures the provenance of an observation.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..observation_constants import (
    ANONYMOUS_SOURCE,
    OBSERVATION_SCHEMA_VERSION,
    SYSTEM_OBSERVER,
    ObservationSource,
)

__all__ = ["ObservationSourceInfo"]


@dataclass
class ObservationSourceInfo:
    """Full provenance descriptor for an observation.

    Instances are lightweight and JSON-serialisable.
    """

    # Primary source enum
    source:        ObservationSource   = ObservationSource.UNKNOWN

    # Human-readable / URI identifier of the originating feed/system
    source_id:     str                 = ""
    source_name:   str                 = ""
    source_uri:    str                 = ""

    # When the event occurred at the source (may differ from ingestion time)
    source_timestamp: Optional[float]  = None

    # Who submitted it to the Observation Engine
    submitted_by:  str                 = SYSTEM_OBSERVER

    # Optional correlation ID from the source system
    correlation_id: str                = ""

    # Feed / collection metadata
    feed_name:     str                 = ""
    feed_version:  str                 = ""
    batch_id:      str                 = ""   # ID of the batch this belonged to

    # Geo context
    exchange:      str                 = ""   # e.g. "NSE", "BSE"
    instrument:    str                 = ""   # symbol / ISIN
    asset_class:   str                 = ""   # equity, futures, options, fx …

    # Extra key/value attributes
    attributes:    dict[str, Any]      = field(default_factory=dict)

    schema_version: str                = OBSERVATION_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "source":           self.source.value,
            "source_id":        self.source_id,
            "source_name":      self.source_name,
            "source_uri":       self.source_uri,
            "source_timestamp": self.source_timestamp,
            "submitted_by":     self.submitted_by,
            "correlation_id":   self.correlation_id,
            "feed_name":        self.feed_name,
            "feed_version":     self.feed_version,
            "batch_id":         self.batch_id,
            "exchange":         self.exchange,
            "instrument":       self.instrument,
            "asset_class":      self.asset_class,
            "attributes":       dict(self.attributes),
            "schema_version":   self.schema_version,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ObservationSourceInfo":
        return cls(
            source           = ObservationSource(d.get("source", ObservationSource.UNKNOWN.value)),
            source_id        = d.get("source_id",        ""),
            source_name      = d.get("source_name",      ""),
            source_uri       = d.get("source_uri",       ""),
            source_timestamp = d.get("source_timestamp"),
            submitted_by     = d.get("submitted_by",     SYSTEM_OBSERVER),
            correlation_id   = d.get("correlation_id",  ""),
            feed_name        = d.get("feed_name",        ""),
            feed_version     = d.get("feed_version",     ""),
            batch_id         = d.get("batch_id",         ""),
            exchange         = d.get("exchange",         ""),
            instrument       = d.get("instrument",       ""),
            asset_class      = d.get("asset_class",      ""),
            attributes       = dict(d.get("attributes",  {})),
            schema_version   = d.get("schema_version",   OBSERVATION_SCHEMA_VERSION),
        )
