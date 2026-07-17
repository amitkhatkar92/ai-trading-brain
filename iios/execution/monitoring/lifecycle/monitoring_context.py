"""iios/execution/monitoring/lifecycle/monitoring_context.py
==================================================
MonitoringContext — immutable context for a single
execution monitoring session.

C6 Execution Intelligence — Phase 6, Module 1
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class MonitoringContext:
    """
    Immutable context for a monitoring session.

    Carries all the identity information needed to create and track
    a MonitoringSession.  Validation is performed by
    MonitoringValidator, not by this class.
    """

    # ── Required correlation IDs ──────────────────────────────────────────────
    execution_session_id: str
    portfolio_id:         str

    # ── Optional correlation IDs ──────────────────────────────────────────────
    gateway_id:  Optional[str] = None
    workflow_id: Optional[str] = None
    strategy_id: Optional[str] = None
    order_id:    Optional[str] = None

    # ── Configuration ─────────────────────────────────────────────────────────
    monitoring_version: int = 1

    # ── Metadata ──────────────────────────────────────────────────────────────
    metadata: Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: float = field(default_factory=time.time, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def has_gateway(self) -> bool:
        return bool(self.gateway_id)

    @property
    def has_workflow(self) -> bool:
        return bool(self.workflow_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_session_id": self.execution_session_id,
            "portfolio_id":         self.portfolio_id,
            "gateway_id":           self.gateway_id,
            "workflow_id":          self.workflow_id,
            "strategy_id":          self.strategy_id,
            "order_id":             self.order_id,
            "monitoring_version":   self.monitoring_version,
            "created_at":           self.created_at,
        }


def make_monitoring_context(
    execution_session_id: str,
    portfolio_id:         str,
    *,
    gateway_id:         Optional[str] = None,
    workflow_id:        Optional[str] = None,
    strategy_id:        Optional[str] = None,
    order_id:           Optional[str] = None,
    monitoring_version: int = 1,
    metadata:           Optional[Dict[str, Any]] = None,
) -> MonitoringContext:
    return MonitoringContext(
        execution_session_id=execution_session_id,
        portfolio_id=portfolio_id,
        gateway_id=gateway_id,
        workflow_id=workflow_id,
        strategy_id=strategy_id,
        order_id=order_id,
        monitoring_version=monitoring_version,
        metadata=metadata or {},
    )
