"""
risk_assessment_events.py — iios.risk.assessment
==================================================
Domain event value object and 10 factory functions for the
Risk Assessment & Optimization Framework.

C11 Risk Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import AssessmentEventType, AssessmentStatus, VERSION


# ---------------------------------------------------------------------------
# Event value object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RiskAssessmentEvent:
    """
    Immutable domain event for the Risk Assessment Framework.

    Fields
    ------
    event_id :          Unique event identifier.
    event_type :        Classification of the event.
    assessment_id :     Correlation identifier.
    portfolio_id :      Target portfolio.
    status :            Assessment status at time of event.
    actor :             Component that emitted the event.
    payload :           Supplementary event payload.
    occurred_at :       Wall-clock time the event occurred.
    framework_version : Framework version string.
    """
    event_id:          str
    event_type:        AssessmentEventType
    assessment_id:     str
    portfolio_id:      str
    status:            AssessmentStatus
    actor:             str               = ""
    payload:           Dict[str, Any]    = field(default_factory=dict)
    occurred_at:       float             = field(default_factory=time.time)
    framework_version: str               = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":          self.event_id,
            "event_type":        self.event_type.value,
            "assessment_id":     self.assessment_id,
            "portfolio_id":      self.portfolio_id,
            "status":            self.status.value,
            "actor":             self.actor,
            "occurred_at":       self.occurred_at,
            "framework_version": self.framework_version,
        }


# ---------------------------------------------------------------------------
# Internal factory helper
# ---------------------------------------------------------------------------

def _make(
    event_type:    AssessmentEventType,
    assessment_id: str,
    portfolio_id:  str,
    status:        AssessmentStatus,
    *,
    actor:   str                       = "",
    payload: Optional[Dict[str, Any]]  = None,
) -> RiskAssessmentEvent:
    return RiskAssessmentEvent(
        event_id      = str(uuid.uuid4()),
        event_type    = event_type,
        assessment_id = assessment_id,
        portfolio_id  = portfolio_id,
        status        = status,
        actor         = actor,
        payload       = dict(payload or {}),
    )


# ---------------------------------------------------------------------------
# 10 public factory functions
# ---------------------------------------------------------------------------

def make_assessment_started(
    assessment_id: str,
    portfolio_id:  str,
    *,
    actor:   str                       = "",
    payload: Optional[Dict[str, Any]]  = None,
) -> RiskAssessmentEvent:
    return _make(
        AssessmentEventType.ASSESSMENT_STARTED,
        assessment_id, portfolio_id,
        AssessmentStatus.PROCESSING,
        actor=actor, payload=payload,
    )


def make_models_loaded(
    assessment_id: str,
    portfolio_id:  str,
    *,
    models_count: int                    = 0,
    actor:        str                    = "",
    payload:      Optional[Dict[str, Any]] = None,
) -> RiskAssessmentEvent:
    p = dict(payload or {})
    p["models_count"] = models_count
    return _make(
        AssessmentEventType.MODELS_LOADED,
        assessment_id, portfolio_id,
        AssessmentStatus.PROCESSING,
        actor=actor, payload=p,
    )


def make_risk_calculated(
    assessment_id: str,
    portfolio_id:  str,
    *,
    risk_score: float                    = 0.0,
    actor:      str                      = "",
    payload:    Optional[Dict[str, Any]] = None,
) -> RiskAssessmentEvent:
    p = dict(payload or {})
    p["risk_score"] = risk_score
    return _make(
        AssessmentEventType.RISK_CALCULATED,
        assessment_id, portfolio_id,
        AssessmentStatus.PROCESSING,
        actor=actor, payload=p,
    )


def make_stress_test_completed(
    assessment_id: str,
    portfolio_id:  str,
    *,
    worst_loss_pct: float                  = 0.0,
    actor:          str                    = "",
    payload:        Optional[Dict[str, Any]] = None,
) -> RiskAssessmentEvent:
    p = dict(payload or {})
    p["worst_loss_pct"] = worst_loss_pct
    return _make(
        AssessmentEventType.STRESS_TEST_COMPLETED,
        assessment_id, portfolio_id,
        AssessmentStatus.PROCESSING,
        actor=actor, payload=p,
    )


def make_scenario_analysis_completed(
    assessment_id: str,
    portfolio_id:  str,
    *,
    expected_return_pct: float               = 0.0,
    actor:               str                 = "",
    payload:             Optional[Dict[str, Any]] = None,
) -> RiskAssessmentEvent:
    p = dict(payload or {})
    p["expected_return_pct"] = expected_return_pct
    return _make(
        AssessmentEventType.SCENARIO_ANALYSIS_COMPLETED,
        assessment_id, portfolio_id,
        AssessmentStatus.PROCESSING,
        actor=actor, payload=p,
    )


def make_optimization_completed(
    assessment_id: str,
    portfolio_id:  str,
    *,
    optimization_gain: float                 = 0.0,
    actor:             str                   = "",
    payload:           Optional[Dict[str, Any]] = None,
) -> RiskAssessmentEvent:
    p = dict(payload or {})
    p["optimization_gain"] = optimization_gain
    return _make(
        AssessmentEventType.OPTIMIZATION_COMPLETED,
        assessment_id, portfolio_id,
        AssessmentStatus.PROCESSING,
        actor=actor, payload=p,
    )


def make_mitigation_generated(
    assessment_id: str,
    portfolio_id:  str,
    *,
    actions_count: int                     = 0,
    actor:         str                     = "",
    payload:       Optional[Dict[str, Any]] = None,
) -> RiskAssessmentEvent:
    p = dict(payload or {})
    p["actions_count"] = actions_count
    return _make(
        AssessmentEventType.MITIGATION_GENERATED,
        assessment_id, portfolio_id,
        AssessmentStatus.PROCESSING,
        actor=actor, payload=p,
    )


def make_assessment_validated(
    assessment_id: str,
    portfolio_id:  str,
    *,
    checks_passed: int                     = 0,
    actor:         str                     = "",
    payload:       Optional[Dict[str, Any]] = None,
) -> RiskAssessmentEvent:
    p = dict(payload or {})
    p["checks_passed"] = checks_passed
    return _make(
        AssessmentEventType.ASSESSMENT_VALIDATED,
        assessment_id, portfolio_id,
        AssessmentStatus.PROCESSING,
        actor=actor, payload=p,
    )


def make_assessment_published(
    assessment_id: str,
    portfolio_id:  str,
    *,
    risk_score: float                    = 0.0,
    actor:      str                      = "",
    payload:    Optional[Dict[str, Any]] = None,
) -> RiskAssessmentEvent:
    p = dict(payload or {})
    p["risk_score"] = risk_score
    return _make(
        AssessmentEventType.ASSESSMENT_PUBLISHED,
        assessment_id, portfolio_id,
        AssessmentStatus.COMPLETED,
        actor=actor, payload=p,
    )


def make_assessment_failed(
    assessment_id: str,
    portfolio_id:  str,
    *,
    reason:  str                         = "",
    actor:   str                         = "",
    payload: Optional[Dict[str, Any]]    = None,
) -> RiskAssessmentEvent:
    p = dict(payload or {})
    p["reason"] = reason
    return _make(
        AssessmentEventType.ASSESSMENT_FAILED,
        assessment_id, portfolio_id,
        AssessmentStatus.FAILED,
        actor=actor, payload=p,
    )
