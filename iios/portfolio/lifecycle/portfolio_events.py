"""
portfolio_events.py — iios.portfolio.lifecycle
================================================
Event value objects and factory functions for the portfolio lifecycle.

All event objects are immutable frozen dataclasses.

C10 Portfolio Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    LIFECYCLE_SYSTEM_ID,
    VERSION,
    PortfolioEventType,
    PortfolioState,
)


# ---------------------------------------------------------------------------
# Core event value object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PortfolioEvent:
    """
    Immutable portfolio lifecycle event.

    Fields
    ------
    event_id :          Unique identifier for this event.
    event_type :        One of the :class:`PortfolioEventType` values.
    session_id :        Portfolio session that produced the event.
    portfolio_id :      Portfolio identifier.
    state :             Session state at the time of the event.
    source :            Identifier of the component that emitted the event.
    payload :           Free-form event payload.
    occurred_at :       Wall-clock time of event occurrence.
    framework_version : Framework version string.
    """
    event_id:          str
    event_type:        PortfolioEventType
    session_id:        str
    portfolio_id:      str
    state:             PortfolioState
    source:            str            = LIFECYCLE_SYSTEM_ID
    payload:           Dict[str, Any] = field(default_factory=dict)
    occurred_at:       float          = field(default_factory=time.time)
    framework_version: str            = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":          self.event_id,
            "event_type":        self.event_type.value,
            "session_id":        self.session_id,
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
    event_type:   PortfolioEventType,
    session_id:   str,
    portfolio_id: str,
    state:        PortfolioState,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> PortfolioEvent:
    return PortfolioEvent(
        event_id     = str(uuid.uuid4()),
        event_type   = event_type,
        session_id   = session_id,
        portfolio_id = portfolio_id,
        state        = state,
        source       = source,
        payload      = payload or {},
    )


# ---------------------------------------------------------------------------
# Public factory functions — one per event type
# ---------------------------------------------------------------------------

def make_portfolio_created(
    session_id:   str,
    portfolio_id: str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> PortfolioEvent:
    """Emitted when a new portfolio session is created (CREATED state)."""
    return _make_event(
        PortfolioEventType.PORTFOLIO_CREATED,
        session_id, portfolio_id,
        PortfolioState.CREATED,
        source=source, payload=payload,
    )


def make_portfolio_initialized(
    session_id:   str,
    portfolio_id: str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> PortfolioEvent:
    """Emitted when a session enters INITIALIZING state."""
    return _make_event(
        PortfolioEventType.PORTFOLIO_INITIALIZED,
        session_id, portfolio_id,
        PortfolioState.INITIALIZING,
        source=source, payload=payload,
    )


def make_portfolio_loaded(
    session_id:   str,
    portfolio_id: str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> PortfolioEvent:
    """Emitted when a session enters LOADING state."""
    return _make_event(
        PortfolioEventType.PORTFOLIO_LOADED,
        session_id, portfolio_id,
        PortfolioState.LOADING,
        source=source, payload=payload,
    )


def make_portfolio_validated(
    session_id:   str,
    portfolio_id: str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> PortfolioEvent:
    """Emitted when a session enters VALIDATING state."""
    return _make_event(
        PortfolioEventType.PORTFOLIO_VALIDATED,
        session_id, portfolio_id,
        PortfolioState.VALIDATING,
        source=source, payload=payload,
    )


def make_portfolio_activated(
    session_id:   str,
    portfolio_id: str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> PortfolioEvent:
    """Emitted when a session enters ACTIVE state."""
    return _make_event(
        PortfolioEventType.PORTFOLIO_ACTIVATED,
        session_id, portfolio_id,
        PortfolioState.ACTIVE,
        source=source, payload=payload,
    )


def make_portfolio_paused(
    session_id:   str,
    portfolio_id: str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> PortfolioEvent:
    """Emitted when a session enters PAUSED state."""
    return _make_event(
        PortfolioEventType.PORTFOLIO_PAUSED,
        session_id, portfolio_id,
        PortfolioState.PAUSED,
        source=source, payload=payload,
    )


def make_portfolio_resumed(
    session_id:   str,
    portfolio_id: str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> PortfolioEvent:
    """Emitted when a session enters RESUMING state."""
    return _make_event(
        PortfolioEventType.PORTFOLIO_RESUMED,
        session_id, portfolio_id,
        PortfolioState.RESUMING,
        source=source, payload=payload,
    )


def make_portfolio_rebalancing(
    session_id:   str,
    portfolio_id: str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> PortfolioEvent:
    """Emitted when a session enters REBALANCING state."""
    return _make_event(
        PortfolioEventType.PORTFOLIO_REBALANCING,
        session_id, portfolio_id,
        PortfolioState.REBALANCING,
        source=source, payload=payload,
    )


def make_portfolio_completed(
    session_id:   str,
    portfolio_id: str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> PortfolioEvent:
    """Emitted when a session enters COMPLETED state."""
    return _make_event(
        PortfolioEventType.PORTFOLIO_COMPLETED,
        session_id, portfolio_id,
        PortfolioState.COMPLETED,
        source=source, payload=payload,
    )


def make_portfolio_failed(
    session_id:   str,
    portfolio_id: str,
    *,
    reason:  str = "",
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> PortfolioEvent:
    """Emitted when a session enters FAILED state."""
    return _make_event(
        PortfolioEventType.PORTFOLIO_FAILED,
        session_id, portfolio_id,
        PortfolioState.FAILED,
        source=source,
        payload=dict(payload or {}, reason=reason),
    )


def make_portfolio_archived(
    session_id:   str,
    portfolio_id: str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> PortfolioEvent:
    """Emitted when a session enters ARCHIVED state."""
    return _make_event(
        PortfolioEventType.PORTFOLIO_ARCHIVED,
        session_id, portfolio_id,
        PortfolioState.ARCHIVED,
        source=source, payload=payload,
    )
