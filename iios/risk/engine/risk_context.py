"""
risk_context.py — iios.risk.engine
=====================================
Immutable engine-level operational context for a risk workflow request.

C11 Risk Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    VERSION,
    RiskWorkflowType,
    SchedulerPriority,
)


@dataclass(frozen=True)
class RiskEngineContext:
    """
    Immutable operational context attached to a risk workflow request.

    Captured at request creation; never mutated afterwards.

    Fields
    ------
    context_id :        Unique identifier.
    risk_id :           Risk assessment identifier.
    portfolio_id :      Portfolio being assessed.
    workflow_type :     Risk workflow classification.
    priority :          Scheduling priority.
    strategy_id :       Strategy being assessed (may be empty).
    workflow_id :       Workflow routing correlation.
    metadata :          Supplementary context metadata.
    framework_version : Framework version.
    """
    context_id:        str
    risk_id:           str
    portfolio_id:      str
    workflow_type:     RiskWorkflowType
    priority:          SchedulerPriority   = SchedulerPriority.NORMAL
    strategy_id:       str                = ""
    workflow_id:       str                = ""
    metadata:          Dict[str, Any]     = field(default_factory=dict)
    framework_version: str                = VERSION

    @classmethod
    def create(
        cls,
        risk_id:      str,
        portfolio_id: str,
        workflow_type: RiskWorkflowType,
        *,
        context_id:  Optional[str]          = None,
        priority:    SchedulerPriority       = SchedulerPriority.NORMAL,
        strategy_id: str                    = "",
        workflow_id: str                    = "",
        metadata:    Optional[Dict[str, Any]] = None,
    ) -> "RiskEngineContext":
        return cls(
            context_id    = context_id or str(uuid.uuid4()),
            risk_id       = risk_id,
            portfolio_id  = portfolio_id,
            workflow_type = workflow_type,
            priority      = priority,
            strategy_id   = strategy_id,
            workflow_id   = workflow_id,
            metadata      = dict(metadata or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":        self.context_id,
            "risk_id":           self.risk_id,
            "portfolio_id":      self.portfolio_id,
            "workflow_type":     self.workflow_type.value,
            "priority":          self.priority.value,
            "strategy_id":       self.strategy_id,
            "workflow_id":       self.workflow_id,
            "framework_version": self.framework_version,
        }
