"""
iios/execution/analytics/predictive/predictive_events.py
========================================================
PredictiveIntelligenceEvent — immutable domain events for the
Predictive Intelligence Framework lifecycle.

Seven factory functions cover the full prediction lifecycle.

C8 Execution Analytics & Intelligence — Phase 1, Module 4
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
    PredictionEventType,
)


@dataclass(frozen=True)
class PredictiveIntelligenceEvent:
    """Immutable domain event for the Predictive Intelligence lifecycle."""

    event_id:    str
    event_type:  PredictionEventType
    request_id:  str
    actor:       str
    system_id:   str
    payload:     Dict[str, Any]  = field(default_factory=dict)
    occurred_at: float           = field(default_factory=time.time)

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
    event_type: PredictionEventType,
    request_id: str,
    actor:      str,
    payload:    Dict[str, Any],
) -> PredictiveIntelligenceEvent:
    return PredictiveIntelligenceEvent(
        event_id   = str(uuid.uuid4()),
        event_type = event_type,
        request_id = request_id,
        actor      = actor,
        system_id  = ENGINE_SYSTEM_ID,
        payload    = payload,
    )


def make_prediction_started_event(
    request_id: str,
    actor:      str                       = ACTOR_ENGINE,
    payload:    Optional[Dict[str, Any]]  = None,
) -> PredictiveIntelligenceEvent:
    return _make(PredictionEventType.PREDICTION_STARTED, request_id, actor, payload or {})


def make_forecast_generated_event(
    request_id:     str,
    forecast_count: int,
    domain:         str,
    actor:          str = ACTOR_ENGINE,
) -> PredictiveIntelligenceEvent:
    return _make(
        PredictionEventType.FORECAST_GENERATED,
        request_id, actor,
        {"forecast_count": forecast_count, "domain": domain},
    )


def make_trend_forecast_completed_event(
    request_id:  str,
    trend_count: int,
    actor:       str = ACTOR_ENGINE,
) -> PredictiveIntelligenceEvent:
    return _make(
        PredictionEventType.TREND_FORECAST_COMPLETED,
        request_id, actor,
        {"trend_count": trend_count},
    )


def make_risk_forecast_completed_event(
    request_id: str,
    risk_level: str,
    risk_score: float,
    actor:      str = ACTOR_ENGINE,
) -> PredictiveIntelligenceEvent:
    return _make(
        PredictionEventType.RISK_FORECAST_COMPLETED,
        request_id, actor,
        {"risk_level": risk_level, "risk_score": risk_score},
    )


def make_capacity_forecast_completed_event(
    request_id:          str,
    forecasted_util:     float,
    bottleneck_risk:     float,
    actor:               str = ACTOR_ENGINE,
) -> PredictiveIntelligenceEvent:
    return _make(
        PredictionEventType.CAPACITY_FORECAST_COMPLETED,
        request_id, actor,
        {"forecasted_utilization": forecasted_util, "bottleneck_risk": bottleneck_risk},
    )


def make_prediction_published_event(
    request_id: str,
    report_id:  str,
    actor:      str = ACTOR_ENGINE,
) -> PredictiveIntelligenceEvent:
    return _make(
        PredictionEventType.PREDICTION_PUBLISHED,
        request_id, actor,
        {"report_id": report_id},
    )


def make_prediction_failed_event(
    request_id: str,
    error:      str,
    actor:      str = ACTOR_SYSTEM,
) -> PredictiveIntelligenceEvent:
    return _make(
        PredictionEventType.PREDICTION_FAILED,
        request_id, actor,
        {"error": error},
    )
