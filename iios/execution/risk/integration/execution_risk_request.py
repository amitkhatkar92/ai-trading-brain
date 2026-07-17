"""iios/execution/risk/integration/execution_risk_request.py
==================================================
ExecutionRiskRequest — the ONLY input type accepted by the integration
layer's public API.

C6 Execution Intelligence — Phase 4, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict

from .constants import DEFAULT_TIMEOUT_MS, EvaluationMode
from .execution_risk_context import ExecutionContext, make_execution_context


@dataclass(frozen=True)
class ExecutionRiskRequest:
    """
    Immutable input submitted to the Execution Risk Integration Engine.

    Wraps an ExecutionContext with evaluation metadata.
    Created by IntegrationRequestFactory or make_execution_risk_request().
    """

    request_id:         str
    execution_context:  ExecutionContext
    evaluation_mode:    EvaluationMode = EvaluationMode.STANDARD
    timeout_ms:         float          = DEFAULT_TIMEOUT_MS
    requested_at:       float          = field(default_factory=time.time)
    requested_by:       str            = ""
    correlation_id:     str            = ""
    risk_category:      str            = "EXECUTION"
    metadata:           Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def execution_id(self) -> str:
        return self.execution_context.execution_id

    @property
    def order_id(self) -> str:
        return self.execution_context.order_id

    @property
    def portfolio_id(self) -> str:
        return self.execution_context.portfolio_id

    @property
    def strategy_id(self) -> str:
        return self.execution_context.strategy_id

    @property
    def age_ms(self) -> float:
        return (time.time() - self.requested_at) * 1_000.0

    @property
    def is_expired(self) -> bool:
        if self.timeout_ms <= 0:
            return False
        return self.age_ms > self.timeout_ms

    @property
    def effective_correlation_id(self) -> str:
        return self.correlation_id or self.execution_context.correlation_id

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":       self.request_id,
            "execution_id":     self.execution_id,
            "order_id":         self.order_id,
            "portfolio_id":     self.portfolio_id,
            "strategy_id":      self.strategy_id,
            "evaluation_mode":  self.evaluation_mode.value,
            "timeout_ms":       self.timeout_ms,
            "requested_at":     self.requested_at,
            "requested_by":     self.requested_by,
            "correlation_id":   self.correlation_id,
            "risk_category":    self.risk_category,
            "is_expired":       self.is_expired,
            "age_ms":           self.age_ms,
            "context":          self.execution_context.to_dict(),
            "metadata":         dict(self.metadata),
        }


# ── Factory ───────────────────────────────────────────────────────────────────

def make_execution_risk_request(
    execution_context: ExecutionContext,
    *,
    evaluation_mode: EvaluationMode = EvaluationMode.STANDARD,
    timeout_ms:      float          = DEFAULT_TIMEOUT_MS,
    requested_by:    str            = "",
    correlation_id:  str            = "",
    risk_category:   str            = "EXECUTION",
    metadata:        Dict[str, Any] | None = None,
) -> ExecutionRiskRequest:
    return ExecutionRiskRequest(
        request_id=str(uuid.uuid4()),
        execution_context=execution_context,
        evaluation_mode=evaluation_mode,
        timeout_ms=timeout_ms,
        requested_by=requested_by,
        correlation_id=correlation_id,
        risk_category=risk_category,
        metadata=metadata or {},
    )
