"""
iios/execution/analytics/engine/analytics_request.py
====================================================
AnalyticsRequest — immutable analytics request submitted to the Execution
Analytics Engine.

C8 Execution Analytics & Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import ACTOR_SYSTEM, VERSION, AnalyticsRequestType


@dataclass(frozen=True)
class AnalyticsRequest:
    """
    Immutable request submitted to the Execution Analytics Engine.

    Fields
    ------
    request_id:           Unique request identifier.
    execution_session_id: The execution session to analyse.
    request_type:         Classification of the request.
    requester:            Actor submitting the request.
    priority:             Dispatch priority (1 = highest, 10 = lowest).
    reason:               Human-readable reason for the request.
    tags:                 Classification tags.
    metadata:             Optional supplementary data.
    submitted_at:         Wall-time of submission.
    scheduled_at:         Wall-time at which analytics should start (None = immediate).
    framework_version:    Framework version.
    """

    request_id:           str
    execution_session_id: str
    request_type:         AnalyticsRequestType = AnalyticsRequestType.ON_DEMAND
    requester:            str                  = ACTOR_SYSTEM
    priority:             int                  = 5
    reason:               str                  = ""
    tags:                 Tuple[str, ...]       = field(default_factory=tuple)
    metadata:             Dict[str, Any]        = field(default_factory=dict)
    submitted_at:         float                = field(default_factory=time.time)
    scheduled_at:         Optional[float]      = None
    framework_version:    str                  = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":           self.request_id,
            "execution_session_id": self.execution_session_id,
            "request_type":         self.request_type.value,
            "requester":            self.requester,
            "priority":             self.priority,
            "reason":               self.reason,
            "tags":                 list(self.tags),
            "submitted_at":         self.submitted_at,
            "scheduled_at":         self.scheduled_at,
            "framework_version":    self.framework_version,
        }


def make_analytics_request(
    execution_session_id: str,
    *,
    request_id:   Optional[str]             = None,
    request_type: AnalyticsRequestType      = AnalyticsRequestType.ON_DEMAND,
    requester:    str                       = ACTOR_SYSTEM,
    priority:     int                       = 5,
    reason:       str                       = "",
    tags:         Tuple[str, ...]            = (),
    metadata:     Optional[Dict[str, Any]]  = None,
    scheduled_at: Optional[float]           = None,
) -> AnalyticsRequest:
    """Create a new AnalyticsRequest."""
    return AnalyticsRequest(
        request_id           = request_id or str(uuid.uuid4()),
        execution_session_id = execution_session_id,
        request_type         = request_type,
        requester            = requester,
        priority             = priority,
        reason               = reason,
        tags                 = tags,
        metadata             = metadata or {},
        scheduled_at         = scheduled_at,
    )
