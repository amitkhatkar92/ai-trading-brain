"""
supervisor_integration_context.py — iios.supervisor.integration
----------------------------------------------------------------
Immutable context value object extracted from an integration request.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import IntegrationMode, VERSION


@dataclass(frozen=True)
class SupervisorIntegrationContext:
    """
    Immutable context extracted from a supervisor integration request.

    Carries all platform snapshots needed by M2-M5 subsystems.

    Fields
    ------
    context_id :                  Unique identifier for this context object.
    integration_id :              Parent integration run identifier.
    session_id :                  Owning lifecycle session identifier.
    workflow_id :                 Workflow routing identifier.
    mode :                        Integration execution mode.
    execution_snapshot :          Execution subsystem snapshot (raw dict).
    execution_recovery_snapshot : Execution recovery subsystem snapshot.
    execution_analytics_snapshot: Execution analytics subsystem snapshot.
    decision_snapshot :           Decision engine snapshot.
    portfolio_snapshot :          Portfolio subsystem snapshot.
    risk_snapshot :               Risk subsystem snapshot.
    market_snapshot :             Market subsystem snapshot.
    extra :                       Additional key-value metadata.
    created_at :                  Wall-clock creation timestamp.
    framework_version :           Framework version string.
    """
    context_id:                   str
    integration_id:               str
    session_id:                   str
    workflow_id:                  str
    mode:                         IntegrationMode
    execution_snapshot:           Dict[str, Any]
    execution_recovery_snapshot:  Dict[str, Any]
    execution_analytics_snapshot: Dict[str, Any]
    decision_snapshot:            Dict[str, Any]
    portfolio_snapshot:           Dict[str, Any]
    risk_snapshot:                Dict[str, Any]
    market_snapshot:              Dict[str, Any]
    extra:                        Dict[str, Any]
    created_at:                   float = field(default_factory=time.time)
    framework_version:            str   = VERSION

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        integration_id: str,
        *,
        context_id:                   Optional[str]            = None,
        session_id:                   str                      = "",
        workflow_id:                  str                      = "",
        mode:                         IntegrationMode          = IntegrationMode.FULL,
        execution_snapshot:           Optional[Dict[str, Any]] = None,
        execution_recovery_snapshot:  Optional[Dict[str, Any]] = None,
        execution_analytics_snapshot: Optional[Dict[str, Any]] = None,
        decision_snapshot:            Optional[Dict[str, Any]] = None,
        portfolio_snapshot:           Optional[Dict[str, Any]] = None,
        risk_snapshot:                Optional[Dict[str, Any]] = None,
        market_snapshot:              Optional[Dict[str, Any]] = None,
        extra:                        Optional[Dict[str, Any]] = None,
    ) -> "SupervisorIntegrationContext":
        return cls(
            context_id                   = context_id or str(uuid.uuid4()),
            integration_id               = integration_id,
            session_id                   = session_id or str(uuid.uuid4()),
            workflow_id                  = workflow_id or str(uuid.uuid4()),
            mode                         = mode,
            execution_snapshot           = execution_snapshot or {},
            execution_recovery_snapshot  = execution_recovery_snapshot or {},
            execution_analytics_snapshot = execution_analytics_snapshot or {},
            decision_snapshot            = decision_snapshot or {},
            portfolio_snapshot           = portfolio_snapshot or {},
            risk_snapshot                = risk_snapshot or {},
            market_snapshot              = market_snapshot or {},
            extra                        = extra or {},
        )

    @classmethod
    def from_inputs(
        cls,
        integration_id: str,
        inputs: Dict[str, Any],
        *,
        context_id:  Optional[str]     = None,
        session_id:  str               = "",
        workflow_id: str               = "",
        mode:        IntegrationMode   = IntegrationMode.FULL,
    ) -> "SupervisorIntegrationContext":
        """Build a context by extracting known keys from a flat ``inputs`` dict."""
        known = {
            "execution_snapshot",
            "execution_recovery_snapshot",
            "execution_analytics_snapshot",
            "decision_snapshot",
            "portfolio_snapshot",
            "risk_snapshot",
            "market_snapshot",
        }
        extra = {k: v for k, v in inputs.items() if k not in known}
        return cls.create(
            integration_id               = integration_id,
            context_id                   = context_id,
            session_id                   = session_id,
            workflow_id                  = workflow_id,
            mode                         = mode,
            execution_snapshot           = inputs.get("execution_snapshot") or {},
            execution_recovery_snapshot  = inputs.get("execution_recovery_snapshot") or {},
            execution_analytics_snapshot = inputs.get("execution_analytics_snapshot") or {},
            decision_snapshot            = inputs.get("decision_snapshot") or {},
            portfolio_snapshot           = inputs.get("portfolio_snapshot") or {},
            risk_snapshot                = inputs.get("risk_snapshot") or {},
            market_snapshot              = inputs.get("market_snapshot") or {},
            extra                        = extra,
        )

    # ------------------------------------------------------------------
    # Derived helpers
    # ------------------------------------------------------------------

    def all_inputs(self) -> Dict[str, Any]:
        """Return a flat dict of all collected subsystem snapshots."""
        return {
            "execution_snapshot":           self.execution_snapshot,
            "execution_recovery_snapshot":  self.execution_recovery_snapshot,
            "execution_analytics_snapshot": self.execution_analytics_snapshot,
            "decision_snapshot":            self.decision_snapshot,
            "portfolio_snapshot":           self.portfolio_snapshot,
            "risk_snapshot":                self.risk_snapshot,
            "market_snapshot":              self.market_snapshot,
            **self.extra,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":      self.context_id,
            "integration_id":  self.integration_id,
            "session_id":      self.session_id,
            "workflow_id":     self.workflow_id,
            "mode":            self.mode.value,
            "created_at":      self.created_at,
            "framework_version": self.framework_version,
        }
