"""
decision_context.py — iios.decision.lifecycle
===============================================
Context value object for decision lifecycle sessions.

C9 Decision Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    VERSION,
    DecisionPriority,
    DecisionScope,
    DecisionTrigger,
    DecisionType,
)


@dataclass(frozen=True)
class DecisionContext:
    """
    Immutable context object for a decision lifecycle session.

    Carries all contextual information available at the time the decision
    session was created.  Downstream components receive this object to
    access routing and classification metadata without holding a reference
    to the mutable :class:`DecisionSession`.

    Fields
    ------
    context_id :         Unique identifier for this context object.
    session_id :         Associated decision session identifier.
    decision_id :        Identifier of the decision being managed.
    workflow_id :        Optional workflow context.
    portfolio_id :       Optional portfolio context.
    strategy_id :        Optional strategy context.
    decision_scope :     Scope of the decision.
    decision_type :      Type of the decision.
    decision_priority :  Scheduling priority.
    decision_trigger :   What initiated the decision.
    context_metadata :   Free-form supplementary context data.
    created_at :         Wall-clock creation time.
    framework_version :  Framework version string.
    """
    context_id:         str
    session_id:         str
    decision_id:        str

    # routing
    workflow_id:        str               = ""
    portfolio_id:       str               = ""
    strategy_id:        str               = ""

    # classification
    decision_scope:     DecisionScope     = DecisionScope.ORDER
    decision_type:      DecisionType      = DecisionType.ORDER
    decision_priority:  DecisionPriority  = DecisionPriority.MEDIUM
    decision_trigger:   DecisionTrigger   = DecisionTrigger.AUTOMATIC

    # metadata
    context_metadata:   Dict[str, Any]    = field(default_factory=dict)
    created_at:         float             = field(default_factory=time.time)
    framework_version:  str               = VERSION

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------
    @classmethod
    def from_session(
        cls,
        session: Any,
        *,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> "DecisionContext":
        """
        Build a :class:`DecisionContext` from a :class:`DecisionSession`.

        Parameters
        ----------
        session :        Source :class:`DecisionSession`.
        extra_metadata : Optional extra metadata merged with session metadata.
        """
        merged: Dict[str, Any] = dict(session.metadata)
        if extra_metadata:
            merged.update(extra_metadata)

        return cls(
            context_id        = str(uuid.uuid4()),
            session_id        = session.session_id,
            decision_id       = session.decision_id,
            workflow_id       = session.workflow_id,
            portfolio_id      = session.portfolio_id,
            strategy_id       = session.strategy_id,
            decision_scope    = session.decision_scope,
            decision_type     = session.decision_type,
            decision_priority = session.decision_priority,
            decision_trigger  = session.decision_trigger,
            context_metadata  = merged,
        )

    def __repr__(self) -> str:
        return (
            f"DecisionContext("
            f"context_id={self.context_id!r}, "
            f"session_id={self.session_id!r}, "
            f"decision_id={self.decision_id!r})"
        )
