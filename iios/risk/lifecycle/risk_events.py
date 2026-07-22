"""
risk_events.py — iios.risk.lifecycle
=======================================
Event value objects and factory functions for the risk lifecycle.

All event objects are immutable frozen dataclasses.

C11 Risk Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    LIFECYCLE_SYSTEM_ID,
    VERSION,
    RiskEventType,
    RiskState,
)


# ---------------------------------------------------------------------------
# Core event value object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RiskEvent:
    """
    Immutable risk lifecycle event.

    Fields
    ------
    event_id :          Unique identifier for this event.
    event_type :        One of the :class:`RiskEventType` values.
    session_id :        Risk session that produced the event.
    risk_id :           Risk assessment identifier.
    portfolio_id :      Portfolio identifier.
    state :             Session state at the time of the event.
    source :            Identifier of the component that emitted the event.
    payload :           Free-form event payload.
    occurred_at :       Wall-clock time of event occurrence.
    framework_version : Framework version string.
    """
    event_id:          str
    event_type:        RiskEventType
    session_id:        str
    risk_id:           str
    portfolio_id:      str
    state:             RiskState
    source:            str            = LIFECYCLE_SYSTEM_ID
    payload:           Dict[str, Any] = field(default_factory=dict)
    occurred_at:       float          = field(default_factory=time.time)
    framework_version: str            = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":          self.event_id,
            "event_type":        self.event_type.value,
            "session_id":        self.session_id,
            "risk_id":           self.risk_id,
            "portfolio_id":      self.portfolio_id,
            "state":             self.state.value,
            "source":            self.source,
            "payload":           dict(self.payload),
            "occurred_at":       self.occurred_at,
            "framework_version": self.framework_version,
        }


# ---------------------------------------------------------------------------
# Internal factory helper
# ---------------------------------------------------------------------------

def _make_event(
    event_type:   RiskEventType,
    session_id:   str,
    risk_id:      str,
    portfolio_id: str,
    state:        RiskState,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> RiskEvent:
    return RiskEvent(
        event_id     = str(uuid.uuid4()),
        event_type   = event_type,
        session_id   = session_id,
        risk_id      = risk_id,
        portfolio_id = portfolio_id,
        state        = state,
        source       = source,
        payload      = payload or {},
    )


# ---------------------------------------------------------------------------
# Public factory functions — one per event type (11 total)
# ---------------------------------------------------------------------------

def make_risk_created(
    session_id:   str,
    risk_id:      str,
    portfolio_id: str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> RiskEvent:
    """Emitted when a new risk session is created (CREATED state)."""
    return _make_event(
        RiskEventType.RISK_CREATED,
        session_id, risk_id, portfolio_id,
        RiskState.CREATED,
        source=source, payload=payload,
    )


def make_risk_initialized(
    session_id:   str,
    risk_id:      str,
    portfolio_id: str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> RiskEvent:
    """Emitted when a session enters INITIALIZING state."""
    return _make_event(
        RiskEventType.RISK_INITIALIZED,
        session_id, risk_id, portfolio_id,
        RiskState.INITIALIZING,
        source=source, payload=payload,
    )


def make_risk_collected(
    session_id:   str,
    risk_id:      str,
    portfolio_id: str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> RiskEvent:
    """Emitted when a session enters COLLECTING state."""
    return _make_event(
        RiskEventType.RISK_COLLECTED,
        session_id, risk_id, portfolio_id,
        RiskState.COLLECTING,
        source=source, payload=payload,
    )


def make_risk_validated(
    session_id:   str,
    risk_id:      str,
    portfolio_id: str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> RiskEvent:
    """Emitted when a session enters VALIDATING state."""
    return _make_event(
        RiskEventType.RISK_VALIDATED,
        session_id, risk_id, portfolio_id,
        RiskState.VALIDATING,
        source=source, payload=payload,
    )


def make_risk_assessment_started(
    session_id:   str,
    risk_id:      str,
    portfolio_id: str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> RiskEvent:
    """Emitted when a session enters ASSESSING state."""
    return _make_event(
        RiskEventType.RISK_ASSESSMENT_STARTED,
        session_id, risk_id, portfolio_id,
        RiskState.ASSESSING,
        source=source, payload=payload,
    )


def make_risk_monitoring_started(
    session_id:   str,
    risk_id:      str,
    portfolio_id: str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> RiskEvent:
    """Emitted when a session enters MONITORING state."""
    return _make_event(
        RiskEventType.RISK_MONITORING_STARTED,
        session_id, risk_id, portfolio_id,
        RiskState.MONITORING,
        source=source, payload=payload,
    )


def make_risk_paused(
    session_id:   str,
    risk_id:      str,
    portfolio_id: str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> RiskEvent:
    """Emitted when a session enters PAUSED state."""
    return _make_event(
        RiskEventType.RISK_PAUSED,
        session_id, risk_id, portfolio_id,
        RiskState.PAUSED,
        source=source, payload=payload,
    )


def make_risk_resumed(
    session_id:   str,
    risk_id:      str,
    portfolio_id: str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> RiskEvent:
    """Emitted when a session enters RESUMING state."""
    return _make_event(
        RiskEventType.RISK_RESUMED,
        session_id, risk_id, portfolio_id,
        RiskState.RESUMING,
        source=source, payload=payload,
    )


def make_risk_completed(
    session_id:   str,
    risk_id:      str,
    portfolio_id: str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> RiskEvent:
    """Emitted when a session enters COMPLETED state."""
    return _make_event(
        RiskEventType.RISK_COMPLETED,
        session_id, risk_id, portfolio_id,
        RiskState.COMPLETED,
        source=source, payload=payload,
    )


def make_risk_failed(
    session_id:   str,
    risk_id:      str,
    portfolio_id: str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> RiskEvent:
    """Emitted when a session enters FAILED state."""
    return _make_event(
        RiskEventType.RISK_FAILED,
        session_id, risk_id, portfolio_id,
        RiskState.FAILED,
        source=source, payload=payload,
    )


def make_risk_archived(
    session_id:   str,
    risk_id:      str,
    portfolio_id: str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> RiskEvent:
    """Emitted when a session enters ARCHIVED state."""
    return _make_event(
        RiskEventType.RISK_ARCHIVED,
        session_id, risk_id, portfolio_id,
        RiskState.ARCHIVED,
        source=source, payload=payload,
    )
