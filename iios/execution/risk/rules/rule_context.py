"""iios/execution/risk/rules/rule_context.py
==================================================
RuleContext — rich, immutable evaluation context passed to every
risk rule during evaluation.

Also provides ``make_rule_context`` (from scratch) and
``make_rule_context_from_engine`` (from M2 objects).

C6 Execution Intelligence — Phase 4, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .rule_category import RuleCategory


@dataclass(frozen=True)
class RuleContext:
    """
    Immutable context passed to each rule's ``evaluate()`` call.

    Rules MUST NOT mutate this object.
    Rules MUST NOT perform IO or broker communication.
    """

    context_id:    str
    evaluation_id: str
    execution_id:  str
    order_id:      str
    position_id:   str
    portfolio_id:  str
    strategy_id:   str
    decision_id:   str
    workflow_id:   str
    risk_category: Optional[RuleCategory]
    correlation_id: str
    created_at:    float

    # ── External data snapshots ───────────────────────────────────────────────
    execution_snapshot: Dict[str, Any] = field(default_factory=dict, compare=False)
    position_snapshot:  Dict[str, Any] = field(default_factory=dict, compare=False)
    risk_limits:        Dict[str, Any] = field(default_factory=dict, compare=False)
    session_info:       Dict[str, Any] = field(default_factory=dict, compare=False)
    system_info:        Dict[str, Any] = field(default_factory=dict, compare=False)
    metadata:           Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def age_ms(self) -> float:
        return (time.time() - self.created_at) * 1_000.0

    @property
    def has_execution_snapshot(self) -> bool:
        return bool(self.execution_snapshot)

    @property
    def has_position_snapshot(self) -> bool:
        return bool(self.position_snapshot)

    @property
    def has_risk_limits(self) -> bool:
        return bool(self.risk_limits)

    @property
    def session_valid(self) -> bool:
        """True if session_info indicates a valid trading session."""
        return bool(self.session_info.get("session_valid", True))

    @property
    def system_healthy(self) -> bool:
        """True if system_info indicates all systems operational."""
        return bool(self.system_info.get("system_healthy", True))

    @property
    def emergency_stop_active(self) -> bool:
        """True if an emergency stop has been activated."""
        return bool(
            self.risk_limits.get("emergency_stop_active", False)
            or self.system_info.get("emergency_stop", False)
        )

    def get_limit(self, key: str, default: Any) -> Any:
        """Retrieve a risk limit value, falling back to *default*."""
        return self.risk_limits.get(key, default)

    def get_exec(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from the execution snapshot."""
        return self.execution_snapshot.get(key, default)

    def get_pos(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from the position snapshot."""
        return self.position_snapshot.get(key, default)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":    self.context_id,
            "evaluation_id": self.evaluation_id,
            "execution_id":  self.execution_id,
            "order_id":      self.order_id,
            "portfolio_id":  self.portfolio_id,
            "strategy_id":   self.strategy_id,
            "risk_category": self.risk_category.value if self.risk_category else None,
            "created_at":    self.created_at,
            "age_ms":        self.age_ms,
            "has_execution_snapshot": self.has_execution_snapshot,
            "has_position_snapshot":  self.has_position_snapshot,
        }


# ── Factory helpers ───────────────────────────────────────────────────────────

def make_rule_context(
    *,
    evaluation_id:      str = "",
    execution_id:       str = "",
    order_id:           str = "",
    position_id:        str = "",
    portfolio_id:       str = "",
    strategy_id:        str = "",
    decision_id:        str = "",
    workflow_id:        str = "",
    risk_category:      Optional[RuleCategory] = None,
    correlation_id:     str = "",
    execution_snapshot: Dict[str, Any] | None = None,
    position_snapshot:  Dict[str, Any] | None = None,
    risk_limits:        Dict[str, Any] | None = None,
    session_info:       Dict[str, Any] | None = None,
    system_info:        Dict[str, Any] | None = None,
    metadata:           Dict[str, Any] | None = None,
) -> RuleContext:
    """Create a ``RuleContext`` with a fresh context_id and timestamp."""
    return RuleContext(
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
        session_info=session_info            or {},
        system_info=system_info              or {},
        metadata=metadata                    or {},
    )


def make_rule_context_from_engine(request: Any, eval_context: Any) -> RuleContext:
    """
    Build a ``RuleContext`` from M2 ``EvaluationRequest`` and
    ``EvaluationContext`` objects.

    Used by ``RuleEngineAdapter`` when bridging M3 rules into the
    M2 RiskEngine.
    """
    from .rule_category import RuleCategory as RC
    from iios.execution.risk.lifecycle import RiskCategory

    # Map M1 RiskCategory → M3 RuleCategory (best-effort)
    _risk_to_rule: dict[RiskCategory, RC] = {
        RiskCategory.EXPOSURE:      RC.EXPOSURE,
        RiskCategory.MARGIN:        RC.MARGIN,
        RiskCategory.LIQUIDITY:     RC.LIQUIDITY,
        RiskCategory.CONCENTRATION: RC.POSITION,
        RiskCategory.ORDER_SIZE:    RC.EXECUTION,
        RiskCategory.PRICE:         RC.MARKET,
        RiskCategory.EXECUTION:     RC.EXECUTION,
        RiskCategory.COMPLIANCE:    RC.COMPLIANCE,
        RiskCategory.OPERATIONAL:   RC.OPERATIONAL,
    }

    rule_cat = None
    if hasattr(eval_context, "risk_category") and eval_context.risk_category is not None:
        rule_cat = _risk_to_rule.get(eval_context.risk_category)
    elif hasattr(request, "risk_category") and request.risk_category is not None:
        rule_cat = _risk_to_rule.get(request.risk_category)

    return RuleContext(
        context_id=str(uuid.uuid4()),
        evaluation_id=getattr(eval_context, "evaluation_id", "") or getattr(request, "request_id", ""),
        execution_id=getattr(eval_context, "execution_id", "") or getattr(request, "execution_id", ""),
        order_id=getattr(eval_context, "order_id", "") or getattr(request, "order_id", ""),
        position_id=getattr(eval_context, "position_id", "") or getattr(request, "position_id", ""),
        portfolio_id=getattr(eval_context, "portfolio_id", "") or getattr(request, "portfolio_id", ""),
        strategy_id=getattr(eval_context, "strategy_id", "") or getattr(request, "strategy_id", ""),
        decision_id=getattr(eval_context, "decision_id", "") or getattr(request, "decision_id", ""),
        workflow_id=getattr(eval_context, "workflow_id", "") or getattr(request, "workflow_id", ""),
        risk_category=rule_cat,
        correlation_id=getattr(eval_context, "correlation_id", "") or getattr(request, "correlation_id", ""),
        created_at=time.time(),
        execution_snapshot=getattr(eval_context, "execution_snapshot", None)
                           or getattr(request, "execution_snapshot", None) or {},
        position_snapshot=getattr(eval_context, "position_snapshot", None)
                          or getattr(request, "position_snapshot", None) or {},
        risk_limits=getattr(eval_context, "risk_limits", None)
                    or getattr(request, "risk_limits", None) or {},
        metadata=getattr(eval_context, "metadata", None)
                 or getattr(request, "metadata", None) or {},
    )
