"""
iios/execution/analytics/lifecycle/analytics_metadata.py
========================================================
AnalyticsMetadata — immutable supplementary metadata for an analytics
session.

C8 Execution Analytics & Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import VERSION


@dataclass(frozen=True)
class AnalyticsMetadata:
    """
    Immutable supplementary metadata for an analytics session.

    Fields
    ------
    metadata_id:           Unique ID for this metadata record.
    analytics_session_id:  Parent analytics session.
    data_window_seconds:   Time window (seconds) for data collection.
    sample_count:          Number of data samples collected.
    collection_start:      Wall-time data collection started.
    collection_end:        Wall-time data collection ended.
    analysis_start:        Wall-time analysis started.
    analysis_end:          Wall-time analysis ended.
    collection_data:       Key-value data from the COLLECTING phase.
    analysis_data:         Key-value data from the ANALYZING phase.
    created_at:            Wall-time of creation.
    framework_version:     Platform version.
    """

    metadata_id:           str
    analytics_session_id:  str
    data_window_seconds:   float            = 60.0
    sample_count:          int              = 0
    collection_start:      Optional[float]  = None
    collection_end:        Optional[float]  = None
    analysis_start:        Optional[float]  = None
    analysis_end:          Optional[float]  = None
    collection_data:       Dict[str, Any]   = field(default_factory=dict, compare=False)
    analysis_data:         Dict[str, Any]   = field(default_factory=dict, compare=False)
    created_at:            float            = field(default_factory=time.time, compare=False)
    framework_version:     str              = VERSION

    @property
    def collection_duration_seconds(self) -> Optional[float]:
        if self.collection_start is not None and self.collection_end is not None:
            return self.collection_end - self.collection_start
        return None

    @property
    def analysis_duration_seconds(self) -> Optional[float]:
        if self.analysis_start is not None and self.analysis_end is not None:
            return self.analysis_end - self.analysis_start
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata_id":           self.metadata_id,
            "analytics_session_id":  self.analytics_session_id,
            "data_window_seconds":   self.data_window_seconds,
            "sample_count":          self.sample_count,
            "collection_start":      self.collection_start,
            "collection_end":        self.collection_end,
            "analysis_start":        self.analysis_start,
            "analysis_end":          self.analysis_end,
            "collection_data":       dict(self.collection_data),
            "analysis_data":         dict(self.analysis_data),
            "created_at":            self.created_at,
            "framework_version":     self.framework_version,
        }


def make_analytics_metadata(
    analytics_session_id: str,
    *,
    data_window_seconds:  float  = 60.0,
    sample_count:         int    = 0,
    collection_start:     Optional[float]           = None,
    collection_end:       Optional[float]           = None,
    analysis_start:       Optional[float]           = None,
    analysis_end:         Optional[float]           = None,
    collection_data:      Optional[Dict[str, Any]]  = None,
    analysis_data:        Optional[Dict[str, Any]]  = None,
    metadata_id:          Optional[str]             = None,
) -> AnalyticsMetadata:
    """Factory for AnalyticsMetadata."""
    return AnalyticsMetadata(
        metadata_id          = metadata_id or str(uuid.uuid4()),
        analytics_session_id = analytics_session_id,
        data_window_seconds  = data_window_seconds,
        sample_count         = sample_count,
        collection_start     = collection_start,
        collection_end       = collection_end,
        analysis_start       = analysis_start,
        analysis_end         = analysis_end,
        collection_data      = dict(collection_data) if collection_data else {},
        analysis_data        = dict(analysis_data)   if analysis_data   else {},
    )
