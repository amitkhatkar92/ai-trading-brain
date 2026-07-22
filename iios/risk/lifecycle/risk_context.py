"""
risk_context.py — iios.risk.lifecycle
========================================
Immutable operational context attached to a risk session.

C11 Risk Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    VERSION,
    RiskPriority,
    RiskScope,
    RiskType,
)


@dataclass(frozen=True)
class RiskContext:
    """
    Immutable operational context that parameterises a risk session.

    Captured at session creation; never mutated afterwards.

    Fields
    ------
    context_id :        Unique identifier.
    risk_id :           Risk assessment identifier.
    portfolio_id :      Portfolio being assessed.
    strategy_id :       Strategy being assessed (may be empty).
    workflow_id :       Optional workflow routing context.
    risk_type :         Type of risk being assessed.
    risk_scope :        Scope of the risk assessment.
    risk_priority :     Priority level of this session.
    metadata :          Supplementary context metadata.
    framework_version : Framework version.
    """
    context_id:        str
    risk_id:           str
    portfolio_id:      str
    strategy_id:       str            = ""
    workflow_id:       str            = ""
    risk_type:         RiskType       = RiskType.CUSTOM
    risk_scope:        RiskScope      = RiskScope.PORTFOLIO
    risk_priority:     RiskPriority   = RiskPriority.MEDIUM
    metadata:          Dict[str, Any] = field(default_factory=dict)
    framework_version: str            = VERSION

    @classmethod
    def create(
        cls,
        risk_id:      str,
        portfolio_id: str,
        *,
        context_id:    Optional[str]          = None,
        strategy_id:   str                    = "",
        workflow_id:   str                    = "",
        risk_type:     RiskType               = RiskType.CUSTOM,
        risk_scope:    RiskScope              = RiskScope.PORTFOLIO,
        risk_priority: RiskPriority           = RiskPriority.MEDIUM,
        metadata:      Optional[Dict[str, Any]] = None,
    ) -> "RiskContext":
        return cls(
            context_id    = context_id or str(uuid.uuid4()),
            risk_id       = risk_id,
            portfolio_id  = portfolio_id,
            strategy_id   = strategy_id,
            workflow_id   = workflow_id,
            risk_type     = risk_type,
            risk_scope    = risk_scope,
            risk_priority = risk_priority,
            metadata      = dict(metadata or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":        self.context_id,
            "risk_id":           self.risk_id,
            "portfolio_id":      self.portfolio_id,
            "strategy_id":       self.strategy_id,
            "workflow_id":       self.workflow_id,
            "risk_type":         self.risk_type.value,
            "risk_scope":        self.risk_scope.value,
            "risk_priority":     self.risk_priority.value,
            "framework_version": self.framework_version,
        }
