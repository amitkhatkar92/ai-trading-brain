"""
decision_context.py — iios.decision.engine
============================================
Frozen routing and execution context for a single decision workflow.

C9 Decision Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict

from .constants import (
    VERSION,
    DecisionMode,
    DecisionPriority,
)
from .decision_request import DecisionRequest


@dataclass(frozen=True)
class DecisionEngineContext:
    """
    Immutable context object threaded through every stage of the decision
    processing pipeline.

    Created from a :class:`DecisionRequest` once the engine has assigned
    a session and pipeline identifier.

    Fields
    ------
    context_id :     Unique identifier for this context instance.
    request_id :     Source request identifier.
    session_id :     Lifecycle session identifier (from Decision Lifecycle M1).
    pipeline_id :    Processing pipeline identifier.
    decision_id :    Decision being managed.
    workflow_id :    Routing — workflow.
    portfolio_id :   Routing — portfolio.
    strategy_id :    Routing — strategy.
    decision_mode :  Scheduling mode from the request.
    priority :       Scheduling priority from the request.
    deadline_s :     Per-decision deadline in seconds.
    inputs :         Institutional input snapshot map.
    metadata :       Supplementary metadata.
    created_at :     Wall-clock creation time.
    framework_version : Framework version.
    """
    context_id:        str
    request_id:        str
    session_id:        str
    pipeline_id:       str
    decision_id:       str
    workflow_id:       str               = ""
    portfolio_id:      str               = ""
    strategy_id:       str               = ""
    decision_mode:     DecisionMode      = DecisionMode.REAL_TIME
    priority:          DecisionPriority  = DecisionPriority.MEDIUM
    deadline_s:        float             = 30.0
    inputs:            Dict[str, Any]    = field(default_factory=dict)
    metadata:          Dict[str, Any]    = field(default_factory=dict)
    created_at:        float             = field(default_factory=time.time)
    framework_version: str               = VERSION

    @classmethod
    def from_request(
        cls,
        request:     DecisionRequest,
        *,
        session_id:  str,
        pipeline_id: str,
    ) -> "DecisionEngineContext":
        """
        Create a :class:`DecisionEngineContext` from a validated
        :class:`DecisionRequest` once session and pipeline IDs are available.
        """
        return cls(
            context_id   = str(uuid.uuid4()),
            request_id   = request.request_id,
            session_id   = session_id,
            pipeline_id  = pipeline_id,
            decision_id  = request.decision_id,
            workflow_id  = request.workflow_id,
            portfolio_id = request.portfolio_id,
            strategy_id  = request.strategy_id,
            decision_mode = request.decision_mode,
            priority     = request.priority,
            deadline_s   = request.deadline_s,
            inputs       = dict(request.inputs),
            metadata     = dict(request.metadata),
        )
