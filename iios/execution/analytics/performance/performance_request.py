"""
iios/execution/analytics/performance/performance_request.py
============================================================
PerformanceRequest — immutable analytics request for the Performance
Analytics Framework.

C8 Execution Analytics & Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import ACTOR_SYSTEM, VERSION, AggregationWindow, KPIType, PerformanceDomain


@dataclass(frozen=True)
class PerformanceRequest:
    """
    Immutable request submitted to the Performance Analytics Engine.

    Fields
    ------
    request_id:         Unique request identifier.
    domain:             Performance domain to analyse.
    window:             Aggregation window.
    kpi_types:          KPIs to compute (empty = all applicable KPIs).
    include_trends:     Whether to run trend analysis.
    include_benchmarks: Whether to run benchmark comparison.
    include_scorecard:  Whether to build a performance scorecard.
    requester:          Actor submitting the request.
    priority:           Dispatch priority (1 = highest).
    reason:             Human-readable reason.
    tags:               Classification tags.
    metadata:           Optional supplementary data.
    submitted_at:       Wall-time of submission.
    framework_version:  Framework version.
    """

    request_id:         str
    domain:             PerformanceDomain
    window:             AggregationWindow    = AggregationWindow.REAL_TIME
    kpi_types:          Tuple[KPIType, ...]  = field(default_factory=tuple)
    include_trends:     bool                 = False
    include_benchmarks: bool                 = True
    include_scorecard:  bool                 = True
    requester:          str                  = ACTOR_SYSTEM
    priority:           int                  = 5
    reason:             str                  = ""
    tags:               Tuple[str, ...]       = field(default_factory=tuple)
    metadata:           Dict[str, Any]        = field(default_factory=dict)
    submitted_at:       float                = field(default_factory=time.time)
    framework_version:  str                  = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":         self.request_id,
            "domain":             self.domain.value,
            "window":             self.window.value,
            "kpi_types":          [k.value for k in self.kpi_types],
            "include_trends":     self.include_trends,
            "include_benchmarks": self.include_benchmarks,
            "include_scorecard":  self.include_scorecard,
            "requester":          self.requester,
            "priority":           self.priority,
            "reason":             self.reason,
            "submitted_at":       self.submitted_at,
            "framework_version":  self.framework_version,
        }


def make_performance_request(
    domain:             PerformanceDomain,
    *,
    request_id:         Optional[str]                 = None,
    window:             AggregationWindow             = AggregationWindow.REAL_TIME,
    kpi_types:          Tuple[KPIType, ...]            = (),
    include_trends:     bool                          = False,
    include_benchmarks: bool                          = True,
    include_scorecard:  bool                          = True,
    requester:          str                           = ACTOR_SYSTEM,
    priority:           int                           = 5,
    reason:             str                           = "",
    tags:               Tuple[str, ...]                = (),
    metadata:           Optional[Dict[str, Any]]      = None,
) -> PerformanceRequest:
    """Create a new PerformanceRequest."""
    return PerformanceRequest(
        request_id         = request_id or str(uuid.uuid4()),
        domain             = domain,
        window             = window,
        kpi_types          = kpi_types,
        include_trends     = include_trends,
        include_benchmarks = include_benchmarks,
        include_scorecard  = include_scorecard,
        requester          = requester,
        priority           = priority,
        reason             = reason,
        tags               = tags,
        metadata           = metadata or {},
    )
