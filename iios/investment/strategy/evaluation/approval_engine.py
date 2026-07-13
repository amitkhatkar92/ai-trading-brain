"""iios/investment/strategy/evaluation/approval_engine.py
Approval decision: APPROVED, CONDITIONAL, or REJECTED.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class ApprovalStatus(str, Enum):
    APPROVED    = "approved"
    CONDITIONAL = "conditional"
    REJECTED    = "rejected"
    PENDING     = "pending"


@dataclass(frozen=True)
class ApprovalCriteria:
    """Configurable thresholds for strategy approval."""
    min_sharpe:          float = 0.80
    min_win_rate:        float = 0.45
    max_drawdown:        float = 0.20
    min_profit_factor:   float = 1.20
    min_trades:          int   = 30
    min_confidence:      float = 40.0  # confidence score (0–100)
    min_overall_score:   float = 60.0  # approved threshold
    conditional_score:   float = 50.0  # conditional threshold


@dataclass(frozen=True)
class ApprovalResult:
    status:     ApprovalStatus
    reasons:    List[str]          # why this status was reached
    violations: List[str]          # criteria that were violated (REJECTED only)
    conditions: List[str]          # conditions for conditional approval
    score:      float              # the overall score used for decision

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status":     self.status.value,
            "reasons":    self.reasons,
            "violations": self.violations,
            "conditions": self.conditions,
            "score":      self.score,
        }


class ApprovalEngine:
    """Determines strategy approval status from metrics and score."""

    def __init__(self, criteria: ApprovalCriteria = ApprovalCriteria()) -> None:
        self._c = criteria

    def decide(
        self,
        *,
        overall_score: float,
        sharpe: float,
        win_rate: float,
        max_drawdown: float,
        profit_factor: float,
        n_trades: int,
        confidence_score: float,
    ) -> ApprovalResult:
        violations: List[str] = []
        conditions: List[str] = []
        reasons: List[str] = []
        c = self._c

        # Hard violations (any one causes rejection regardless of score)
        if max_drawdown > c.max_drawdown:
            violations.append(
                f"Max drawdown {max_drawdown:.1%} > limit {c.max_drawdown:.1%}"
            )
        if n_trades < c.min_trades:
            violations.append(
                f"Only {n_trades} trades; need ≥ {c.min_trades}"
            )
        if sharpe < 0.0:
            violations.append(f"Negative Sharpe ratio ({sharpe:.2f})")

        # Conditional criteria (warn but don't block)
        if sharpe < c.min_sharpe:
            conditions.append(f"Sharpe {sharpe:.2f} below target {c.min_sharpe}")
        if win_rate < c.min_win_rate:
            conditions.append(
                f"Win rate {win_rate:.1%} below target {c.min_win_rate:.1%}"
            )
        if profit_factor < c.min_profit_factor:
            conditions.append(
                f"Profit factor {profit_factor:.2f} below target {c.min_profit_factor}"
            )
        if confidence_score < c.min_confidence:
            conditions.append(
                f"Confidence {confidence_score:.0f} below threshold {c.min_confidence:.0f}"
            )

        # Decision
        if violations:
            status = ApprovalStatus.REJECTED
            reasons = [f"REJECTED: {v}" for v in violations]
        elif overall_score >= c.min_overall_score and not conditions:
            status = ApprovalStatus.APPROVED
            reasons = [f"Score {overall_score:.1f} ≥ {c.min_overall_score:.0f} with no conditional flags"]
        elif overall_score >= c.conditional_score:
            status = ApprovalStatus.CONDITIONAL
            reasons = [
                f"Score {overall_score:.1f} between conditional ({c.conditional_score:.0f}) and approved ({c.min_overall_score:.0f}) thresholds",
                "Conditional criteria flagged: see conditions list",
            ]
        else:
            status = ApprovalStatus.REJECTED
            reasons = [f"Overall score {overall_score:.1f} below minimum {c.conditional_score:.0f}"]

        return ApprovalResult(
            status=status,
            reasons=reasons,
            violations=violations,
            conditions=conditions,
            score=overall_score,
        )
