"""
iios/observation/repositories/observation_query.py
==================================================
Query builder for filtering observations from the storage layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from ..observation_constants import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    ObservationDomain,
    ObservationSource,
    ObservationStatus,
    ObservationType,
    ObservationPriority,
    SortOrder,
)

__all__ = ["ObservationQuery", "SortOrder"]


# Re-export for convenience
from ..observation_constants import SortOrder  # noqa: F811


@dataclass
class ObservationQuery:
    """Fluent query builder for observation store filtering.

    Usage::

        q = (ObservationQuery()
             .with_status(ObservationStatus.ACCEPTED)
             .with_type(ObservationType.MARKET_DATA)
             .with_domain(ObservationDomain.MARKET)
             .order_by("created_at", SortOrder.DESC)
             .limit(100))
    """

    # Filters
    obs_ids:         list[str]                      = field(default_factory=list)
    obs_types:       list[ObservationType]           = field(default_factory=list)
    statuses:        list[ObservationStatus]         = field(default_factory=list)
    domains:         list[ObservationDomain]         = field(default_factory=list)
    sources:         list[ObservationSource]         = field(default_factory=list)
    priorities:      list[ObservationPriority]       = field(default_factory=list)
    tags:            list[str]                       = field(default_factory=list)
    instruments:     list[str]                       = field(default_factory=list)
    exchanges:       list[str]                       = field(default_factory=list)

    # Full-text / title
    title_contains:  Optional[str]                  = None

    # Confidence range
    min_confidence:  Optional[float]                = None
    max_confidence:  Optional[float]                = None

    # Time range (created_at)
    created_after:   Optional[float]                = None
    created_before:  Optional[float]                = None

    # Observed-at range
    observed_after:  Optional[float]                = None
    observed_before: Optional[float]                = None

    # Pagination
    page_size:       int                            = DEFAULT_PAGE_SIZE
    page_offset:     int                            = 0

    # Sorting
    sort_field:      str                            = "created_at"
    sort_order:      SortOrder                      = SortOrder.DESC

    # Include soft-deleted?
    include_deleted: bool                           = False

    # ── Fluent helpers ────────────────────────────────────────────────────────

    def with_id(self, obs_id: str) -> "ObservationQuery":
        self.obs_ids.append(obs_id)
        return self

    def with_type(self, obs_type: ObservationType) -> "ObservationQuery":
        self.obs_types.append(obs_type)
        return self

    def with_status(self, status: ObservationStatus) -> "ObservationQuery":
        self.statuses.append(status)
        return self

    def with_domain(self, domain: ObservationDomain) -> "ObservationQuery":
        self.domains.append(domain)
        return self

    def with_source(self, source: ObservationSource) -> "ObservationQuery":
        self.sources.append(source)
        return self

    def with_tag(self, tag: str) -> "ObservationQuery":
        self.tags.append(tag)
        return self

    def with_instrument(self, instrument: str) -> "ObservationQuery":
        self.instruments.append(instrument)
        return self

    def with_confidence(self, min_c: float = 0.0, max_c: float = 1.0) -> "ObservationQuery":
        self.min_confidence = min_c
        self.max_confidence = max_c
        return self

    def created_between(self, after: float, before: float) -> "ObservationQuery":
        self.created_after  = after
        self.created_before = before
        return self

    def order_by(self, field_name: str, order: SortOrder = SortOrder.DESC) -> "ObservationQuery":
        self.sort_field = field_name
        self.sort_order = order
        return self

    def limit(self, n: int) -> "ObservationQuery":
        self.page_size = min(max(1, n), MAX_PAGE_SIZE)
        return self

    def offset(self, n: int) -> "ObservationQuery":
        self.page_offset = max(0, n)
        return self

    def matches(self, obs: Any) -> bool:
        """Return True if *obs* (an Observation) satisfies all filter criteria."""
        if not self.include_deleted and obs.is_deleted:
            return False
        if self.obs_ids and obs.id not in self.obs_ids:
            return False
        if self.obs_types and obs.obs_type not in self.obs_types:
            return False
        if self.statuses and obs.status not in self.statuses:
            return False
        if self.domains and obs.metadata.domain not in self.domains:
            return False
        if self.sources and obs.metadata.source not in self.sources:
            return False
        if self.priorities and obs.metadata.priority not in self.priorities:
            return False
        if self.tags:
            obs_tags = set(obs.metadata.tags)
            if not obs_tags.issuperset(self.tags):
                return False
        if self.instruments and obs.source_info.instrument not in self.instruments:
            return False
        if self.exchanges and obs.source_info.exchange not in self.exchanges:
            return False
        if self.title_contains and self.title_contains.lower() not in obs.title.lower():
            return False
        if self.min_confidence is not None and obs.metadata.confidence < self.min_confidence:
            return False
        if self.max_confidence is not None and obs.metadata.confidence > self.max_confidence:
            return False
        if self.created_after  is not None and obs.created_at < self.created_after:
            return False
        if self.created_before is not None and obs.created_at > self.created_before:
            return False
        return True
