"""
iios/observation/models/observation_metadata.py
===============================================
Rich metadata envelope attached to every Observation.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..observation_constants import (
    DEFAULT_CONFIDENCE,
    DEFAULT_TTL_SECONDS,
    MAX_CONFIDENCE,
    MAX_TAGS,
    MIN_CONFIDENCE,
    OBSERVATION_SCHEMA_VERSION,
    SYSTEM_OBSERVER,
    ObservationDomain,
    ObservationPriority,
    ObservationSource,
    ObservationQuality,
)

__all__ = ["ObservationMetadata"]


@dataclass
class ObservationMetadata:
    """Metadata envelope for an observation.

    All fields have sane defaults; enrich progressively as the
    observation moves through the pipeline.
    """

    # Ownership
    owner_id:       str                    = SYSTEM_OBSERVER
    created_by:     str                    = SYSTEM_OBSERVER
    updated_by:     str                    = SYSTEM_OBSERVER

    # Timestamps
    created_at:     float                  = field(default_factory=time.time)
    updated_at:     float                  = field(default_factory=time.time)
    observed_at:    Optional[float]        = None   # when event actually occurred
    expires_at:     Optional[float]        = None   # None = never

    # Domain context
    domain:         ObservationDomain      = ObservationDomain.GENERAL
    source:         ObservationSource      = ObservationSource.UNKNOWN
    priority:       ObservationPriority    = ObservationPriority.MEDIUM

    # Quality / confidence
    confidence:     float                  = DEFAULT_CONFIDENCE
    quality:        ObservationQuality     = ObservationQuality.FAIR
    quality_score:  float                  = 0.5

    # Descriptors
    description:    str                    = ""
    tags:           list[str]              = field(default_factory=list)
    labels:         dict[str, str]         = field(default_factory=dict)
    attributes:     dict[str, Any]         = field(default_factory=dict)

    # TTL
    ttl_seconds:    int                    = DEFAULT_TTL_SECONDS

    # Schema
    schema_version: str                    = OBSERVATION_SCHEMA_VERSION

    # Provenance
    source_uri:     str                    = ""
    checksum:       str                    = ""
    notes:          str                    = ""

    def __post_init__(self) -> None:
        self.confidence = max(MIN_CONFIDENCE, min(MAX_CONFIDENCE, self.confidence))
        if len(self.tags) > MAX_TAGS:
            self.tags = self.tags[:MAX_TAGS]
        if self.expires_at is None:
            if self.ttl_seconds > 0:
                self.expires_at = self.created_at + self.ttl_seconds
            elif self.ttl_seconds <= 0:
                # Negative or zero TTL → immediately expired
                self.expires_at = self.created_at - 1

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() >= self.expires_at

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "owner_id":       self.owner_id,
            "created_by":     self.created_by,
            "updated_by":     self.updated_by,
            "created_at":     self.created_at,
            "updated_at":     self.updated_at,
            "observed_at":    self.observed_at,
            "expires_at":     self.expires_at,
            "domain":         self.domain.value,
            "source":         self.source.value,
            "priority":       self.priority.value,
            "confidence":     self.confidence,
            "quality":        self.quality.value,
            "quality_score":  self.quality_score,
            "description":    self.description,
            "tags":           list(self.tags),
            "labels":         dict(self.labels),
            "attributes":     dict(self.attributes),
            "ttl_seconds":    self.ttl_seconds,
            "schema_version": self.schema_version,
            "source_uri":     self.source_uri,
            "checksum":       self.checksum,
            "notes":          self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ObservationMetadata":
        meta = cls(
            owner_id       = d.get("owner_id",       SYSTEM_OBSERVER),
            created_by     = d.get("created_by",     SYSTEM_OBSERVER),
            updated_by     = d.get("updated_by",     SYSTEM_OBSERVER),
            created_at     = d.get("created_at",     time.time()),
            updated_at     = d.get("updated_at",     time.time()),
            observed_at    = d.get("observed_at"),
            expires_at     = d.get("expires_at"),
            domain         = ObservationDomain(d.get("domain", ObservationDomain.GENERAL.value)),
            source         = ObservationSource(d.get("source", ObservationSource.UNKNOWN.value)),
            priority       = ObservationPriority(d.get("priority", ObservationPriority.MEDIUM.value)),
            confidence     = float(d.get("confidence", DEFAULT_CONFIDENCE)),
            quality        = ObservationQuality(d.get("quality", ObservationQuality.FAIR.value)),
            quality_score  = float(d.get("quality_score", 0.5)),
            description    = d.get("description",    ""),
            tags           = list(d.get("tags",       [])),
            labels         = dict(d.get("labels",     {})),
            attributes     = dict(d.get("attributes", {})),
            ttl_seconds    = int(d.get("ttl_seconds", DEFAULT_TTL_SECONDS)),
            schema_version = d.get("schema_version",  OBSERVATION_SCHEMA_VERSION),
            source_uri     = d.get("source_uri",      ""),
            checksum       = d.get("checksum",        ""),
            notes          = d.get("notes",           ""),
        )
        return meta
