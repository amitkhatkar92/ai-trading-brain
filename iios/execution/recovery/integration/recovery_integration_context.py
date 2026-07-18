"""
iios/execution/recovery/integration/recovery_integration_context.py
===================================================================
IntegrationContext — immutable snapshot of the execution context that
triggered a recovery request.

C7 Execution Recovery & Resilience — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import VERSION


@dataclass(frozen=True)
class IntegrationContext:
    """
    Immutable context describing the execution environment at the time
    a recovery was requested.

    Passed through the integration subsystem alongside the request; consumed
    by health and status monitors.
    """

    context_id:           str
    execution_session_id: str
    subsystem_id:         str
    failure_type:         str
    failure_severity:     str
    failure_reason:       str
    workflow_id:          str           = ""
    gateway_id:           str           = ""
    broker_id:            str           = ""
    portfolio_id:         str           = ""
    strategy_id:          str           = ""
    is_emergency:         bool          = False
    tags:                 Tuple[str, ...] = ()
    metadata:             Dict[str, Any]  = field(default_factory=dict)
    version:              str           = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":           self.context_id,
            "execution_session_id": self.execution_session_id,
            "subsystem_id":         self.subsystem_id,
            "failure_type":         self.failure_type,
            "failure_severity":     self.failure_severity,
            "failure_reason":       self.failure_reason,
            "workflow_id":          self.workflow_id,
            "gateway_id":           self.gateway_id,
            "broker_id":            self.broker_id,
            "portfolio_id":         self.portfolio_id,
            "strategy_id":         self.strategy_id,
            "is_emergency":         self.is_emergency,
            "tags":                 list(self.tags),
            "version":              self.version,
        }


def make_integration_context(
    execution_session_id: str,
    subsystem_id:         str,
    failure_type:         str,
    failure_reason:       str,
    *,
    failure_severity: str  = "MEDIUM",
    workflow_id:      str  = "",
    gateway_id:       str  = "",
    broker_id:        str  = "",
    portfolio_id:     str  = "",
    strategy_id:      str  = "",
    is_emergency:     bool = False,
    tags:             Optional[Tuple[str, ...]] = None,
    metadata:         Optional[Dict[str, Any]]  = None,
    context_id:       Optional[str]             = None,
) -> IntegrationContext:
    return IntegrationContext(
        context_id           = context_id or str(uuid.uuid4()),
        execution_session_id = execution_session_id,
        subsystem_id         = subsystem_id,
        failure_type         = failure_type,
        failure_severity     = failure_severity,
        failure_reason       = failure_reason,
        workflow_id          = workflow_id,
        gateway_id           = gateway_id,
        broker_id            = broker_id,
        portfolio_id         = portfolio_id,
        strategy_id         = strategy_id,
        is_emergency         = is_emergency,
        tags                 = tags or (),
        metadata             = dict(metadata) if metadata else {},
    )
