"""
decision_request.py — iios.decision.engine
============================================
Immutable decision request value object and factory.

C9 Decision Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    DEFAULT_DEADLINE_S,
    VERSION,
    DecisionMode,
    DecisionPriority,
)


@dataclass(frozen=True)
class DecisionRequest:
    """
    Immutable request submitted to :class:`DecisionEngine`.

    Fields
    ------
    request_id :     Unique identifier for this request.
    decision_id :    Caller-supplied decision identifier.
    workflow_id :    Routing context — workflow.
    portfolio_id :   Routing context — portfolio.
    strategy_id :    Routing context — strategy.
    decision_mode :  Scheduling mode.
    decision_reason: Human-readable purpose.
    priority :       Scheduling priority.
    deadline_s :     Maximum allowed wall-clock seconds for the full workflow.
    inputs :         Institutional input snapshots (keyed by source name).
    metadata :       Supplementary caller metadata.
    requested_at :   Wall-clock creation time.
    framework_version : Framework version.
    """
    request_id:         str
    decision_id:        str
    workflow_id:        str                   = ""
    portfolio_id:       str                   = ""
    strategy_id:        str                   = ""
    decision_mode:      DecisionMode          = DecisionMode.REAL_TIME
    decision_reason:    str                   = ""
    priority:           DecisionPriority      = DecisionPriority.MEDIUM
    deadline_s:         float                 = DEFAULT_DEADLINE_S
    inputs:             Dict[str, Any]        = field(default_factory=dict)
    metadata:           Dict[str, Any]        = field(default_factory=dict)
    requested_at:       float                 = field(default_factory=time.time)
    framework_version:  str                   = VERSION

    @classmethod
    def create(
        cls,
        decision_id: str,
        *,
        request_id:     Optional[str]         = None,
        workflow_id:    str                   = "",
        portfolio_id:   str                   = "",
        strategy_id:    str                   = "",
        decision_mode:  DecisionMode          = DecisionMode.REAL_TIME,
        decision_reason: str                  = "",
        priority:       DecisionPriority      = DecisionPriority.MEDIUM,
        deadline_s:     float                 = DEFAULT_DEADLINE_S,
        inputs:         Optional[Dict[str, Any]] = None,
        metadata:       Optional[Dict[str, Any]] = None,
    ) -> "DecisionRequest":
        """
        Create a new :class:`DecisionRequest` with an auto-generated
        ``request_id`` if one is not supplied.
        """
        return cls(
            request_id      = request_id or str(uuid.uuid4()),
            decision_id     = decision_id,
            workflow_id     = workflow_id,
            portfolio_id    = portfolio_id,
            strategy_id     = strategy_id,
            decision_mode   = decision_mode,
            decision_reason = decision_reason,
            priority        = priority,
            deadline_s      = deadline_s,
            inputs          = dict(inputs or {}),
            metadata        = dict(metadata or {}),
        )
