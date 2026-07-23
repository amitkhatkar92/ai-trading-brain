"""
market_policy_events.py — iios.market.policies
================================================
Domain event value object and 8 factory functions for the Market Policy Framework.

C12 Market Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import VERSION, PolicyAction, PolicyEventType


# ---------------------------------------------------------------------------
# Event value object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MarketPolicyEvent:
    """
    Immutable domain event for the Market Policy Framework.

    Fields
    ------
    event_id :            Unique event identifier.
    event_type :          Classification of the event.
    evaluation_id :       Market workflow evaluation correlation identifier.
    request_id :          Policy evaluation request identifier.
    market_analysis_id :  Market analysis identifier.
    exchange :            Exchange identifier.
    policy_id :           Policy identifier (empty for evaluation-level events).
    final_action :        Governance outcome at the time of the event.
    actor :               Identifier of the component that emitted the event.
    payload :             Supplementary event payload.
    occurred_at :         Wall-clock time the event occurred.
    framework_version :   Framework version string.
    """
    event_id:            str
    event_type:          PolicyEventType
    evaluation_id:       str
    request_id:          str
    market_analysis_id:  str              = ""
    exchange:            str              = ""
    policy_id:           str              = ""
    final_action:        Optional[PolicyAction] = None
    actor:               str              = ""
    payload:             Dict[str, Any]   = field(default_factory=dict)
    occurred_at:         float            = field(default_factory=time.time)
    framework_version:   str              = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":           self.event_id,
            "event_type":         self.event_type.value,
            "evaluation_id":      self.evaluation_id,
            "request_id":         self.request_id,
            "market_analysis_id": self.market_analysis_id,
            "exchange":           self.exchange,
            "policy_id":          self.policy_id,
            "final_action":       self.final_action.value if self.final_action else None,
            "actor":              self.actor,
            "occurred_at":        self.occurred_at,
            "framework_version":  self.framework_version,
        }


# ---------------------------------------------------------------------------
# Internal factory helper
# ---------------------------------------------------------------------------

def _make(
    event_type:          PolicyEventType,
    evaluation_id:       str,
    request_id:          str,
    *,
    market_analysis_id:  str                     = "",
    exchange:            str                     = "",
    policy_id:           str                     = "",
    final_action:        Optional[PolicyAction]  = None,
    actor:               str                     = "",
    payload:             Optional[Dict[str, Any]] = None,
) -> MarketPolicyEvent:
    return MarketPolicyEvent(
        event_id           = str(uuid.uuid4()),
        event_type         = event_type,
        evaluation_id      = evaluation_id,
        request_id         = request_id,
        market_analysis_id = market_analysis_id,
        exchange           = exchange,
        policy_id          = policy_id,
        final_action       = final_action,
        actor              = actor,
        payload            = dict(payload or {}),
    )


# ---------------------------------------------------------------------------
# 8 public factory functions
# ---------------------------------------------------------------------------

def make_market_policy_evaluation_started(
    evaluation_id:      str,
    request_id:         str,
    *,
    market_analysis_id: str                     = "",
    exchange:           str                     = "",
    actor:              str                     = "",
    payload:            Optional[Dict[str, Any]] = None,
) -> MarketPolicyEvent:
    return _make(
        PolicyEventType.EVALUATION_STARTED,
        evaluation_id, request_id,
        market_analysis_id=market_analysis_id,
        exchange=exchange,
        actor=actor, payload=payload,
    )


def make_market_policy_loaded(
    evaluation_id:      str,
    request_id:         str,
    policy_id:          str,
    *,
    market_analysis_id: str                     = "",
    exchange:           str                     = "",
    actor:              str                     = "",
    payload:            Optional[Dict[str, Any]] = None,
) -> MarketPolicyEvent:
    return _make(
        PolicyEventType.POLICY_LOADED,
        evaluation_id, request_id,
        market_analysis_id=market_analysis_id,
        exchange=exchange,
        policy_id=policy_id, actor=actor, payload=payload,
    )


def make_market_policy_validated(
    evaluation_id:      str,
    request_id:         str,
    policy_id:          str,
    *,
    market_analysis_id: str                     = "",
    exchange:           str                     = "",
    actor:              str                     = "",
    payload:            Optional[Dict[str, Any]] = None,
) -> MarketPolicyEvent:
    return _make(
        PolicyEventType.POLICY_VALIDATED,
        evaluation_id, request_id,
        market_analysis_id=market_analysis_id,
        exchange=exchange,
        policy_id=policy_id, actor=actor, payload=payload,
    )


def make_market_policy_approved(
    evaluation_id:      str,
    request_id:         str,
    policy_id:          str,
    final_action:       PolicyAction,
    *,
    market_analysis_id: str                     = "",
    exchange:           str                     = "",
    actor:              str                     = "",
    payload:            Optional[Dict[str, Any]] = None,
) -> MarketPolicyEvent:
    return _make(
        PolicyEventType.POLICY_APPROVED,
        evaluation_id, request_id,
        market_analysis_id=market_analysis_id,
        exchange=exchange,
        policy_id=policy_id, final_action=final_action,
        actor=actor, payload=payload,
    )


def make_market_policy_rejected(
    evaluation_id:      str,
    request_id:         str,
    policy_id:          str,
    *,
    market_analysis_id: str                     = "",
    exchange:           str                     = "",
    actor:              str                     = "",
    payload:            Optional[Dict[str, Any]] = None,
) -> MarketPolicyEvent:
    return _make(
        PolicyEventType.POLICY_REJECTED,
        evaluation_id, request_id,
        market_analysis_id=market_analysis_id,
        exchange=exchange,
        policy_id=policy_id,
        final_action=PolicyAction.REJECT,
        actor=actor, payload=payload,
    )


def make_market_policy_blocked(
    evaluation_id:      str,
    request_id:         str,
    policy_id:          str,
    *,
    market_analysis_id: str                     = "",
    exchange:           str                     = "",
    actor:              str                     = "",
    payload:            Optional[Dict[str, Any]] = None,
) -> MarketPolicyEvent:
    return _make(
        PolicyEventType.POLICY_BLOCKED,
        evaluation_id, request_id,
        market_analysis_id=market_analysis_id,
        exchange=exchange,
        policy_id=policy_id,
        final_action=PolicyAction.BLOCK,
        actor=actor, payload=payload,
    )


def make_market_policy_escalated(
    evaluation_id:      str,
    request_id:         str,
    policy_id:          str,
    *,
    market_analysis_id: str                     = "",
    exchange:           str                     = "",
    actor:              str                     = "",
    payload:            Optional[Dict[str, Any]] = None,
) -> MarketPolicyEvent:
    return _make(
        PolicyEventType.POLICY_ESCALATED,
        evaluation_id, request_id,
        market_analysis_id=market_analysis_id,
        exchange=exchange,
        policy_id=policy_id,
        final_action=PolicyAction.ESCALATE,
        actor=actor, payload=payload,
    )


def make_market_policy_evaluation_completed(
    evaluation_id:      str,
    request_id:         str,
    final_action:       PolicyAction,
    *,
    market_analysis_id: str                     = "",
    exchange:           str                     = "",
    actor:              str                     = "",
    payload:            Optional[Dict[str, Any]] = None,
) -> MarketPolicyEvent:
    return _make(
        PolicyEventType.EVALUATION_COMPLETED,
        evaluation_id, request_id,
        market_analysis_id=market_analysis_id,
        exchange=exchange,
        final_action=final_action,
        actor=actor, payload=payload,
    )
