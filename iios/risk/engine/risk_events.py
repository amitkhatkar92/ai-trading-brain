"""
risk_events.py — iios.risk.engine
====================================
Risk engine event value object and nine factory functions.

C11 Risk Intelligence — Phase 1, Module 2
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
    RiskEngineEventType,
)


@dataclass(frozen=True)
class RiskEngineEvent:
    """
    Immutable domain event emitted by the Risk Engine.

    Fields
    ------
    event_id :          Unique identifier.
    event_type :        Event classification.
    risk_id :           Risk assessment identifier.
    portfolio_id :      Portfolio identifier.
    session_id :        Owning lifecycle session.
    pipeline_id :       Associated pipeline (may be empty).
    engine_state :      Engine state at emission time.
    actor :             Component that emitted the event.
    payload :           Supplementary event data.
    occurred_at :       Wall-clock emission time.
    framework_version : Framework version string.
    """
    event_id:          str
    event_type:        RiskEngineEventType
    risk_id:           str
    portfolio_id:      str
    session_id:        str
    pipeline_id:       str
    engine_state:      EngineState
    actor:             str
    payload:           Dict[str, Any]  = field(default_factory=dict)
    occurred_at:       float           = field(default_factory=time.time)
    framework_version: str             = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":          self.event_id,
            "event_type":        self.event_type.value,
            "risk_id":           self.risk_id,
            "portfolio_id":      self.portfolio_id,
            "session_id":        self.session_id,
            "pipeline_id":       self.pipeline_id,
            "engine_state":      self.engine_state.value,
            "actor":             self.actor,
            "occurred_at":       self.occurred_at,
            "framework_version": self.framework_version,
        }


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make(
    event_type:   RiskEngineEventType,
    risk_id:      str,
    portfolio_id: str,
    session_id:   str,
    engine_state: EngineState,
    *,
    pipeline_id: str                    = "",
    actor:       str                    = ACTOR_ENGINE,
    payload:     Optional[Dict[str, Any]] = None,
) -> RiskEngineEvent:
    return RiskEngineEvent(
        event_id      = str(uuid.uuid4()),
        event_type    = event_type,
        risk_id       = risk_id,
        portfolio_id  = portfolio_id,
        session_id    = session_id,
        pipeline_id   = pipeline_id,
        engine_state  = engine_state,
        actor         = actor,
        payload       = dict(payload or {}),
    )


# ---------------------------------------------------------------------------
# Factory functions — one per event type
# ---------------------------------------------------------------------------

def make_risk_initialized(
    risk_id:      str,
    portfolio_id: str,
    session_id:   str,
    *,
    payload: Optional[Dict[str, Any]] = None,
) -> RiskEngineEvent:
    return _make(
        RiskEngineEventType.RISK_INITIALIZED,
        risk_id, portfolio_id, session_id,
        EngineState.INITIALIZING,
        actor   = ACTOR_SYSTEM,
        payload = payload,
    )


def make_risk_started(
    risk_id:      str,
    portfolio_id: str,
    session_id:   str,
    *,
    payload: Optional[Dict[str, Any]] = None,
) -> RiskEngineEvent:
    return _make(
        RiskEngineEventType.RISK_STARTED,
        risk_id, portfolio_id, session_id,
        EngineState.COLLECTING,
        payload = payload,
    )


def make_risk_collected(
    risk_id:      str,
    portfolio_id: str,
    session_id:   str,
    *,
    pipeline_id: str                    = "",
    payload:     Optional[Dict[str, Any]] = None,
) -> RiskEngineEvent:
    return _make(
        RiskEngineEventType.RISK_COLLECTED,
        risk_id, portfolio_id, session_id,
        EngineState.COLLECTING,
        pipeline_id = pipeline_id,
        payload     = payload,
    )


def make_risk_dispatched(
    risk_id:      str,
    portfolio_id: str,
    session_id:   str,
    *,
    pipeline_id: str                    = "",
    payload:     Optional[Dict[str, Any]] = None,
) -> RiskEngineEvent:
    return _make(
        RiskEngineEventType.RISK_DISPATCHED,
        risk_id, portfolio_id, session_id,
        EngineState.DISPATCHING,
        pipeline_id = pipeline_id,
        payload     = payload,
    )


def make_risk_assessment_started(
    risk_id:      str,
    portfolio_id: str,
    session_id:   str,
    *,
    pipeline_id: str                    = "",
    payload:     Optional[Dict[str, Any]] = None,
) -> RiskEngineEvent:
    return _make(
        RiskEngineEventType.RISK_ASSESSMENT_STARTED,
        risk_id, portfolio_id, session_id,
        EngineState.ASSESSING,
        pipeline_id = pipeline_id,
        payload     = payload,
    )


def make_risk_published(
    risk_id:      str,
    portfolio_id: str,
    session_id:   str,
    *,
    pipeline_id: str                    = "",
    payload:     Optional[Dict[str, Any]] = None,
) -> RiskEngineEvent:
    return _make(
        RiskEngineEventType.RISK_PUBLISHED,
        risk_id, portfolio_id, session_id,
        EngineState.PUBLISHING,
        pipeline_id = pipeline_id,
        payload     = payload,
    )


def make_risk_completed(
    risk_id:      str,
    portfolio_id: str,
    session_id:   str,
    *,
    pipeline_id: str                    = "",
    payload:     Optional[Dict[str, Any]] = None,
) -> RiskEngineEvent:
    return _make(
        RiskEngineEventType.RISK_COMPLETED,
        risk_id, portfolio_id, session_id,
        EngineState.COMPLETED,
        pipeline_id = pipeline_id,
        payload     = payload,
    )


def make_risk_failed(
    risk_id:      str,
    portfolio_id: str,
    session_id:   str,
    *,
    pipeline_id: str                    = "",
    payload:     Optional[Dict[str, Any]] = None,
) -> RiskEngineEvent:
    return _make(
        RiskEngineEventType.RISK_FAILED,
        risk_id, portfolio_id, session_id,
        EngineState.FAILED,
        pipeline_id = pipeline_id,
        payload     = payload,
    )


def make_risk_stopped(
    risk_id:      str,
    portfolio_id: str,
    session_id:   str    = "",
    *,
    payload: Optional[Dict[str, Any]] = None,
) -> RiskEngineEvent:
    return _make(
        RiskEngineEventType.RISK_STOPPED,
        risk_id, portfolio_id, session_id,
        EngineState.STOPPED,
        actor   = ACTOR_SYSTEM,
        payload = payload,
    )
