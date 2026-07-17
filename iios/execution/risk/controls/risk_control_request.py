"""iios/execution/risk/controls/risk_control_request.py
==================================================
ControlRequest — the input to the Execution Risk Controls Framework.

C6 Execution Intelligence — Phase 4, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import PolicyType
from .risk_control_context import ControlContext, make_control_context


@dataclass(frozen=True)
class ControlRequest:
    """
    Immutable input submitted to the RiskControlEngine.

    Carries M3 rule results and a ControlContext.
    The engine applies the selected policy to derive a RiskControlDecision.
    """

    request_id:    str
    evaluation_id: str
    execution_id:  str
    order_id:      str
    portfolio_id:  str
    strategy_id:   str
    correlation_id: str
    created_at:    float

    # ── Primary inputs ────────────────────────────────────────────────────────
    # rule_results is a tuple of M3 RuleResult objects.
    # Typed as Any to avoid a hard import of M3 at module level.
    rule_results:   Tuple[Any, ...]
    context:        ControlContext

    # ── Optional M2 result ────────────────────────────────────────────────────
    # Callers may supply the M2 EvaluationResult for additional context.
    # The control engine never re-evaluates risk from it.
    evaluation_result: Optional[Any] = field(default=None, compare=False)

    # ── Policy override ───────────────────────────────────────────────────────
    policy_type: PolicyType = PolicyType.HIGHEST_SEVERITY

    metadata: Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def age_ms(self) -> float:
        return (time.time() - self.created_at) * 1_000.0

    @property
    def rule_count(self) -> int:
        return len(self.rule_results)

    @property
    def has_evaluation_result(self) -> bool:
        return self.evaluation_result is not None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":    self.request_id,
            "evaluation_id": self.evaluation_id,
            "execution_id":  self.execution_id,
            "order_id":      self.order_id,
            "portfolio_id":  self.portfolio_id,
            "strategy_id":   self.strategy_id,
            "correlation_id": self.correlation_id,
            "created_at":    self.created_at,
            "rule_count":    self.rule_count,
            "policy_type":   self.policy_type.value,
        }


# ── Factory ───────────────────────────────────────────────────────────────────

def make_control_request(
    rule_results,
    context: ControlContext,
    *,
    evaluation_id:     str = "",
    execution_id:      str = "",
    order_id:          str = "",
    portfolio_id:      str = "",
    strategy_id:       str = "",
    correlation_id:    str = "",
    policy_type:       PolicyType = PolicyType.HIGHEST_SEVERITY,
    evaluation_result: Any = None,
    metadata:          Dict[str, Any] | None = None,
) -> ControlRequest:
    return ControlRequest(
        request_id=str(uuid.uuid4()),
        evaluation_id=evaluation_id,
        execution_id=execution_id,
        order_id=order_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        correlation_id=correlation_id,
        created_at=time.time(),
        rule_results=tuple(rule_results),
        context=context,
        evaluation_result=evaluation_result,
        policy_type=policy_type,
        metadata=metadata or {},
    )
