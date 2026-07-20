"""
iios/execution/analytics/snapshot/analytics_snapshot_metadata.py
=================================================================
AnalyticsMetadata and AuditMetadata — immutable metadata containers
for ExecutionAnalyticsSnapshot.

C8 Execution Analytics & Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import ACTOR_BUILDER, SNAPSHOT_FRAMEWORK_VERSION


@dataclass(frozen=True)
class AnalyticsMetadata:
    """
    Metadata describing the analytics context that produced a snapshot.

    Immutable.  Populated by the builder from session and engine data.
    """

    source_version:    str                = SNAPSHOT_FRAMEWORK_VERSION
    build_duration_ms: float              = 0.0
    data_sources:      Tuple[str, ...]    = field(default_factory=tuple)
    tags:              Tuple[str, ...]    = field(default_factory=tuple)
    properties:        Dict[str, Any]     = field(default_factory=dict)
    notes:             str                = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_version":    self.source_version,
            "build_duration_ms": self.build_duration_ms,
            "data_sources":      list(self.data_sources),
            "tags":              list(self.tags),
            "properties":        dict(self.properties),
            "notes":             self.notes,
        }


@dataclass(frozen=True)
class AuditMetadata:
    """
    Audit trail for a snapshot — who created, validated, and published it.

    Immutable.  Populated by the builder and store.
    """

    created_by:    str            = ACTOR_BUILDER
    created_at:    float          = field(default_factory=time.time)
    validated_by:  str            = ""
    validated_at:  Optional[float] = None
    published_by:  str            = ""
    published_at:  Optional[float] = None
    audit_trail:   Tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "created_by":   self.created_by,
            "created_at":   self.created_at,
            "validated_by": self.validated_by,
            "validated_at": self.validated_at,
            "published_by": self.published_by,
            "published_at": self.published_at,
            "audit_trail":  list(self.audit_trail),
        }
