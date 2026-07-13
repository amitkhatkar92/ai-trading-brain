"""iios/investment/strategy/evaluation/institutional_score.py
InstitutionalStrategyScore — comprehensive composite score for the evaluation engine.
Complements the existing StrategyScore (simple) without replacing it.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict

from iios.investment.strategy.evaluation.evaluation_grade import (
    EvaluationGrade, grade_from_score, grade_label
)
from iios.investment.strategy.evaluation.approval_engine import ApprovalStatus
from iios.investment.strategy.evaluation.performance_statistics import clamp


@dataclass
class InstitutionalStrategyScore:
    """
    Comprehensive score produced by StrategyEvaluationEngine.
    All dimension scores are in [0, 100].
    """

    score_id:         str   = field(default_factory=lambda: str(uuid.uuid4()))
    strategy_id:      str   = ""
    strategy_name:    str   = ""

    # Dimension scores (0–100)
    performance_score: float = 0.0
    risk_score:        float = 0.0
    robustness_score:  float = 0.0
    execution_score:   float = 0.0
    confidence_score:  float = 0.0

    # Composite
    overall_score:     float = 0.0

    # Grade and approval
    grade:             EvaluationGrade = EvaluationGrade.UNKNOWN
    grade_label:       str             = ""
    approval_status:   ApprovalStatus  = ApprovalStatus.PENDING

    evaluated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # ── sub-score computation ────────────────────────────────────────────────

    @classmethod
    def compute(
        cls,
        strategy_id: str,
        strategy_name: str,
        *,
        sharpe: float,
        ann_return: float,
        max_drawdown: float,
        win_rate: float,
        profit_factor: float,
        robustness: float,        # 0–1 from RobustnessEngine
        exec_efficiency: float,   # 0–1 from ExecutionQualityAnalyzer
        confidence: float,        # 0–100 from ConfidenceScoreCalculator
        approval_status: ApprovalStatus = ApprovalStatus.PENDING,
        weights: Dict[str, float] | None = None,
    ) -> "InstitutionalStrategyScore":
        from iios.investment.strategy.evaluation.performance_statistics import scale_metric

        perf = _performance_score(sharpe, ann_return, profit_factor)
        risk = _risk_score(max_drawdown, sharpe)
        rob = clamp(robustness * 100.0, 0.0, 100.0)
        exc = clamp(exec_efficiency * 100.0, 0.0, 100.0)
        conf = clamp(confidence, 0.0, 100.0)

        w = weights or {
            "performance":  0.30,
            "risk":         0.25,
            "robustness":   0.25,
            "execution":    0.10,
            "confidence":   0.10,
        }

        overall = (
            w.get("performance", 0.30) * perf
            + w.get("risk",        0.25) * risk
            + w.get("robustness",  0.25) * rob
            + w.get("execution",   0.10) * exc
            + w.get("confidence",  0.10) * conf
        )
        overall = clamp(overall, 0.0, 100.0)
        g = grade_from_score(overall)

        return cls(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            performance_score=round(perf, 2),
            risk_score=round(risk, 2),
            robustness_score=round(rob, 2),
            execution_score=round(exc, 2),
            confidence_score=round(conf, 2),
            overall_score=round(overall, 2),
            grade=g,
            grade_label=grade_label(g),
            approval_status=approval_status,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score_id":         self.score_id,
            "strategy_id":      self.strategy_id,
            "strategy_name":    self.strategy_name,
            "performance_score": self.performance_score,
            "risk_score":       self.risk_score,
            "robustness_score": self.robustness_score,
            "execution_score":  self.execution_score,
            "confidence_score": self.confidence_score,
            "overall_score":    self.overall_score,
            "grade":            self.grade.value,
            "grade_label":      self.grade_label,
            "approval_status":  self.approval_status.value,
            "evaluated_at":     self.evaluated_at.isoformat(),
        }


# ── scoring helpers ──────────────────────────────────────────────────────────

def _performance_score(
    sharpe: float, ann_return: float, profit_factor: float
) -> float:
    """Map performance metrics to [0, 100]."""
    from iios.investment.strategy.evaluation.performance_statistics import scale_metric
    sharpe_s = scale_metric(sharpe, low=-0.5, high=2.5)
    return_s = scale_metric(ann_return, low=-0.10, high=0.40)
    pf_s = scale_metric(min(profit_factor, 5.0), low=0.5, high=2.5)
    return 0.5 * sharpe_s + 0.3 * return_s + 0.2 * pf_s


def _risk_score(max_drawdown: float, sharpe: float) -> float:
    """Lower drawdown → higher risk score."""
    from iios.investment.strategy.evaluation.performance_statistics import scale_metric
    dd_s = scale_metric(max_drawdown, low=0.0, high=0.40, invert=True)
    sharpe_s = scale_metric(sharpe, low=-0.5, high=2.5)
    return 0.7 * dd_s + 0.3 * sharpe_s
