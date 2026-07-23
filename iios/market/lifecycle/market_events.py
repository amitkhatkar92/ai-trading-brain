"""
market_events.py — iios.market.lifecycle
==========================================
Event value objects and factory functions for the market lifecycle.

All event objects are immutable frozen dataclasses.

C12 Market Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    LIFECYCLE_SYSTEM_ID,
    VERSION,
    MarketEventType,
    MarketState,
)


# ---------------------------------------------------------------------------
# Core event value object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MarketEvent:
    """
    Immutable market lifecycle event.

    Fields
    ------
    event_id :           Unique identifier for this event.
    event_type :         One of the :class:`MarketEventType` values.
    session_id :         Market session that produced the event.
    market_analysis_id : Market analysis identifier.
    exchange :           Exchange or venue identifier.
    state :              Session state at the time of the event.
    source :             Identifier of the component that emitted the event.
    payload :            Free-form event payload.
    occurred_at :        Wall-clock time of event occurrence.
    framework_version :  Framework version string.
    """
    event_id:            str
    event_type:          MarketEventType
    session_id:          str
    market_analysis_id:  str
    exchange:            str
    state:               MarketState
    source:              str            = LIFECYCLE_SYSTEM_ID
    payload:             Dict[str, Any] = field(default_factory=dict)
    occurred_at:         float          = field(default_factory=time.time)
    framework_version:   str            = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":            self.event_id,
            "event_type":          self.event_type.value,
            "session_id":          self.session_id,
            "market_analysis_id":  self.market_analysis_id,
            "exchange":            self.exchange,
            "state":               self.state.value,
            "source":              self.source,
            "payload":             dict(self.payload),
            "occurred_at":         self.occurred_at,
            "framework_version":   self.framework_version,
        }


# ---------------------------------------------------------------------------
# Internal factory helper
# ---------------------------------------------------------------------------

def _make_event(
    event_type:          MarketEventType,
    session_id:          str,
    market_analysis_id:  str,
    exchange:            str,
    state:               MarketState,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> MarketEvent:
    return MarketEvent(
        event_id           = str(uuid.uuid4()),
        event_type         = event_type,
        session_id         = session_id,
        market_analysis_id = market_analysis_id,
        exchange           = exchange,
        state              = state,
        source             = source,
        payload            = payload or {},
    )


# ---------------------------------------------------------------------------
# Public factory functions — one per event type (11 total)
# ---------------------------------------------------------------------------

def make_market_created(
    session_id:          str,
    market_analysis_id:  str,
    exchange:            str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> MarketEvent:
    """Emitted when a new market session is created (CREATED state)."""
    return _make_event(
        MarketEventType.MARKET_CREATED,
        session_id, market_analysis_id, exchange,
        MarketState.CREATED,
        source=source, payload=payload,
    )


def make_market_initialized(
    session_id:          str,
    market_analysis_id:  str,
    exchange:            str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> MarketEvent:
    """Emitted when a session transitions to INITIALIZING."""
    return _make_event(
        MarketEventType.MARKET_INITIALIZED,
        session_id, market_analysis_id, exchange,
        MarketState.INITIALIZING,
        source=source, payload=payload,
    )


def make_market_collected(
    session_id:          str,
    market_analysis_id:  str,
    exchange:            str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> MarketEvent:
    """Emitted when a session transitions to COLLECTING."""
    return _make_event(
        MarketEventType.MARKET_COLLECTED,
        session_id, market_analysis_id, exchange,
        MarketState.COLLECTING,
        source=source, payload=payload,
    )


def make_market_validated(
    session_id:          str,
    market_analysis_id:  str,
    exchange:            str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> MarketEvent:
    """Emitted when a session transitions to VALIDATING."""
    return _make_event(
        MarketEventType.MARKET_VALIDATED,
        session_id, market_analysis_id, exchange,
        MarketState.VALIDATING,
        source=source, payload=payload,
    )


def make_market_analysis_started(
    session_id:          str,
    market_analysis_id:  str,
    exchange:            str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> MarketEvent:
    """Emitted when a session transitions to ANALYZING."""
    return _make_event(
        MarketEventType.MARKET_ANALYSIS_STARTED,
        session_id, market_analysis_id, exchange,
        MarketState.ANALYZING,
        source=source, payload=payload,
    )


def make_market_monitoring_started(
    session_id:          str,
    market_analysis_id:  str,
    exchange:            str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> MarketEvent:
    """Emitted when a session transitions to MONITORING."""
    return _make_event(
        MarketEventType.MARKET_MONITORING_STARTED,
        session_id, market_analysis_id, exchange,
        MarketState.MONITORING,
        source=source, payload=payload,
    )


def make_market_paused(
    session_id:          str,
    market_analysis_id:  str,
    exchange:            str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> MarketEvent:
    """Emitted when a session transitions to PAUSED."""
    return _make_event(
        MarketEventType.MARKET_PAUSED,
        session_id, market_analysis_id, exchange,
        MarketState.PAUSED,
        source=source, payload=payload,
    )


def make_market_resumed(
    session_id:          str,
    market_analysis_id:  str,
    exchange:            str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> MarketEvent:
    """Emitted when a session transitions to RESUMING."""
    return _make_event(
        MarketEventType.MARKET_RESUMED,
        session_id, market_analysis_id, exchange,
        MarketState.RESUMING,
        source=source, payload=payload,
    )


def make_market_completed(
    session_id:          str,
    market_analysis_id:  str,
    exchange:            str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> MarketEvent:
    """Emitted when a session transitions to COMPLETED."""
    return _make_event(
        MarketEventType.MARKET_COMPLETED,
        session_id, market_analysis_id, exchange,
        MarketState.COMPLETED,
        source=source, payload=payload,
    )


def make_market_failed(
    session_id:          str,
    market_analysis_id:  str,
    exchange:            str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> MarketEvent:
    """Emitted when a session transitions to FAILED."""
    return _make_event(
        MarketEventType.MARKET_FAILED,
        session_id, market_analysis_id, exchange,
        MarketState.FAILED,
        source=source, payload=payload,
    )


def make_market_archived(
    session_id:          str,
    market_analysis_id:  str,
    exchange:            str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> MarketEvent:
    """Emitted when a session transitions to ARCHIVED."""
    return _make_event(
        MarketEventType.MARKET_ARCHIVED,
        session_id, market_analysis_id, exchange,
        MarketState.ARCHIVED,
        source=source, payload=payload,
    )
