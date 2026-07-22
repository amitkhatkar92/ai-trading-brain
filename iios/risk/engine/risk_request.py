"""
risk_request.py — iios.risk.engine
=====================================
Immutable risk workflow request value object.

C11 Risk Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    VERSION,
    RiskWorkflowType,
    SchedulerPriority,
)
from .risk_context import RiskEngineContext


@dataclass(frozen=True)
class RiskRequest:
    """
    Immutable risk workflow request.

    Wraps all inputs required to execute a single risk workflow pipeline.

    Fields
    ------
    request_id :        Unique request identifier.
    risk_id :           Risk assessment identifier.
    portfolio_id :      Target portfolio identifier.
    workflow_type :     Risk workflow classification.
    priority :          Scheduling priority.
    context :           Engine-level operational context.
    inputs :            Collected institutional snapshots.
                        Keys include: "portfolio_snapshot",
                        "decision_snapshot", "execution_analytics_snapshot",
                        "order_snapshot", "position_snapshot",
                        "account_snapshot", "market_snapshot", etc.
    requested_at :      Wall-clock request creation time.
    metadata :          Supplementary request metadata.
    framework_version : Framework version string.
    """
    request_id:        str
    risk_id:           str
    portfolio_id:      str
    workflow_type:     RiskWorkflowType
    priority:          SchedulerPriority
    context:           RiskEngineContext
    inputs:            Dict[str, Any]   = field(default_factory=dict)
    requested_at:      float            = field(default_factory=time.time)
    metadata:          Dict[str, Any]   = field(default_factory=dict)
    framework_version: str              = VERSION

    @classmethod
    def create(
        cls,
        risk_id:       str,
        portfolio_id:  str,
        workflow_type: RiskWorkflowType = RiskWorkflowType.PORTFOLIO_RISK_ASSESSMENT,
        *,
        request_id:  Optional[str]              = None,
        priority:    SchedulerPriority           = SchedulerPriority.NORMAL,
        context:     Optional[RiskEngineContext] = None,
        strategy_id: str                        = "",
        inputs:      Optional[Dict[str, Any]]   = None,
        metadata:    Optional[Dict[str, Any]]   = None,
    ) -> "RiskRequest":
        rid = request_id or str(uuid.uuid4())
        ctx = context or RiskEngineContext.create(
            risk_id,
            portfolio_id,
            workflow_type,
            priority    = priority,
            strategy_id = strategy_id,
        )
        return cls(
            request_id    = rid,
            risk_id       = risk_id,
            portfolio_id  = portfolio_id,
            workflow_type = workflow_type,
            priority      = priority,
            context       = ctx,
            inputs        = dict(inputs or {}),
            metadata      = dict(metadata or {}),
        )

    def with_inputs(self, inputs: Dict[str, Any]) -> "RiskRequest":
        """Return a new request with the given inputs merged in."""
        merged = {**self.inputs, **inputs}
        return RiskRequest(
            request_id        = self.request_id,
            risk_id           = self.risk_id,
            portfolio_id      = self.portfolio_id,
            workflow_type     = self.workflow_type,
            priority          = self.priority,
            context           = self.context,
            inputs            = merged,
            requested_at      = self.requested_at,
            metadata          = dict(self.metadata),
            framework_version = self.framework_version,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":        self.request_id,
            "risk_id":           self.risk_id,
            "portfolio_id":      self.portfolio_id,
            "workflow_type":     self.workflow_type.value,
            "priority":          self.priority.value,
            "input_keys":        list(self.inputs.keys()),
            "requested_at":      self.requested_at,
            "framework_version": self.framework_version,
        }
