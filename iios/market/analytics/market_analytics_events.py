"""
market_analytics_events.py — iios.market.analytics
====================================================
Domain event factories for the Market Analytics Framework.

C12 Market Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import ANALYTICS_SYSTEM_ID, AnalyticsEventType


@dataclass(frozen=True)
class MarketAnalyticsEvent:
    """Immutable domain event for market analytics lifecycle transitions."""
    event_id:         str
    event_type:       AnalyticsEventType
    analytics_id:     str
    market_analysis_id: str
    exchange:         str
    actor:            str
    payload:          Dict[str, Any]
    occurred_at:      float
    correlation_id:   str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":           self.event_id,
            "event_type":         self.event_type.value,
            "analytics_id":       self.analytics_id,
            "market_analysis_id": self.market_analysis_id,
            "exchange":           self.exchange,
            "actor":              self.actor,
            "payload":            self.payload,
            "occurred_at":        self.occurred_at,
            "correlation_id":     self.correlation_id,
            "source":             ANALYTICS_SYSTEM_ID,
        }


def _make(
    event_type:         AnalyticsEventType,
    analytics_id:       str,
    market_analysis_id: str,
    exchange:           str,
    actor:              str,
    payload:            Optional[Dict[str, Any]] = None,
    correlation_id:     Optional[str]            = None,
) -> MarketAnalyticsEvent:
    return MarketAnalyticsEvent(
        event_id           = str(uuid.uuid4()),
        event_type         = event_type,
        analytics_id       = analytics_id,
        market_analysis_id = market_analysis_id,
        exchange           = exchange,
        actor              = actor,
        payload            = dict(payload or {}),
        occurred_at        = time.time(),
        correlation_id     = correlation_id or str(uuid.uuid4()),
    )


# ---------------------------------------------------------------------------
# Factory functions — one per AnalyticsEventType
# ---------------------------------------------------------------------------

def analytics_started_event(
    analytics_id:       str,
    market_analysis_id: str,
    exchange:           str,
    actor:              str,
    **kwargs: Any,
) -> MarketAnalyticsEvent:
    return _make(
        AnalyticsEventType.ANALYTICS_STARTED,
        analytics_id, market_analysis_id, exchange, actor,
        payload=kwargs,
    )


def datasets_loaded_event(
    analytics_id:       str,
    market_analysis_id: str,
    exchange:           str,
    actor:              str,
    **kwargs: Any,
) -> MarketAnalyticsEvent:
    return _make(
        AnalyticsEventType.DATASETS_LOADED,
        analytics_id, market_analysis_id, exchange, actor,
        payload=kwargs,
    )


def regime_detected_event(
    analytics_id:       str,
    market_analysis_id: str,
    exchange:           str,
    actor:              str,
    **kwargs: Any,
) -> MarketAnalyticsEvent:
    return _make(
        AnalyticsEventType.REGIME_DETECTED,
        analytics_id, market_analysis_id, exchange, actor,
        payload=kwargs,
    )


def sector_analysis_completed_event(
    analytics_id:       str,
    market_analysis_id: str,
    exchange:           str,
    actor:              str,
    **kwargs: Any,
) -> MarketAnalyticsEvent:
    return _make(
        AnalyticsEventType.SECTOR_ANALYSIS_COMPLETED,
        analytics_id, market_analysis_id, exchange, actor,
        payload=kwargs,
    )


def breadth_analysis_completed_event(
    analytics_id:       str,
    market_analysis_id: str,
    exchange:           str,
    actor:              str,
    **kwargs: Any,
) -> MarketAnalyticsEvent:
    return _make(
        AnalyticsEventType.BREADTH_ANALYSIS_COMPLETED,
        analytics_id, market_analysis_id, exchange, actor,
        payload=kwargs,
    )


def forecast_generated_event(
    analytics_id:       str,
    market_analysis_id: str,
    exchange:           str,
    actor:              str,
    **kwargs: Any,
) -> MarketAnalyticsEvent:
    return _make(
        AnalyticsEventType.FORECAST_GENERATED,
        analytics_id, market_analysis_id, exchange, actor,
        payload=kwargs,
    )


def scores_calculated_event(
    analytics_id:       str,
    market_analysis_id: str,
    exchange:           str,
    actor:              str,
    **kwargs: Any,
) -> MarketAnalyticsEvent:
    return _make(
        AnalyticsEventType.SCORES_CALCULATED,
        analytics_id, market_analysis_id, exchange, actor,
        payload=kwargs,
    )


def analytics_validated_event(
    analytics_id:       str,
    market_analysis_id: str,
    exchange:           str,
    actor:              str,
    **kwargs: Any,
) -> MarketAnalyticsEvent:
    return _make(
        AnalyticsEventType.ANALYTICS_VALIDATED,
        analytics_id, market_analysis_id, exchange, actor,
        payload=kwargs,
    )


def analytics_published_event(
    analytics_id:       str,
    market_analysis_id: str,
    exchange:           str,
    actor:              str,
    **kwargs: Any,
) -> MarketAnalyticsEvent:
    return _make(
        AnalyticsEventType.ANALYTICS_PUBLISHED,
        analytics_id, market_analysis_id, exchange, actor,
        payload=kwargs,
    )


def analytics_failed_event(
    analytics_id:       str,
    market_analysis_id: str,
    exchange:           str,
    actor:              str,
    **kwargs: Any,
) -> MarketAnalyticsEvent:
    return _make(
        AnalyticsEventType.ANALYTICS_FAILED,
        analytics_id, market_analysis_id, exchange, actor,
        payload=kwargs,
    )
