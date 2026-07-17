"""iios/execution/risk/engine/execution_risk_result.py
==================================================
EvaluationResult — unified result returned by every Execution Risk
Engine operation.

C6 Execution Intelligence — Phase 4, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import OperationType, RuleOutcome
from .execution_risk_request import RuleResult


@dataclass(frozen=True)
class EvaluationResult:
    """
    Immutable result returned by every Execution Risk Engine operation.

    The result is the single source of truth for whether an operation
    succeeded, which evaluation was affected, the aggregated outcome, and
    what each individual rule returned.
    """

    result_id:      str
    request_id:     str
    operation_type: OperationType
    succeeded:      bool
    evaluation_id:  str                       # M1 risk_id
    outcome:        Optional[RuleOutcome]     # aggregated rule outcome
    rule_results:   Tuple[RuleResult, ...]    # one per executed rule
    elapsed_ms:     float
    error_code:     str
    error_message:  str
    rule_count:     int
    completed_at:   float = field(default_factory=time.time)
    data:           Dict[str, Any] = field(default_factory=dict, compare=False)
    metadata:       Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def failed(self) -> bool:
        return not self.succeeded

    @property
    def is_blocked(self) -> bool:
        return self.outcome == RuleOutcome.BLOCKED

    @property
    def is_passed(self) -> bool:
        return self.outcome in {RuleOutcome.PASSED, RuleOutcome.WARNING}

    @property
    def has_warnings(self) -> bool:
        return any(r.warned for r in self.rule_results)

    @property
    def blocked_rules(self) -> List[RuleResult]:
        return [r for r in self.rule_results if r.blocked]

    @property
    def warning_rules(self) -> List[RuleResult]:
        return [r for r in self.rule_results if r.warned]

    @property
    def errored_rules(self) -> List[RuleResult]:
        return [r for r in self.rule_results if r.errored]

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id":      self.result_id,
            "request_id":     self.request_id,
            "operation_type": self.operation_type.value,
            "succeeded":      self.succeeded,
            "evaluation_id":  self.evaluation_id,
            "outcome":        self.outcome.value if self.outcome is not None else None,
            "rule_results":   [r.to_dict() for r in self.rule_results],
            "elapsed_ms":     self.elapsed_ms,
            "error_code":     self.error_code,
            "error_message":  self.error_message,
            "rule_count":     self.rule_count,
            "completed_at":   self.completed_at,
            "is_blocked":     self.is_blocked,
            "is_passed":      self.is_passed,
            "data":           dict(self.data),
            "metadata":       dict(self.metadata),
        }


# ── Factory helpers ───────────────────────────────────────────────────────────

def make_success_result(
    request_id:     str,
    operation_type: OperationType,
    evaluation_id:  str,
    outcome:        RuleOutcome,
    elapsed_ms:     float,
    *,
    rule_results: Tuple[RuleResult, ...] = (),
    data:         Dict[str, Any] | None  = None,
    metadata:     Dict[str, Any] | None  = None,
) -> EvaluationResult:
    return EvaluationResult(
        result_id=str(uuid.uuid4()),
        request_id=request_id,
        operation_type=operation_type,
        succeeded=True,
        evaluation_id=evaluation_id,
        outcome=outcome,
        rule_results=rule_results,
        elapsed_ms=elapsed_ms,
        error_code="",
        error_message="",
        rule_count=len(rule_results),
        data=data or {},
        metadata=metadata or {},
    )


def make_failure_result(
    request_id:     str,
    operation_type: OperationType,
    error_code:     str,
    error_message:  str,
    elapsed_ms:     float,
    *,
    evaluation_id: str                    = "",
    rule_results:  Tuple[RuleResult, ...] = (),
    metadata:      Dict[str, Any] | None  = None,
) -> EvaluationResult:
    return EvaluationResult(
        result_id=str(uuid.uuid4()),
        request_id=request_id,
        operation_type=operation_type,
        succeeded=False,
        evaluation_id=evaluation_id,
        outcome=None,
        rule_results=rule_results,
        elapsed_ms=elapsed_ms,
        error_code=error_code,
        error_message=error_message,
        rule_count=len(rule_results),
        metadata=metadata or {},
    )
