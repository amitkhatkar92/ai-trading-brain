"""
iios/execution/analytics/performance/performance_events.py
==========================================================
PerformanceAnalyticsEvent — immutable domain events emitted by the
Performance Analytics Framework.

Seven factory functions cover the full analytics lifecycle.

C8 Execution Analytics & Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    ACTOR_ENGINE,
    ACTOR_SYSTEM,
    ENGINE_SYSTEM_ID,
    PerformanceEventType,
)


@dataclass(frozen=True)
class PerformanceAnalyticsEvent:
    """Immutable domain event for the Performance Analytics lifecycle."""

    event_id:    str
    event_type:  PerformanceEventType
    request_id:  str
    actor:       str
    system_id:   str
    payload:     Dict[str, Any]       = field(default_factory=dict)
    occurred_at: float                = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "request_id":  self.request_id,
            "actor":       self.actor,
            "system_id":   self.system_id,
            "payload":     dict(self.payload),
            "occurred_at": self.occurred_at,
        }


# ── Factory functions ─────────────────────────────────────────────────────────

def _make(
    event_type: PerformanceEventType,
    request_id: str,
    actor:      str,
    payload:    Dict[str, Any],
) -> PerformanceAnalyticsEvent:
    return PerformanceAnalyticsEvent(
        event_id   = str(uuid.uuid4()),
        event_type = event_type,
        request_id = request_id,
        actor      = actor,
        system_id  = ENGINE_SYSTEM_ID,
        payload    = payload,
    )


def make_analytics_started_event(
    request_id: str,
    actor:      str       = ACTOR_ENGINE,
    payload:    Optional[Dict[str, Any]] = None,
) -> PerformanceAnalyticsEvent:
    return _make(
        PerformanceEventType.ANALYTICS_STARTED, request_id, actor, payload or {}
    )


def make_kpi_calculated_event(
    request_id: str,
    kpi_count:  int,
    domain:     str,
    actor:      str = ACTOR_ENGINE,
) -> PerformanceAnalyticsEvent:
    return _make(
        PerformanceEventType.KPI_CALCULATED,
        request_id,
        actor,
        {"kpi_count": kpi_count, "domain": domain},
    )


def make_trend_detected_event(
    request_id:  str,
    trend_count: int,
    actor:       str = ACTOR_ENGINE,
) -> PerformanceAnalyticsEvent:
    return _make(
        PerformanceEventType.TREND_DETECTED,
        request_id,
        actor,
        {"trend_count": trend_count},
    )


def make_benchmark_completed_event(
    request_id:    str,
    overall_score: float,
    domain:        str,
    actor:         str = ACTOR_ENGINE,
) -> PerformanceAnalyticsEvent:
    return _make(
        PerformanceEventType.BENCHMARK_COMPLETED,
        request_id,
        actor,
        {"overall_score": overall_score, "domain": domain},
    )


def make_report_generated_event(
    request_id:    str,
    report_id:     str,
    processing_ms: float,
    actor:         str = ACTOR_ENGINE,
) -> PerformanceAnalyticsEvent:
    return _make(
        PerformanceEventType.REPORT_GENERATED,
        request_id,
        actor,
        {"report_id": report_id, "processing_ms": processing_ms},
    )


def make_analytics_published_event(
    request_id: str,
    report_id:  str,
    actor:      str = ACTOR_ENGINE,
) -> PerformanceAnalyticsEvent:
    return _make(
        PerformanceEventType.ANALYTICS_PUBLISHED,
        request_id,
        actor,
        {"report_id": report_id},
    )


def make_analytics_failed_event(
    request_id: str,
    error:      str,
    actor:      str = ACTOR_SYSTEM,
) -> PerformanceAnalyticsEvent:
    return _make(
        PerformanceEventType.ANALYTICS_FAILED,
        request_id,
        actor,
        {"error": error},
    )
