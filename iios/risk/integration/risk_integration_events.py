"""
risk_integration_events.py — iios.risk.integration
====================================================
Domain event value objects for the Risk Integration layer.

C11 Risk Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import IntegrationEventType, VERSION


@dataclass(frozen=True)
class RiskIntegrationEvent:
    """Immutable domain event for the Risk Integration layer."""
    event_id:          str
    event_type:        IntegrationEventType
    engine_id:         str
    portfolio_id:      str
    request_id:        str
    actor:             str
    payload:           Dict[str, Any]
    framework_version: str   = VERSION
    occurred_at:       float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":          self.event_id,
            "event_type":        self.event_type.value,
            "engine_id":         self.engine_id,
            "portfolio_id":      self.portfolio_id,
            "request_id":        self.request_id,
            "actor":             self.actor,
            "payload":           self.payload,
            "framework_version": self.framework_version,
            "occurred_at":       self.occurred_at,
        }


def _make_event(
    event_type:   IntegrationEventType,
    engine_id:    str,
    portfolio_id: str,
    request_id:   str,
    actor:        str,
    payload:      Optional[Dict[str, Any]] = None,
) -> RiskIntegrationEvent:
    return RiskIntegrationEvent(
        event_id     = str(uuid.uuid4()),
        event_type   = event_type,
        engine_id    = engine_id,
        portfolio_id = portfolio_id,
        request_id   = request_id,
        actor        = actor,
        payload      = payload or {},
    )


def make_integration_started(
    engine_id: str, portfolio_id: str, actor: str, **kwargs: Any
) -> RiskIntegrationEvent:
    return _make_event(
        IntegrationEventType.RISK_INTEGRATION_STARTED,
        engine_id, portfolio_id, "", actor, kwargs,
    )


def make_request_received(
    engine_id: str, portfolio_id: str, request_id: str, actor: str, **kwargs: Any
) -> RiskIntegrationEvent:
    return _make_event(
        IntegrationEventType.RISK_REQUEST_RECEIVED,
        engine_id, portfolio_id, request_id, actor, kwargs,
    )


def make_risk_validated(
    engine_id: str, portfolio_id: str, request_id: str, actor: str, **kwargs: Any
) -> RiskIntegrationEvent:
    return _make_event(
        IntegrationEventType.RISK_VALIDATED,
        engine_id, portfolio_id, request_id, actor, kwargs,
    )


def make_snapshot_published(
    engine_id: str, portfolio_id: str, request_id: str, actor: str, **kwargs: Any
) -> RiskIntegrationEvent:
    return _make_event(
        IntegrationEventType.RISK_SNAPSHOT_PUBLISHED,
        engine_id, portfolio_id, request_id, actor, kwargs,
    )


def make_risk_completed(
    engine_id: str, portfolio_id: str, request_id: str, actor: str, **kwargs: Any
) -> RiskIntegrationEvent:
    return _make_event(
        IntegrationEventType.RISK_COMPLETED,
        engine_id, portfolio_id, request_id, actor, kwargs,
    )


def make_risk_failed(
    engine_id: str, portfolio_id: str, request_id: str, actor: str, **kwargs: Any
) -> RiskIntegrationEvent:
    return _make_event(
        IntegrationEventType.RISK_FAILED,
        engine_id, portfolio_id, request_id, actor, kwargs,
    )


def make_integration_stopped(
    engine_id: str, portfolio_id: str, actor: str, **kwargs: Any
) -> RiskIntegrationEvent:
    return _make_event(
        IntegrationEventType.RISK_INTEGRATION_STOPPED,
        engine_id, portfolio_id, "", actor, kwargs,
    )
