"""
market_integration_events.py — iios.market.integration
========================================================
Domain event factory for the Market Integration subsystem.

C12 Market Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .constants import INTEGRATION_SYSTEM_ID, IntegrationEventType


@dataclass(frozen=True)
class MarketIntegrationEvent:
    """Immutable domain event for the Market Integration subsystem."""
    event_id:       str
    event_type:     IntegrationEventType
    integration_id: str
    exchange:       str
    actor:          str
    payload:        Dict[str, Any]
    occurred_at:    float
    correlation_id: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":       self.event_id,
            "event_type":     self.event_type.value,
            "integration_id": self.integration_id,
            "exchange":       self.exchange,
            "actor":          self.actor,
            "payload":        self.payload,
            "occurred_at":    self.occurred_at,
            "correlation_id": self.correlation_id,
            "source":         INTEGRATION_SYSTEM_ID,
        }


# ---------------------------------------------------------------------------
# Internal builder
# ---------------------------------------------------------------------------

def _make(
    event_type:     IntegrationEventType,
    integration_id: str,
    exchange:       str,
    actor:          str,
    payload:        Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str]            = None,
) -> MarketIntegrationEvent:
    return MarketIntegrationEvent(
        event_id       = str(uuid.uuid4()),
        event_type     = event_type,
        integration_id = integration_id,
        exchange       = exchange,
        actor          = actor,
        payload        = dict(payload or {}),
        occurred_at    = time.time(),
        correlation_id = correlation_id or str(uuid.uuid4()),
    )


# ---------------------------------------------------------------------------
# Factory functions — one per IntegrationEventType
# ---------------------------------------------------------------------------

def market_integration_started_event(
    integration_id: str, exchange: str, actor: str, **kwargs: Any
) -> MarketIntegrationEvent:
    return _make(IntegrationEventType.MARKET_INTEGRATION_STARTED,
                 integration_id, exchange, actor, kwargs)


def market_request_received_event(
    integration_id: str, exchange: str, actor: str, **kwargs: Any
) -> MarketIntegrationEvent:
    return _make(IntegrationEventType.MARKET_REQUEST_RECEIVED,
                 integration_id, exchange, actor, kwargs)


def market_validated_event(
    integration_id: str, exchange: str, actor: str, **kwargs: Any
) -> MarketIntegrationEvent:
    return _make(IntegrationEventType.MARKET_VALIDATED,
                 integration_id, exchange, actor, kwargs)


def market_snapshot_published_event(
    integration_id: str, exchange: str, actor: str, **kwargs: Any
) -> MarketIntegrationEvent:
    return _make(IntegrationEventType.MARKET_SNAPSHOT_PUBLISHED,
                 integration_id, exchange, actor, kwargs)


def market_completed_event(
    integration_id: str, exchange: str, actor: str, **kwargs: Any
) -> MarketIntegrationEvent:
    return _make(IntegrationEventType.MARKET_COMPLETED,
                 integration_id, exchange, actor, kwargs)


def market_failed_event(
    integration_id: str, exchange: str, actor: str, **kwargs: Any
) -> MarketIntegrationEvent:
    return _make(IntegrationEventType.MARKET_FAILED,
                 integration_id, exchange, actor, kwargs)


def market_integration_stopped_event(
    integration_id: str, exchange: str, actor: str, **kwargs: Any
) -> MarketIntegrationEvent:
    return _make(IntegrationEventType.MARKET_INTEGRATION_STOPPED,
                 integration_id, exchange, actor, kwargs)
