"""
portfolio_integration_events.py — iios.portfolio.integration
=============================================================
IntegrationEvent value object and eight factory functions.

C10 Portfolio Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .constants import (
    INTEGRATION_SYSTEM_ID,
    VERSION,
    IntegrationEventType,
)


@dataclass(frozen=True)
class IntegrationEvent:
    """
    Immutable record of a single portfolio integration lifecycle event.
    """
    event_id:          str
    event_type:        str   # IntegrationEventType.value
    portfolio_id:      str
    request_id:        str
    source:            str
    payload:           Dict[str, Any]
    occurred_at:       float
    framework_version: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":         self.event_id,
            "event_type":       self.event_type,
            "portfolio_id":     self.portfolio_id,
            "request_id":       self.request_id,
            "source":           self.source,
            "payload":          dict(self.payload),
            "occurred_at":      self.occurred_at,
            "framework_version": self.framework_version,
        }


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _make_event(
    event_type:   IntegrationEventType,
    portfolio_id: str,
    request_id:   str,
    source:       str,
    payload:      Dict[str, Any],
) -> IntegrationEvent:
    return IntegrationEvent(
        event_id          = str(uuid.uuid4()),
        event_type        = event_type.value,
        portfolio_id      = portfolio_id,
        request_id        = request_id,
        source            = source,
        payload           = dict(payload),
        occurred_at       = time.time(),
        framework_version = VERSION,
    )


# ---------------------------------------------------------------------------
# Eight public factory functions
# ---------------------------------------------------------------------------

def make_portfolio_initialized(
    portfolio_id: str,
    request_id:   str = "",
    *,
    source:  str = INTEGRATION_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> IntegrationEvent:
    """Create a PortfolioInitialized event."""
    return _make_event(
        IntegrationEventType.PORTFOLIO_INITIALIZED,
        portfolio_id, request_id, source, payload or {},
    )


def make_portfolio_started(
    portfolio_id: str,
    request_id:   str = "",
    *,
    source:  str = INTEGRATION_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> IntegrationEvent:
    """Create a PortfolioStarted event."""
    return _make_event(
        IntegrationEventType.PORTFOLIO_STARTED,
        portfolio_id, request_id, source, payload or {},
    )


def make_portfolio_completed(
    portfolio_id: str,
    request_id:   str = "",
    *,
    source:       str = INTEGRATION_SYSTEM_ID,
    service_type: str = "",
    payload:      Optional[Dict[str, Any]] = None,
) -> IntegrationEvent:
    """Create a PortfolioCompleted event."""
    p = dict(payload or {})
    p.setdefault("service_type", service_type)
    return _make_event(
        IntegrationEventType.PORTFOLIO_COMPLETED,
        portfolio_id, request_id, source, p,
    )


def make_portfolio_stopped(
    portfolio_id: str,
    request_id:   str = "",
    *,
    source:  str = INTEGRATION_SYSTEM_ID,
    reason:  str = "",
    payload: Optional[Dict[str, Any]] = None,
) -> IntegrationEvent:
    """Create a PortfolioStopped event."""
    p = dict(payload or {})
    p.setdefault("reason", reason)
    return _make_event(
        IntegrationEventType.PORTFOLIO_STOPPED,
        portfolio_id, request_id, source, p,
    )


def make_portfolio_restarted(
    portfolio_id: str,
    request_id:   str = "",
    *,
    source:  str = INTEGRATION_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> IntegrationEvent:
    """Create a PortfolioRestarted event."""
    return _make_event(
        IntegrationEventType.PORTFOLIO_RESTARTED,
        portfolio_id, request_id, source, payload or {},
    )


def make_portfolio_validated(
    portfolio_id: str,
    request_id:   str = "",
    *,
    source:        str = INTEGRATION_SYSTEM_ID,
    passed_checks: int = 0,
    payload:       Optional[Dict[str, Any]] = None,
) -> IntegrationEvent:
    """Create a PortfolioValidated event."""
    p = dict(payload or {})
    p.setdefault("passed_checks", passed_checks)
    return _make_event(
        IntegrationEventType.PORTFOLIO_VALIDATED,
        portfolio_id, request_id, source, p,
    )


def make_portfolio_health_changed(
    portfolio_id: str,
    request_id:   str = "",
    *,
    source:     str = INTEGRATION_SYSTEM_ID,
    from_health: str = "",
    to_health:   str = "",
    payload:    Optional[Dict[str, Any]] = None,
) -> IntegrationEvent:
    """Create a PortfolioHealthChanged event."""
    p = dict(payload or {})
    p.setdefault("from_health", from_health)
    p.setdefault("to_health", to_health)
    return _make_event(
        IntegrationEventType.PORTFOLIO_HEALTH_CHANGED,
        portfolio_id, request_id, source, p,
    )


def make_snapshot_published(
    portfolio_id: str,
    request_id:   str = "",
    *,
    source:      str = INTEGRATION_SYSTEM_ID,
    snapshot_id: str = "",
    payload:     Optional[Dict[str, Any]] = None,
) -> IntegrationEvent:
    """Create a PortfolioSnapshotPublished event."""
    p = dict(payload or {})
    p.setdefault("snapshot_id", snapshot_id)
    return _make_event(
        IntegrationEventType.PORTFOLIO_SNAPSHOT_PUBLISHED,
        portfolio_id, request_id, source, p,
    )
