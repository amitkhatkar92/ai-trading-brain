"""
market_events.py — iios.market.engine
========================================
Market engine event value object and nine factory functions.

Events emitted:
  MarketInitialized, MarketStarted, MarketCollected, MarketDispatched,
  MarketAnalysisStarted, MarketPublished, MarketCompleted,
  MarketFailed, MarketStopped

C12 Market Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    VERSION,
    ACTOR_ENGINE,
    ACTOR_SYSTEM,
    EngineState,
    MarketEngineEventType,
)


@dataclass(frozen=True)
class MarketEngineEvent:
    """
    Immutable domain event emitted by the Market Engine.

    Fields
    ------
    event_id :            Unique identifier.
    event_type :          Event classification.
    market_analysis_id :  Market analysis identifier.
    exchange :            Target exchange.
    session_id :          Owning lifecycle session.
    pipeline_id :         Associated pipeline (may be empty).
    engine_state :        Engine state at emission time.
    actor :               Component that emitted the event.
    payload :             Supplementary event data.
    occurred_at :         Wall-clock emission time.
    framework_version :   Framework version string.
    """
    event_id:             str
    event_type:           MarketEngineEventType
    market_analysis_id:   str
    exchange:             str
    session_id:           str
    pipeline_id:          str
    engine_state:         EngineState
    actor:                str
    payload:              Dict[str, Any] = field(default_factory=dict)
    occurred_at:          float          = field(default_factory=time.time)
    framework_version:    str            = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":            self.event_id,
            "event_type":          self.event_type.value,
            "market_analysis_id":  self.market_analysis_id,
            "exchange":            self.exchange,
            "session_id":          self.session_id,
            "pipeline_id":         self.pipeline_id,
            "engine_state":        self.engine_state.value,
            "actor":               self.actor,
            "occurred_at":         self.occurred_at,
            "framework_version":   self.framework_version,
        }


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make(
    event_type:          MarketEngineEventType,
    market_analysis_id:  str,
    exchange:            str,
    session_id:          str,
    engine_state:        EngineState,
    *,
    pipeline_id: str                     = "",
    actor:       str                     = ACTOR_ENGINE,
    payload:     Optional[Dict[str, Any]] = None,
) -> MarketEngineEvent:
    return MarketEngineEvent(
        event_id           = str(uuid.uuid4()),
        event_type         = event_type,
        market_analysis_id = market_analysis_id,
        exchange           = exchange,
        session_id         = session_id,
        pipeline_id        = pipeline_id,
        engine_state       = engine_state,
        actor              = actor,
        payload            = dict(payload or {}),
    )


# ---------------------------------------------------------------------------
# Factory functions — one per event type
# ---------------------------------------------------------------------------

def make_market_engine_initialized(
    market_analysis_id: str,
    exchange:           str,
    session_id:         str,
    *,
    payload: Optional[Dict[str, Any]] = None,
) -> MarketEngineEvent:
    return _make(
        MarketEngineEventType.MARKET_INITIALIZED,
        market_analysis_id, exchange, session_id,
        EngineState.INITIALIZING,
        actor   = ACTOR_SYSTEM,
        payload = payload,
    )


def make_market_engine_started(
    market_analysis_id: str,
    exchange:           str,
    session_id:         str,
    *,
    payload: Optional[Dict[str, Any]] = None,
) -> MarketEngineEvent:
    return _make(
        MarketEngineEventType.MARKET_STARTED,
        market_analysis_id, exchange, session_id,
        EngineState.COLLECTING,
        payload = payload,
    )


def make_market_engine_collected(
    market_analysis_id: str,
    exchange:           str,
    session_id:         str,
    *,
    pipeline_id: str                     = "",
    payload:     Optional[Dict[str, Any]] = None,
) -> MarketEngineEvent:
    return _make(
        MarketEngineEventType.MARKET_COLLECTED,
        market_analysis_id, exchange, session_id,
        EngineState.COLLECTING,
        pipeline_id = pipeline_id,
        payload     = payload,
    )


def make_market_engine_dispatched(
    market_analysis_id: str,
    exchange:           str,
    session_id:         str,
    *,
    pipeline_id: str                     = "",
    payload:     Optional[Dict[str, Any]] = None,
) -> MarketEngineEvent:
    return _make(
        MarketEngineEventType.MARKET_DISPATCHED,
        market_analysis_id, exchange, session_id,
        EngineState.DISPATCHING,
        pipeline_id = pipeline_id,
        payload     = payload,
    )


def make_market_engine_analysis_started(
    market_analysis_id: str,
    exchange:           str,
    session_id:         str,
    *,
    pipeline_id: str                     = "",
    payload:     Optional[Dict[str, Any]] = None,
) -> MarketEngineEvent:
    return _make(
        MarketEngineEventType.MARKET_ANALYSIS_STARTED,
        market_analysis_id, exchange, session_id,
        EngineState.ANALYZING,
        pipeline_id = pipeline_id,
        payload     = payload,
    )


def make_market_engine_published(
    market_analysis_id: str,
    exchange:           str,
    session_id:         str,
    *,
    pipeline_id: str                     = "",
    payload:     Optional[Dict[str, Any]] = None,
) -> MarketEngineEvent:
    return _make(
        MarketEngineEventType.MARKET_PUBLISHED,
        market_analysis_id, exchange, session_id,
        EngineState.PUBLISHING,
        pipeline_id = pipeline_id,
        payload     = payload,
    )


def make_market_engine_completed(
    market_analysis_id: str,
    exchange:           str,
    session_id:         str,
    *,
    pipeline_id: str                     = "",
    payload:     Optional[Dict[str, Any]] = None,
) -> MarketEngineEvent:
    return _make(
        MarketEngineEventType.MARKET_COMPLETED,
        market_analysis_id, exchange, session_id,
        EngineState.COMPLETED,
        pipeline_id = pipeline_id,
        payload     = payload,
    )


def make_market_engine_failed(
    market_analysis_id: str,
    exchange:           str,
    session_id:         str,
    *,
    pipeline_id: str                     = "",
    payload:     Optional[Dict[str, Any]] = None,
) -> MarketEngineEvent:
    return _make(
        MarketEngineEventType.MARKET_FAILED,
        market_analysis_id, exchange, session_id,
        EngineState.FAILED,
        pipeline_id = pipeline_id,
        payload     = payload,
    )


def make_market_engine_stopped(
    market_analysis_id: str,
    exchange:           str,
    *,
    payload: Optional[Dict[str, Any]] = None,
) -> MarketEngineEvent:
    return _make(
        MarketEngineEventType.MARKET_STOPPED,
        market_analysis_id, exchange, "",
        EngineState.STOPPED,
        actor   = ACTOR_SYSTEM,
        payload = payload,
    )
