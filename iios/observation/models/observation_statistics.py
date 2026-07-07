"""
iios/observation/models/observation_statistics.py
=================================================
Aggregated statistics for the Observation Engine.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from ..observation_constants import ObservationStatus, ObservationType

__all__ = ["ObservationStatistics", "ObservationTypeStats"]


@dataclass
class ObservationTypeStats:
    """Per-type breakdown of observation counts."""

    obs_type:  str   = ""
    total:     int   = 0
    accepted:  int   = 0
    rejected:  int   = 0
    pending:   int   = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "obs_type": self.obs_type,
            "total":    self.total,
            "accepted": self.accepted,
            "rejected": self.rejected,
            "pending":  self.pending,
        }


@dataclass
class ObservationStatistics:
    """Snapshot statistics for the Observation Engine."""

    # Overall counts
    total_created:    int   = 0
    total_accepted:   int   = 0
    total_rejected:   int   = 0
    total_archived:   int   = 0
    total_expired:    int   = 0
    total_deleted:    int   = 0
    total_in_flight:  int   = 0    # not yet in terminal state

    # Pipeline metrics
    total_validated:  int   = 0
    total_classified: int   = 0
    total_enriched:   int   = 0
    total_duplicates: int   = 0
    total_batches:    int   = 0

    # Timing
    avg_pipeline_ms:  float = 0.0
    max_pipeline_ms:  float = 0.0
    min_pipeline_ms:  float = float("inf")

    # Per-type breakdown
    by_type:          dict[str, ObservationTypeStats] = field(default_factory=dict)

    # Engine health
    cache_hits:       int   = 0
    cache_misses:     int   = 0
    storage_size:     int   = 0

    # Timestamp
    computed_at:      float = field(default_factory=time.time)

    @property
    def acceptance_rate(self) -> float:
        if self.total_created == 0:
            return 0.0
        return self.total_accepted / self.total_created

    @property
    def rejection_rate(self) -> float:
        if self.total_created == 0:
            return 0.0
        return self.total_rejected / self.total_created

    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_created":    self.total_created,
            "total_accepted":   self.total_accepted,
            "total_rejected":   self.total_rejected,
            "total_archived":   self.total_archived,
            "total_expired":    self.total_expired,
            "total_deleted":    self.total_deleted,
            "total_in_flight":  self.total_in_flight,
            "total_validated":  self.total_validated,
            "total_classified": self.total_classified,
            "total_enriched":   self.total_enriched,
            "total_duplicates": self.total_duplicates,
            "total_batches":    self.total_batches,
            "avg_pipeline_ms":  self.avg_pipeline_ms,
            "max_pipeline_ms":  self.max_pipeline_ms,
            "acceptance_rate":  round(self.acceptance_rate, 4),
            "rejection_rate":   round(self.rejection_rate, 4),
            "cache_hit_rate":   round(self.cache_hit_rate, 4),
            "storage_size":     self.storage_size,
            "by_type":          {k: v.to_dict() for k, v in self.by_type.items()},
            "computed_at":      self.computed_at,
        }
