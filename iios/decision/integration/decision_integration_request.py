"""
decision_integration_request.py — iios.decision.integration
=============================================================
Immutable public request submitted to :class:`DecisionIntegrationEngine`.

C9 Decision Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import DEFAULT_DEADLINE_S, VERSION


@dataclass(frozen=True)
class DecisionIntegrationRequest:
    """
    Immutable request submitted to the Decision Integration Engine.

    This is the ONLY input type accepted by
    :meth:`DecisionIntegrationEngine.submit`.

    Fields
    ------
    request_id :        Unique identifier for this request.
    decision_id :       Caller-supplied decision identifier.
    workflow_id :       Routing context — workflow.
    portfolio_id :      Routing context — portfolio.
    strategy_id :       Routing context — strategy.
    decision_scope :    Scope of the decision (e.g. "order").
    decision_type :     Type of the decision (e.g. "order").
    decision_priority : Priority string (e.g. "medium").
    decision_trigger :  What triggered the decision (e.g. "automatic").
    decision_reason :   Human-readable purpose of this decision.
    inputs :            Institutional input snapshots (keyed by source name).
    metadata :          Supplementary caller metadata.
    deadline_s :        Maximum allowed wall-clock seconds for the workflow.
    requested_at :      Wall-clock creation time (seconds since epoch).
    framework_version : Framework version.
    """

    request_id:         str
    decision_id:        str
    workflow_id:        str            = ""
    portfolio_id:       str            = ""
    strategy_id:        str            = ""
    decision_scope:     str            = "order"
    decision_type:      str            = "order"
    decision_priority:  str            = "medium"
    decision_trigger:   str            = "automatic"
    decision_reason:    str            = ""
    inputs:             Dict[str, Any] = field(default_factory=dict)
    metadata:           Dict[str, Any] = field(default_factory=dict)
    deadline_s:         float          = DEFAULT_DEADLINE_S
    requested_at:       float          = field(default_factory=time.time)
    framework_version:  str            = VERSION

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        decision_id: str,
        *,
        request_id:        Optional[str]          = None,
        workflow_id:       str                    = "",
        portfolio_id:      str                    = "",
        strategy_id:       str                    = "",
        decision_scope:    str                    = "order",
        decision_type:     str                    = "order",
        decision_priority: str                    = "medium",
        decision_trigger:  str                    = "automatic",
        decision_reason:   str                    = "",
        inputs:            Optional[Dict[str, Any]] = None,
        metadata:          Optional[Dict[str, Any]] = None,
        deadline_s:        float                  = DEFAULT_DEADLINE_S,
    ) -> "DecisionIntegrationRequest":
        """
        Create a new request with an auto-generated ``request_id`` when not
        provided.
        """
        return cls(
            request_id        = request_id or str(uuid.uuid4()),
            decision_id       = decision_id,
            workflow_id       = workflow_id,
            portfolio_id      = portfolio_id,
            strategy_id       = strategy_id,
            decision_scope    = decision_scope,
            decision_type     = decision_type,
            decision_priority = decision_priority,
            decision_trigger  = decision_trigger,
            decision_reason   = decision_reason,
            inputs            = dict(inputs or {}),
            metadata          = dict(metadata or {}),
            deadline_s        = deadline_s,
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":        self.request_id,
            "decision_id":       self.decision_id,
            "workflow_id":       self.workflow_id,
            "portfolio_id":      self.portfolio_id,
            "strategy_id":       self.strategy_id,
            "decision_scope":    self.decision_scope,
            "decision_type":     self.decision_type,
            "decision_priority": self.decision_priority,
            "decision_trigger":  self.decision_trigger,
            "decision_reason":   self.decision_reason,
            "deadline_s":        self.deadline_s,
            "requested_at":      self.requested_at,
            "framework_version": self.framework_version,
        }

    def __repr__(self) -> str:
        return (
            f"DecisionIntegrationRequest("
            f"request_id={self.request_id!r}, "
            f"decision_id={self.decision_id!r}, "
            f"scope={self.decision_scope!r})"
        )
