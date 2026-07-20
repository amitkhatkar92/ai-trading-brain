"""
decision_factory.py — iios.decision.lifecycle
===============================================
Factory for creating :class:`DecisionSession` instances.

C9 Decision Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from .constants import (
    DecisionPriority,
    DecisionScope,
    DecisionTrigger,
    DecisionType,
)
from .decision_session import DecisionSession


class DecisionFactory:
    """
    Stateless factory for :class:`DecisionSession` instances.

    All parameters are keyword-only after ``decision_id``.  Sensible
    defaults are provided for every optional field so callers can construct
    minimal sessions with a single line::

        session = DecisionFactory().create(decision_id="d-001")
    """

    def create(
        self,
        decision_id: str,
        *,
        session_id:        Optional[str]      = None,
        workflow_id:       str                = "",
        portfolio_id:      str                = "",
        strategy_id:       str                = "",
        decision_scope:    DecisionScope      = DecisionScope.ORDER,
        decision_type:     DecisionType       = DecisionType.ORDER,
        decision_priority: DecisionPriority   = DecisionPriority.MEDIUM,
        decision_trigger:  DecisionTrigger    = DecisionTrigger.AUTOMATIC,
        decision_reason:   str                = "",
        decision_version:  int                = 1,
        metadata:          Optional[Dict[str, Any]] = None,
    ) -> DecisionSession:
        """
        Create a new :class:`DecisionSession` in CREATED state.

        Parameters
        ----------
        decision_id :        Caller-supplied identifier for the decision.
        session_id :         Optional explicit session ID; a UUID is generated
                             if omitted.
        workflow_id :        Workflow routing context.
        portfolio_id :       Portfolio routing context.
        strategy_id :        Strategy routing context.
        decision_scope :     Scope of the decision.
        decision_type :      Type of the decision.
        decision_priority :  Scheduling priority.
        decision_trigger :   What triggered the decision.
        decision_reason :    Human-readable purpose.
        decision_version :   Initial version counter (default 1).
        metadata :           Supplementary session metadata.
        """
        return DecisionSession(
            session_id        = session_id,
            decision_id       = decision_id,
            workflow_id       = workflow_id,
            portfolio_id      = portfolio_id,
            strategy_id       = strategy_id,
            decision_scope    = decision_scope,
            decision_type     = decision_type,
            decision_priority = decision_priority,
            decision_trigger  = decision_trigger,
            decision_reason   = decision_reason,
            decision_version  = decision_version,
            metadata          = metadata,
        )

    def create_with_id(
        self,
        *,
        decision_id: str,
        session_id:  Optional[str] = None,
        **kwargs: Any,
    ) -> DecisionSession:
        """
        Alias for :meth:`create` that accepts keyword-only *decision_id*.

        Useful when the caller builds the arguments as a dict::

            factory.create_with_id(**session_params)
        """
        return self.create(decision_id, session_id=session_id, **kwargs)
