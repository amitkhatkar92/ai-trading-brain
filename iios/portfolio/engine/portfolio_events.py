"""
portfolio_events.py — iios.portfolio.engine
============================================
Event value objects and factory functions for the Portfolio Engine.

C10 Portfolio Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    ENGINE_SYSTEM_ID,
    VERSION,
    PortfolioEventType,
    PortfolioWorkflowType,
)


@dataclass(frozen=True)
class PortfolioEngineEvent:
    """
    Immutable portfolio engine lifecycle event.

    Fields
    ------
    event_id :          Unique identifier.
    event_type :        One of the :class:`PortfolioEventType` values.
    portfolio_id :      Portfolio identifier.
    session_id :        Portfolio session that produced the event.
    workflow_type :     Workflow associated with this event.
    source :            Identifier of the emitting component.
    payload :           Free-form event payload.
    occurred_at :       Wall-clock time.
    framework_version : Framework version string.
    """
    event_id:          str
    event_type:        PortfolioEventType
    portfolio_id:      str
    session_id:        str             = ""
    workflow_type:     Optional[PortfolioWorkflowType] = None
    source:            str             = ENGINE_SYSTEM_ID
    payload:           Dict[str, Any]  = field(default_factory=dict)
    occurred_at:       float           = field(default_factory=time.time)
    framework_version: str             = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":          self.event_id,
            "event_type":        self.event_type.value,
            "portfolio_id":      self.portfolio_id,
            "session_id":        self.session_id,
            "workflow_type":     self.workflow_type.value if self.workflow_type else None,
            "source":            self.source,
            "payload":           dict(self.payload),
            "occurred_at":       self.occurred_at,
            "framework_version": self.framework_version,
        }


# ---------------------------------------------------------------------------
# Internal factory helper
# ---------------------------------------------------------------------------

def _make_event(
    event_type:    PortfolioEventType,
    portfolio_id:  str,
    *,
    session_id:    str                          = "",
    workflow_type: Optional[PortfolioWorkflowType] = None,
    source:        str                          = ENGINE_SYSTEM_ID,
    payload:       Optional[Dict[str, Any]]     = None,
) -> PortfolioEngineEvent:
    return PortfolioEngineEvent(
        event_id      = str(uuid.uuid4()),
        event_type    = event_type,
        portfolio_id  = portfolio_id,
        session_id    = session_id,
        workflow_type = workflow_type,
        source        = source,
        payload       = payload or {},
    )


# ---------------------------------------------------------------------------
# Public factory functions — one per event type
# ---------------------------------------------------------------------------

def make_portfolio_initialized(
    portfolio_id: str,
    *,
    session_id:    str                          = "",
    workflow_type: Optional[PortfolioWorkflowType] = None,
    payload:       Optional[Dict[str, Any]]     = None,
) -> PortfolioEngineEvent:
    return _make_event(
        PortfolioEventType.PORTFOLIO_INITIALIZED, portfolio_id,
        session_id=session_id, workflow_type=workflow_type, payload=payload,
    )


def make_portfolio_started(
    portfolio_id: str,
    *,
    session_id:    str                          = "",
    workflow_type: Optional[PortfolioWorkflowType] = None,
    payload:       Optional[Dict[str, Any]]     = None,
) -> PortfolioEngineEvent:
    return _make_event(
        PortfolioEventType.PORTFOLIO_STARTED, portfolio_id,
        session_id=session_id, workflow_type=workflow_type, payload=payload,
    )


def make_portfolio_collected(
    portfolio_id: str,
    *,
    session_id:    str                          = "",
    workflow_type: Optional[PortfolioWorkflowType] = None,
    input_keys:    Optional[list]               = None,
    payload:       Optional[Dict[str, Any]]     = None,
) -> PortfolioEngineEvent:
    p = dict(payload or {})
    if input_keys:
        p["input_keys"] = input_keys
    return _make_event(
        PortfolioEventType.PORTFOLIO_COLLECTED, portfolio_id,
        session_id=session_id, workflow_type=workflow_type, payload=p,
    )


def make_portfolio_dispatched(
    portfolio_id: str,
    *,
    session_id:    str                          = "",
    workflow_type: Optional[PortfolioWorkflowType] = None,
    payload:       Optional[Dict[str, Any]]     = None,
) -> PortfolioEngineEvent:
    return _make_event(
        PortfolioEventType.PORTFOLIO_DISPATCHED, portfolio_id,
        session_id=session_id, workflow_type=workflow_type, payload=payload,
    )


def make_portfolio_published(
    portfolio_id: str,
    *,
    session_id:    str                          = "",
    workflow_type: Optional[PortfolioWorkflowType] = None,
    snapshot_id:   str                          = "",
    payload:       Optional[Dict[str, Any]]     = None,
) -> PortfolioEngineEvent:
    p = dict(payload or {})
    if snapshot_id:
        p["snapshot_id"] = snapshot_id
    return _make_event(
        PortfolioEventType.PORTFOLIO_PUBLISHED, portfolio_id,
        session_id=session_id, workflow_type=workflow_type, payload=p,
    )


def make_portfolio_completed(
    portfolio_id: str,
    *,
    session_id:    str                          = "",
    workflow_type: Optional[PortfolioWorkflowType] = None,
    elapsed_s:     float                        = 0.0,
    payload:       Optional[Dict[str, Any]]     = None,
) -> PortfolioEngineEvent:
    p = dict(payload or {})
    if elapsed_s:
        p["elapsed_s"] = elapsed_s
    return _make_event(
        PortfolioEventType.PORTFOLIO_COMPLETED, portfolio_id,
        session_id=session_id, workflow_type=workflow_type, payload=p,
    )


def make_portfolio_failed(
    portfolio_id: str,
    *,
    session_id:    str                          = "",
    workflow_type: Optional[PortfolioWorkflowType] = None,
    reason:        str                          = "",
    payload:       Optional[Dict[str, Any]]     = None,
) -> PortfolioEngineEvent:
    p = dict(payload or {})
    if reason:
        p["reason"] = reason
    return _make_event(
        PortfolioEventType.PORTFOLIO_FAILED, portfolio_id,
        session_id=session_id, workflow_type=workflow_type, payload=p,
    )


def make_portfolio_stopped(
    portfolio_id: str,
    *,
    session_id:    str                          = "",
    workflow_type: Optional[PortfolioWorkflowType] = None,
    payload:       Optional[Dict[str, Any]]     = None,
) -> PortfolioEngineEvent:
    return _make_event(
        PortfolioEventType.PORTFOLIO_STOPPED, portfolio_id,
        session_id=session_id, workflow_type=workflow_type, payload=payload,
    )
