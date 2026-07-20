"""
analytics_integration_events.py — iios.execution.analytics.integration
=======================================================================
Event value objects and factory functions for the eight integration
lifecycle events.

All event objects are immutable frozen dataclasses.  Events are dispatched
internally via the integration manager and stored in
:class:`~.analytics_integration_history.AnalyticsIntegrationHistory`.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    INTEGRATION_SYSTEM_ID,
    INTEGRATION_VERSION,
    IntegrationEventType,
)


# ---------------------------------------------------------------------------
# Core event value object
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AnalyticsIntegrationEvent:
    """
    Immutable integration lifecycle event.

    Fields
    ------
    event_id :          Unique identifier for this event.
    event_type :        One of the eight :class:`IntegrationEventType` values.
    source :            Identifier of the component that emitted the event.
    request_id :        Related request identifier, empty string if none.
    session_id :        Related analytics session identifier, empty if none.
    payload :           Free-form payload dictionary.
    occurred_at :       Unix timestamp of event occurrence.
    framework_version : Framework version string.
    """

    event_id:          str
    event_type:        IntegrationEventType
    source:            str
    request_id:        str = ""
    session_id:        str = ""
    payload:           Dict[str, Any] = field(default_factory=dict)
    occurred_at:       float = field(default_factory=time.time)
    framework_version: str = INTEGRATION_VERSION


# ---------------------------------------------------------------------------
# Factory helpers — one per event type
# ---------------------------------------------------------------------------
def _make_event(
    event_type: IntegrationEventType,
    *,
    source: str = INTEGRATION_SYSTEM_ID,
    request_id: str = "",
    session_id: str = "",
    payload: Optional[Dict[str, Any]] = None,
) -> AnalyticsIntegrationEvent:
    return AnalyticsIntegrationEvent(
        event_id   = str(uuid.uuid4()),
        event_type = event_type,
        source     = source,
        request_id = request_id,
        session_id = session_id,
        payload    = payload or {},
    )


def make_analytics_initialized(
    *,
    source: str = INTEGRATION_SYSTEM_ID,
    metadata: Optional[Dict[str, Any]] = None,
) -> AnalyticsIntegrationEvent:
    """Create an ANALYTICS_INITIALIZED event (subsystem set-up complete)."""
    return _make_event(
        IntegrationEventType.ANALYTICS_INITIALIZED,
        source=source,
        payload=metadata or {},
    )


def make_analytics_started(
    *,
    source: str = INTEGRATION_SYSTEM_ID,
    metadata: Optional[Dict[str, Any]] = None,
) -> AnalyticsIntegrationEvent:
    """Create an ANALYTICS_STARTED event (subsystem entered running state)."""
    return _make_event(
        IntegrationEventType.ANALYTICS_STARTED,
        source=source,
        payload=metadata or {},
    )


def make_analytics_completed(
    *,
    request_id: str,
    session_id: str = "",
    source: str = INTEGRATION_SYSTEM_ID,
    processing_ms: float = 0.0,
    status: str = "success",
    metadata: Optional[Dict[str, Any]] = None,
) -> AnalyticsIntegrationEvent:
    """Create an ANALYTICS_COMPLETED event for a finished analytics request."""
    payload: Dict[str, Any] = {
        "processing_ms": processing_ms,
        "status":        status,
    }
    if metadata:
        payload.update(metadata)
    return _make_event(
        IntegrationEventType.ANALYTICS_COMPLETED,
        source=source,
        request_id=request_id,
        session_id=session_id,
        payload=payload,
    )


def make_analytics_stopped(
    *,
    source: str = INTEGRATION_SYSTEM_ID,
    reason: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> AnalyticsIntegrationEvent:
    """Create an ANALYTICS_STOPPED event (subsystem shut down)."""
    payload: Dict[str, Any] = {"reason": reason}
    if metadata:
        payload.update(metadata)
    return _make_event(
        IntegrationEventType.ANALYTICS_STOPPED,
        source=source,
        payload=payload,
    )


def make_analytics_restarted(
    *,
    source: str = INTEGRATION_SYSTEM_ID,
    metadata: Optional[Dict[str, Any]] = None,
) -> AnalyticsIntegrationEvent:
    """Create an ANALYTICS_RESTARTED event."""
    return _make_event(
        IntegrationEventType.ANALYTICS_RESTARTED,
        source=source,
        payload=metadata or {},
    )


def make_analytics_validated(
    *,
    request_id: str = "",
    source: str = INTEGRATION_SYSTEM_ID,
    passed: bool = True,
    failed_checks: tuple[str, ...] = (),
    metadata: Optional[Dict[str, Any]] = None,
) -> AnalyticsIntegrationEvent:
    """Create an ANALYTICS_VALIDATED event after a validation run."""
    payload: Dict[str, Any] = {
        "passed":        passed,
        "failed_checks": list(failed_checks),
    }
    if metadata:
        payload.update(metadata)
    return _make_event(
        IntegrationEventType.ANALYTICS_VALIDATED,
        source=source,
        request_id=request_id,
        payload=payload,
    )


def make_analytics_health_changed(
    *,
    source: str = INTEGRATION_SYSTEM_ID,
    previous_health: str = "",
    current_health: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> AnalyticsIntegrationEvent:
    """Create an ANALYTICS_HEALTH_CHANGED event."""
    payload: Dict[str, Any] = {
        "previous_health": previous_health,
        "current_health":  current_health,
    }
    if metadata:
        payload.update(metadata)
    return _make_event(
        IntegrationEventType.ANALYTICS_HEALTH_CHANGED,
        source=source,
        payload=payload,
    )


def make_analytics_snapshot_published(
    *,
    request_id: str,
    session_id: str = "",
    snapshot_id: str = "",
    source: str = INTEGRATION_SYSTEM_ID,
    metadata: Optional[Dict[str, Any]] = None,
) -> AnalyticsIntegrationEvent:
    """Create an ANALYTICS_SNAPSHOT_PUBLISHED event."""
    payload: Dict[str, Any] = {"snapshot_id": snapshot_id}
    if metadata:
        payload.update(metadata)
    return _make_event(
        IntegrationEventType.ANALYTICS_SNAPSHOT_PUBLISHED,
        source=source,
        request_id=request_id,
        session_id=session_id,
        payload=payload,
    )
