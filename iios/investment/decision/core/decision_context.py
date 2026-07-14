"""iios/investment/decision/core/decision_context.py
DecisionContext — immutable contextual envelope for every decision.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from iios.investment.decision.core.decision_constants import (
    DecisionPriority,
    DecisionType,
    EnvironmentProfile,
)


@dataclass(frozen=True)
class DecisionContext:
    """
    Immutable context passed at decision creation.
    Describes WHAT is being decided and WHERE (environment, source).
    Contains no analysis — purely contextual metadata.
    """
    decision_id:       str
    decision_type:     DecisionType
    subject_id:        str                         # e.g. ticker, portfolio_id, strategy_id
    subject_type:      str                         # e.g. "equity", "portfolio", "strategy"
    environment:       EnvironmentProfile
    priority:          DecisionPriority
    source:            str                         # originating component/agent
    created_at:        datetime
    correlation_id:    str                         # links related decisions
    session_id:        Optional[str]
    parent_decision_id: Optional[str]
    tags:              tuple                       # immutable tag set
    extra:             Dict[str, Any]              # extensible metadata (avoid runtime mutation)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id":        self.decision_id,
            "decision_type":      self.decision_type.value,
            "subject_id":         self.subject_id,
            "subject_type":       self.subject_type,
            "environment":        self.environment.value,
            "priority":           self.priority.value,
            "source":             self.source,
            "created_at":         self.created_at.isoformat(),
            "correlation_id":     self.correlation_id,
            "session_id":         self.session_id,
            "parent_decision_id": self.parent_decision_id,
            "tags":               list(self.tags),
            "extra":              self.extra,
        }


def make_context(
    decision_type:      DecisionType,
    subject_id:         str,
    subject_type:       str,
    source:             str,
    environment:        EnvironmentProfile     = EnvironmentProfile.DEVELOPMENT,
    priority:           DecisionPriority       = DecisionPriority.NORMAL,
    session_id:         Optional[str]          = None,
    parent_decision_id: Optional[str]          = None,
    tags:               tuple                  = (),
    extra:              Optional[Dict[str, Any]] = None,
) -> DecisionContext:
    return DecisionContext(
        decision_id=str(uuid.uuid4()),
        decision_type=decision_type,
        subject_id=subject_id,
        subject_type=subject_type,
        environment=environment,
        priority=priority,
        source=source,
        created_at=datetime.now(timezone.utc),
        correlation_id=str(uuid.uuid4()),
        session_id=session_id,
        parent_decision_id=parent_decision_id,
        tags=tags,
        extra=extra or {},
    )
