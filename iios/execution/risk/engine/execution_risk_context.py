"""iios/execution/risk/engine/execution_risk_context.py
==================================================
EvaluationContext — immutable per-evaluation context passed to risk
rules during the EVALUATING phase.

Also defines ``make_evaluation_context`` — the canonical factory.

C6 Execution Intelligence — Phase 4, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from iios.execution.risk.lifecycle import RiskCategory


@dataclass(frozen=True)
class EvaluationContext:
    """
    Immutable context object passed to each registered risk rule.

    Contains all identifiers, snapshots, and risk limits a rule needs
    to perform its evaluation without any coupling to the engine internals.

    Risk rules MUST NOT mutate this object.
    """

    context_id:          str
    evaluation_id:       str            # M1 risk_id
    execution_id:        str
    order_id:            str
    position_id:         str
    portfolio_id:        str
    strategy_id:         str
    decision_id:         str
    workflow_id:         str
    risk_category:       RiskCategory
    correlation_id:      str
    created_at:          float
    execution_snapshot:  Dict[str, Any] = field(default_factory=dict, compare=False)
    position_snapshot:   Dict[str, Any] = field(default_factory=dict, compare=False)
    risk_limits:         Dict[str, Any] = field(default_factory=dict, compare=False)
    metadata:            Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def age_ms(self) -> float:
        """Context age in milliseconds."""
        return (time.time() - self.created_at) * 1_000.0

    @property
    def has_execution_snapshot(self) -> bool:
        """True if an execution snapshot was provided."""
        return bool(self.execution_snapshot)

    @property
    def has_position_snapshot(self) -> bool:
        """True if a position snapshot was provided."""
        return bool(self.position_snapshot)

    @property
    def has_risk_limits(self) -> bool:
        """True if risk limits were specified."""
        return bool(self.risk_limits)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "context_id":         self.context_id,
            "evaluation_id":      self.evaluation_id,
            "execution_id":       self.execution_id,
            "order_id":           self.order_id,
            "position_id":        self.position_id,
            "portfolio_id":       self.portfolio_id,
            "strategy_id":        self.strategy_id,
            "decision_id":        self.decision_id,
            "workflow_id":        self.workflow_id,
            "risk_category":      self.risk_category.value,
            "correlation_id":     self.correlation_id,
            "created_at":         self.created_at,
            "has_execution_snapshot": self.has_execution_snapshot,
            "has_position_snapshot":  self.has_position_snapshot,
            "has_risk_limits":    self.has_risk_limits,
            "metadata":           dict(self.metadata),
        }


def make_evaluation_context(
    evaluation_id:   str,
    risk_category:   RiskCategory,
    *,
    execution_id:    str = "",
    order_id:        str = "",
    position_id:     str = "",
    portfolio_id:    str = "",
    strategy_id:     str = "",
    decision_id:     str = "",
    workflow_id:     str = "",
    correlation_id:  str = "",
    execution_snapshot: Dict[str, Any] | None = None,
    position_snapshot:  Dict[str, Any] | None = None,
    risk_limits:        Dict[str, Any] | None = None,
    metadata:           Dict[str, Any] | None = None,
) -> EvaluationContext:
    """Create an ``EvaluationContext`` with a fresh UUID and timestamp."""
    return EvaluationContext(
        context_id=str(uuid.uuid4()),
        evaluation_id=evaluation_id,
        execution_id=execution_id,
        order_id=order_id,
        position_id=position_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        decision_id=decision_id,
        workflow_id=workflow_id,
        risk_category=risk_category,
        correlation_id=correlation_id,
        created_at=time.time(),
        execution_snapshot=execution_snapshot or {},
        position_snapshot=position_snapshot  or {},
        risk_limits=risk_limits              or {},
        metadata=metadata                    or {},
    )
