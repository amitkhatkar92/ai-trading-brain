"""iios/execution/risk/engine/execution_risk_factory.py
==================================================
EvaluationFactory — creates M1 ExecutionRisk objects and
EvaluationContext objects from engine-layer EvaluationRequest objects.

C6 Execution Intelligence — Phase 4, Module 2
"""
from __future__ import annotations

import time

from iios.execution.risk.lifecycle import RiskFactory

from .constants import ACTOR_ENGINE
from .execution_risk_context import EvaluationContext, make_evaluation_context
from .execution_risk_request import EvaluationRequest


class EvaluationFactory:
    """
    Stateless factory used by the RiskManager to create:
    1. M1 ``ExecutionRisk`` domain objects from ``EvaluationRequest``
    2. ``EvaluationContext`` objects for rule invocations
    """

    def __init__(self) -> None:
        self._risk_factory = RiskFactory()

    # ── ExecutionRisk ─────────────────────────────────────────────────────────

    def create_from_request(self, request: "EvaluationRequest"):
        """Create an M1 ``ExecutionRisk`` from *request*."""
        from iios.execution.risk.lifecycle import ExecutionRisk

        expiry_time = None
        if request.expiry_ttl_seconds is not None and request.expiry_ttl_seconds > 0:
            expiry_time = time.time() + request.expiry_ttl_seconds

        return self._risk_factory.create(
            risk_category=request.risk_category,
            execution_id=request.execution_id,
            order_id=request.order_id,
            position_id=request.position_id,
            portfolio_id=request.portfolio_id,
            strategy_id=request.strategy_id,
            decision_id=request.decision_id,
            workflow_id=request.workflow_id,
            correlation_id=request.correlation_id,
            expiry_time=expiry_time,
        )

    # ── EvaluationContext ─────────────────────────────────────────────────────

    def create_evaluation_context(
        self,
        risk,               # ExecutionRisk (M1 domain object)
        request: "EvaluationRequest",
    ) -> EvaluationContext:
        """Build an ``EvaluationContext`` combining M1 risk identity and request data."""
        return make_evaluation_context(
            evaluation_id=risk.risk_id,
            risk_category=risk.risk_category,
            execution_id=risk.execution_id,
            order_id=risk.order_id,
            position_id=risk.position_id,
            portfolio_id=risk.portfolio_id,
            strategy_id=risk.strategy_id,
            decision_id=risk.decision_id,
            workflow_id=risk.workflow_id,
            correlation_id=risk.correlation_id,
            execution_snapshot=request.execution_snapshot,
            position_snapshot=request.position_snapshot,
            risk_limits=request.risk_limits,
            metadata=request.metadata,
        )
