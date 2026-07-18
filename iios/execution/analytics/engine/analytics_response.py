"""
iios/execution/analytics/engine/analytics_response.py
=====================================================
AnalyticsResponse and AnalyticsSnapshot — output types of the Execution
Analytics Engine.

C8 Execution Analytics & Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import VERSION, ResponseStatus, EngineAnalyticsState


@dataclass(frozen=True)
class AnalyticsSnapshot:
    """
    Immutable point-in-time snapshot published by the Analytics Engine
    upon completion of an analytics cycle.

    Fields
    ------
    snapshot_id:       Globally unique snapshot ID.
    engine_state:      Engine state at snapshot capture.
    request_id:        Request that triggered this snapshot.
    session_id:        Analytics lifecycle session ID.
    pipeline_id:       Pipeline that was dispatched (if any).
    captured_at:       Wall-time of capture.
    metadata:          Supplementary data.
    framework_version: Framework version.
    """

    snapshot_id:       str
    engine_state:      EngineAnalyticsState
    request_id:        str              = ""
    session_id:        str              = ""
    pipeline_id:       str              = ""
    captured_at:       float            = field(default_factory=time.time)
    metadata:          Dict[str, Any]   = field(default_factory=dict)
    framework_version: str              = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":       self.snapshot_id,
            "engine_state":      self.engine_state.value,
            "request_id":        self.request_id,
            "session_id":        self.session_id,
            "pipeline_id":       self.pipeline_id,
            "captured_at":       self.captured_at,
            "framework_version": self.framework_version,
        }


@dataclass(frozen=True)
class AnalyticsResponse:
    """
    Immutable response returned by the Execution Analytics Engine after
    processing an AnalyticsRequest.

    Fields
    ------
    response_id:       Unique response ID.
    request_id:        Request that generated this response.
    status:            Overall outcome of the analytics cycle.
    session_id:        Analytics lifecycle session ID.
    pipeline_id:       Pipeline that was dispatched.
    snapshot:          Published analytics snapshot (available on SUCCESS).
    error_message:     Error description (only on FAILED/REJECTED status).
    processing_ms:     Total processing time in milliseconds.
    collection_ms:     Collection phase duration in milliseconds.
    dispatch_ms:       Dispatch phase duration in milliseconds.
    metadata:          Supplementary data.
    responded_at:      Wall-time of response creation.
    framework_version: Framework version.
    """

    response_id:       str
    request_id:        str
    status:            ResponseStatus
    session_id:        str                         = ""
    pipeline_id:       str                         = ""
    snapshot:          Optional[AnalyticsSnapshot] = None
    error_message:     str                         = ""
    processing_ms:     float                       = 0.0
    collection_ms:     float                       = 0.0
    dispatch_ms:       float                       = 0.0
    metadata:          Dict[str, Any]              = field(default_factory=dict)
    responded_at:      float                       = field(default_factory=time.time)
    framework_version: str                         = VERSION

    @property
    def is_success(self) -> bool:
        return self.status == ResponseStatus.SUCCESS

    @property
    def is_failed(self) -> bool:
        return self.status in (ResponseStatus.FAILED, ResponseStatus.REJECTED)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":      self.response_id,
            "request_id":       self.request_id,
            "status":           self.status.value,
            "session_id":       self.session_id,
            "pipeline_id":      self.pipeline_id,
            "error_message":    self.error_message,
            "processing_ms":    self.processing_ms,
            "collection_ms":    self.collection_ms,
            "dispatch_ms":      self.dispatch_ms,
            "responded_at":     self.responded_at,
            "framework_version":self.framework_version,
            "snapshot":         self.snapshot.to_dict() if self.snapshot else None,
        }


def make_analytics_snapshot(
    engine_state: EngineAnalyticsState,
    *,
    snapshot_id: Optional[str]            = None,
    request_id:  str                      = "",
    session_id:  str                      = "",
    pipeline_id: str                      = "",
    metadata:    Optional[Dict[str, Any]] = None,
) -> AnalyticsSnapshot:
    """Create a new AnalyticsSnapshot."""
    return AnalyticsSnapshot(
        snapshot_id  = snapshot_id or str(uuid.uuid4()),
        engine_state = engine_state,
        request_id   = request_id,
        session_id   = session_id,
        pipeline_id  = pipeline_id,
        metadata     = metadata or {},
    )


def make_analytics_response(
    request_id: str,
    status:     ResponseStatus,
    *,
    response_id:   Optional[str]               = None,
    session_id:    str                         = "",
    pipeline_id:   str                         = "",
    snapshot:      Optional[AnalyticsSnapshot] = None,
    error_message: str                         = "",
    processing_ms: float                       = 0.0,
    collection_ms: float                       = 0.0,
    dispatch_ms:   float                       = 0.0,
    metadata:      Optional[Dict[str, Any]]    = None,
) -> AnalyticsResponse:
    """Create a new AnalyticsResponse."""
    return AnalyticsResponse(
        response_id   = response_id or str(uuid.uuid4()),
        request_id    = request_id,
        status        = status,
        session_id    = session_id,
        pipeline_id   = pipeline_id,
        snapshot      = snapshot,
        error_message = error_message,
        processing_ms = processing_ms,
        collection_ms = collection_ms,
        dispatch_ms   = dispatch_ms,
        metadata      = metadata or {},
    )
