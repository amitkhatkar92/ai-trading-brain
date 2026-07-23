"""
autonomous_governance_context.py — iios.supervisor.governance
--------------------------------------------------------------
Immutable context capturing all enterprise snapshot data required
for a single autonomous governance assessment cycle.

All snapshot fields are stored as Dict[str, Any] to maintain zero
coupling to other IIOS packages.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import VERSION


@dataclass(frozen=True)
class AutonomousGovernanceContext:
    """
    Immutable enterprise-wide context for one governance assessment cycle.

    All snapshot data is captured from the supervision request inputs
    prior to launching the governance pipeline.

    Fields
    ------
    context_id :                    Unique identifier.
    supervision_id :                Supervision run identifier.
    subsystem_id :                  Target subsystem identifier.
    governance_policy_response :    Approved policy response (Dict form of
                                    AIGovernancePolicyResponse).
    supervisor_snapshot :           Supervisor engine snapshot (Dict form).
    execution_snapshot :            Execution intelligence snapshot.
    execution_recovery_snapshot :   Execution recovery snapshot.
    execution_analytics_snapshot :  Execution analytics snapshot.
    decision_snapshot :             Decision intelligence snapshot.
    portfolio_snapshot :            Portfolio intelligence snapshot.
    risk_snapshot :                 Risk intelligence snapshot.
    market_snapshot :               Market intelligence snapshot.
    platform_health :               Platform health metrics.
    infrastructure_metrics :        Infrastructure telemetry.
    audit_events :                  Recent audit events.
    inputs :                        Raw key-value input extras.
    created_at :                    Context creation time.
    framework_version :             Framework version string.
    """
    context_id:                   str
    supervision_id:               str
    subsystem_id:                 str
    governance_policy_response:   Dict[str, Any] = field(default_factory=dict)
    supervisor_snapshot:          Dict[str, Any] = field(default_factory=dict)
    execution_snapshot:           Dict[str, Any] = field(default_factory=dict)
    execution_recovery_snapshot:  Dict[str, Any] = field(default_factory=dict)
    execution_analytics_snapshot: Dict[str, Any] = field(default_factory=dict)
    decision_snapshot:            Dict[str, Any] = field(default_factory=dict)
    portfolio_snapshot:           Dict[str, Any] = field(default_factory=dict)
    risk_snapshot:                Dict[str, Any] = field(default_factory=dict)
    market_snapshot:              Dict[str, Any] = field(default_factory=dict)
    platform_health:              Dict[str, Any] = field(default_factory=dict)
    infrastructure_metrics:       Dict[str, Any] = field(default_factory=dict)
    audit_events:                 List[Dict[str, Any]] = field(default_factory=list)
    inputs:                       Dict[str, Any] = field(default_factory=dict)
    created_at:                   float           = field(default_factory=time.time)
    framework_version:            str             = VERSION

    @classmethod
    def create(
        cls,
        supervision_id: str,
        subsystem_id:   str = "",
        *,
        context_id:                   Optional[str]                  = None,
        governance_policy_response:   Optional[Dict[str, Any]]       = None,
        supervisor_snapshot:          Optional[Dict[str, Any]]       = None,
        execution_snapshot:           Optional[Dict[str, Any]]       = None,
        execution_recovery_snapshot:  Optional[Dict[str, Any]]       = None,
        execution_analytics_snapshot: Optional[Dict[str, Any]]       = None,
        decision_snapshot:            Optional[Dict[str, Any]]       = None,
        portfolio_snapshot:           Optional[Dict[str, Any]]       = None,
        risk_snapshot:                Optional[Dict[str, Any]]       = None,
        market_snapshot:              Optional[Dict[str, Any]]       = None,
        platform_health:              Optional[Dict[str, Any]]       = None,
        infrastructure_metrics:       Optional[Dict[str, Any]]       = None,
        audit_events:                 Optional[List[Dict[str, Any]]] = None,
        inputs:                       Optional[Dict[str, Any]]       = None,
    ) -> "AutonomousGovernanceContext":
        return cls(
            context_id                   = context_id or str(uuid.uuid4()),
            supervision_id               = supervision_id,
            subsystem_id                 = subsystem_id,
            governance_policy_response   = governance_policy_response   or {},
            supervisor_snapshot          = supervisor_snapshot          or {},
            execution_snapshot           = execution_snapshot           or {},
            execution_recovery_snapshot  = execution_recovery_snapshot  or {},
            execution_analytics_snapshot = execution_analytics_snapshot or {},
            decision_snapshot            = decision_snapshot            or {},
            portfolio_snapshot           = portfolio_snapshot           or {},
            risk_snapshot                = risk_snapshot                or {},
            market_snapshot              = market_snapshot              or {},
            platform_health              = platform_health              or {},
            infrastructure_metrics       = infrastructure_metrics       or {},
            audit_events                 = audit_events                 or [],
            inputs                       = inputs                       or {},
        )

    @classmethod
    def from_inputs(
        cls,
        supervision_id: str,
        subsystem_id:   str,
        inputs:         Dict[str, Any],
    ) -> "AutonomousGovernanceContext":
        """Build a context by extracting known snapshot keys from a flat inputs dict."""
        return cls.create(
            supervision_id,
            subsystem_id,
            governance_policy_response   = inputs.get("governance_policy_response"),
            supervisor_snapshot          = inputs.get("supervisor_snapshot"),
            execution_snapshot           = inputs.get("execution_snapshot"),
            execution_recovery_snapshot  = inputs.get("execution_recovery_snapshot"),
            execution_analytics_snapshot = inputs.get("execution_analytics_snapshot"),
            decision_snapshot            = inputs.get("decision_snapshot"),
            portfolio_snapshot           = inputs.get("portfolio_snapshot"),
            risk_snapshot                = inputs.get("risk_snapshot"),
            market_snapshot              = inputs.get("market_snapshot"),
            platform_health              = inputs.get("platform_health"),
            infrastructure_metrics       = inputs.get("infrastructure_metrics"),
            audit_events                 = inputs.get("audit_events"),
            inputs                       = inputs,
        )

    def snapshot_count(self) -> int:
        """Return the number of non-empty snapshots present."""
        snapshots = [
            self.governance_policy_response,
            self.supervisor_snapshot,
            self.execution_snapshot,
            self.execution_recovery_snapshot,
            self.execution_analytics_snapshot,
            self.decision_snapshot,
            self.portfolio_snapshot,
            self.risk_snapshot,
            self.market_snapshot,
            self.platform_health,
            self.infrastructure_metrics,
        ]
        return sum(1 for s in snapshots if s)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":     self.context_id,
            "supervision_id": self.supervision_id,
            "subsystem_id":   self.subsystem_id,
            "snapshot_count": self.snapshot_count(),
            "audit_events":   len(self.audit_events),
            "created_at":     self.created_at,
            "framework_version": self.framework_version,
        }
