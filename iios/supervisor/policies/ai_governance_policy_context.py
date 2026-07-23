"""
ai_governance_policy_context.py — iios.supervisor.policies
------------------------------------------------------------
Immutable governance evaluation context value object.

The context carries all platform state snapshots that governance
policies are permitted to inspect during evaluation.  No snapshot
type is imported — all snapshots are stored as plain dicts so that
this module has zero cross-package dependencies.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import VERSION


@dataclass(frozen=True)
class AIGovernancePolicyContext:
    """
    Immutable snapshot of platform state for governance evaluation.

    All snapshot fields are plain :class:`dict` so that this module
    has no cross-package import dependencies.

    Fields
    ------
    context_id :           Unique identifier.
    supervision_id :       Parent supervision run identifier.
    platform_health :      Platform-wide health indicators (PlatformHealth).
    model_metadata :       Active model metadata (ModelMetadata).
    market_snapshot :      Current market state (MarketSnapshot).
    risk_snapshot :        Current risk state (RiskSnapshot).
    portfolio_snapshot :   Current portfolio state (PortfolioSnapshot).
    decision_snapshot :    Recent decision state (DecisionSnapshot).
    execution_snapshot :   Recent execution state (ExecutionSnapshot).
    supervisor_snapshot :  Supervisor state (SupervisorSnapshot).
    inputs :               Flat evaluation inputs for condition evaluation.
    created_at :           Wall-clock creation time.
    framework_version :    Framework version string.
    """
    context_id:          str
    supervision_id:      str
    platform_health:     Dict[str, Any]
    model_metadata:      Dict[str, Any]
    market_snapshot:     Dict[str, Any]
    risk_snapshot:       Dict[str, Any]
    portfolio_snapshot:  Dict[str, Any]
    decision_snapshot:   Dict[str, Any]
    execution_snapshot:  Dict[str, Any]
    supervisor_snapshot: Dict[str, Any]
    inputs:              Dict[str, Any]
    created_at:          float          = field(default_factory=time.time)
    framework_version:   str            = VERSION

    @classmethod
    def create(
        cls,
        supervision_id: str,
        *,
        context_id:          Optional[str]             = None,
        platform_health:     Optional[Dict[str, Any]]  = None,
        model_metadata:      Optional[Dict[str, Any]]  = None,
        market_snapshot:     Optional[Dict[str, Any]]  = None,
        risk_snapshot:       Optional[Dict[str, Any]]  = None,
        portfolio_snapshot:  Optional[Dict[str, Any]]  = None,
        decision_snapshot:   Optional[Dict[str, Any]]  = None,
        execution_snapshot:  Optional[Dict[str, Any]]  = None,
        supervisor_snapshot: Optional[Dict[str, Any]]  = None,
        inputs:              Optional[Dict[str, Any]]  = None,
    ) -> "AIGovernancePolicyContext":
        return cls(
            context_id          = context_id or str(uuid.uuid4()),
            supervision_id      = supervision_id,
            platform_health     = platform_health     or {},
            model_metadata      = model_metadata      or {},
            market_snapshot     = market_snapshot     or {},
            risk_snapshot       = risk_snapshot       or {},
            portfolio_snapshot  = portfolio_snapshot  or {},
            decision_snapshot   = decision_snapshot   or {},
            execution_snapshot  = execution_snapshot  or {},
            supervisor_snapshot = supervisor_snapshot or {},
            inputs              = inputs              or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":        self.context_id,
            "supervision_id":    self.supervision_id,
            "platform_health":   dict(self.platform_health),
            "inputs":            dict(self.inputs),
            "created_at":        self.created_at,
            "framework_version": self.framework_version,
        }
