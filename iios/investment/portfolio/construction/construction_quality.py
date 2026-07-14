"""iios/investment/portfolio/construction/construction_quality.py

Construction quality assessment — aggregates signals from validators,
constraint engine, and portfolio statistics into a structured quality verdict.

The quality assessment is a read-only consumer: it never modifies a blueprint.
"""
from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.construction.construction_types import (
    HealthStatus,
    QualityDimension,
)


# ---------------------------------------------------------------------------
# DimensionScore
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DimensionScore:
    """Score [0, 1] on a single quality dimension with supporting detail."""

    dimension:   QualityDimension = QualityDimension.COMPLETENESS
    score:       float            = 0.0     # [0, 1]
    max_score:   float            = 1.0
    passed:      bool             = True
    message:     str              = ""
    details:     Dict[str, Any]   = field(default_factory=dict)

    @property
    def normalised(self) -> float:
        return self.score / self.max_score if self.max_score > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension":  self.dimension.value,
            "score":      round(self.score, 4),
            "max_score":  self.max_score,
            "normalised": round(self.normalised, 4),
            "passed":     self.passed,
            "message":    self.message,
            "details":    dict(self.details),
        }


# ---------------------------------------------------------------------------
# ConstructionQualityReport
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConstructionQualityReport:
    """
    Full quality report for a single construction run.

    Produced by ConstructionQualityAssessor.assess().
    """

    report_id:      str                       = field(default_factory=lambda: str(uuid.uuid4()))
    blueprint_id:   str                       = ""
    portfolio_id:   str                       = ""

    dimension_scores: Tuple[DimensionScore, ...] = field(default_factory=tuple)
    overall_score:  float                     = 0.0   # Weighted average [0, 1]
    health_status:  HealthStatus              = HealthStatus.UNKNOWN

    is_acceptable:  bool                      = False  # overall_score >= threshold
    threshold:      float                     = 0.60   # minimum acceptable score

    # Per-dimension breakdown
    completeness_score:          float        = 0.0
    consistency_score:           float        = 0.0
    constraint_compliance_score: float        = 0.0
    recommendation_alignment_score: float     = 0.0
    policy_compliance_score:     float        = 0.0
    diversity_score:             float        = 0.0
    readiness_score:             float        = 0.0

    assessed_at:    float                     = field(default_factory=time.time)
    metadata:       Dict[str, Any]            = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":                      self.report_id,
            "blueprint_id":                   self.blueprint_id,
            "portfolio_id":                   self.portfolio_id,
            "overall_score":                  round(self.overall_score, 4),
            "health_status":                  self.health_status.value,
            "is_acceptable":                  self.is_acceptable,
            "threshold":                      self.threshold,
            "completeness_score":             round(self.completeness_score, 4),
            "consistency_score":              round(self.consistency_score, 4),
            "constraint_compliance_score":    round(self.constraint_compliance_score, 4),
            "recommendation_alignment_score": round(self.recommendation_alignment_score, 4),
            "policy_compliance_score":        round(self.policy_compliance_score, 4),
            "diversity_score":                round(self.diversity_score, 4),
            "readiness_score":                round(self.readiness_score, 4),
            "dimension_scores":               [d.to_dict() for d in self.dimension_scores],
            "assessed_at":                    self.assessed_at,
            "metadata":                       dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# ConstructionQualityAssessor
# ---------------------------------------------------------------------------

class ConstructionQualityAssessor:
    """
    Aggregates signals from validators, constraint reports, and portfolio
    statistics into a single ConstructionQualityReport.

    Dimension weights (sum = 1.0):
      completeness             0.20
      consistency              0.15
      constraint_compliance    0.20
      recommendation_alignment 0.15
      policy_compliance        0.10
      diversity                0.10
      readiness                0.10
    """

    _WEIGHTS: Dict[str, float] = {
        QualityDimension.COMPLETENESS.value:              0.20,
        QualityDimension.CONSISTENCY.value:               0.15,
        QualityDimension.CONSTRAINT_COMPLIANCE.value:     0.20,
        QualityDimension.RECOMMENDATION_ALIGNMENT.value:  0.15,
        QualityDimension.POLICY_COMPLIANCE.value:         0.10,
        QualityDimension.DIVERSITY.value:                 0.10,
        QualityDimension.READINESS.value:                 0.10,
    }

    def __init__(self, acceptable_threshold: float = 0.60) -> None:
        self._threshold = acceptable_threshold

    def assess(
        self,
        blueprint: Any,
        portfolio_report: Any,
        construction_report: Any,
        constraint_report: Any,
        readiness_assessment: Any,
        *,
        stats: Optional[Any] = None,
    ) -> ConstructionQualityReport:
        """
        Produce a ConstructionQualityReport from pre-computed reports.

        All reports are accepted as Any to avoid circular imports — only
        attribute access is used.
        """
        dims = []

        # --- Completeness ---
        c_score = self._completeness_score(blueprint, portfolio_report)
        dims.append(c_score)

        # --- Consistency ---
        cs_score = self._consistency_score(construction_report)
        dims.append(cs_score)

        # --- Constraint compliance ---
        cc_score = self._constraint_compliance_score(constraint_report)
        dims.append(cc_score)

        # --- Recommendation alignment ---
        ra_score = self._recommendation_alignment_score(blueprint)
        dims.append(ra_score)

        # --- Policy compliance ---
        pc_score = self._policy_compliance_score(construction_report)
        dims.append(pc_score)

        # --- Diversity ---
        dv_score = self._diversity_score(blueprint, stats)
        dims.append(dv_score)

        # --- Readiness ---
        rd_score = self._readiness_score(readiness_assessment)
        dims.append(rd_score)

        # Weighted overall
        overall = sum(
            d.normalised * self._WEIGHTS.get(d.dimension.value, 0.0)
            for d in dims
        )
        overall = round(min(1.0, max(0.0, overall)), 4)

        health = self._health(overall)

        scores_by_dim = {d.dimension: d.normalised for d in dims}

        return ConstructionQualityReport(
            blueprint_id   = getattr(blueprint, "blueprint_id", ""),
            portfolio_id   = getattr(blueprint, "portfolio_id", ""),
            dimension_scores = tuple(dims),
            overall_score  = overall,
            health_status  = health,
            is_acceptable  = overall >= self._threshold,
            threshold      = self._threshold,
            completeness_score             = scores_by_dim.get(QualityDimension.COMPLETENESS, 0.0),
            consistency_score              = scores_by_dim.get(QualityDimension.CONSISTENCY, 0.0),
            constraint_compliance_score    = scores_by_dim.get(QualityDimension.CONSTRAINT_COMPLIANCE, 0.0),
            recommendation_alignment_score = scores_by_dim.get(QualityDimension.RECOMMENDATION_ALIGNMENT, 0.0),
            policy_compliance_score        = scores_by_dim.get(QualityDimension.POLICY_COMPLIANCE, 0.0),
            diversity_score                = scores_by_dim.get(QualityDimension.DIVERSITY, 0.0),
            readiness_score                = scores_by_dim.get(QualityDimension.READINESS, 0.0),
        )

    # ------------------------------------------------------------------
    # Per-dimension helpers
    # ------------------------------------------------------------------

    def _completeness_score(self, bp: Any, portfolio_report: Any) -> DimensionScore:
        passed_count  = getattr(portfolio_report, "passed", 0)
        total_count   = getattr(portfolio_report, "total", 1)
        total_slots   = getattr(bp, "total_slots", 0)

        completeness = (passed_count / total_count) if total_count > 0 else 0.0
        has_positions = 1.0 if total_slots > 0 else 0.0
        score = round((completeness + has_positions) / 2.0, 4)

        return DimensionScore(
            dimension = QualityDimension.COMPLETENESS,
            score     = score,
            passed    = score >= 0.5,
            message   = f"{total_slots} positions; {passed_count}/{total_count} portfolio checks passed",
            details   = {"total_slots": total_slots, "passed_checks": passed_count},
        )

    def _consistency_score(self, construction_report: Any) -> DimensionScore:
        passed = getattr(construction_report, "passed", 0)
        total  = getattr(construction_report, "total", 1)
        score  = round(passed / total, 4) if total > 0 else 0.0
        return DimensionScore(
            dimension = QualityDimension.CONSISTENCY,
            score     = score,
            passed    = score >= 0.7,
            message   = f"{passed}/{total} construction checks passed",
        )

    def _constraint_compliance_score(self, constraint_report: Any) -> DimensionScore:
        rate = getattr(constraint_report, "compliance_rate", 1.0)
        hard_violated = getattr(constraint_report, "hard_violated", 0)
        # Hard violations sharply penalise score
        penalty = 0.4 * hard_violated
        score = round(max(0.0, rate - penalty), 4)
        return DimensionScore(
            dimension = QualityDimension.CONSTRAINT_COMPLIANCE,
            score     = score,
            passed    = hard_violated == 0,
            message   = f"Compliance rate {rate:.1%}; {hard_violated} hard violation(s)",
            details   = {"hard_violated": hard_violated, "compliance_rate": rate},
        )

    def _recommendation_alignment_score(self, bp: Any) -> DimensionScore:
        slots = getattr(bp, "slots", ())
        if not slots:
            return DimensionScore(
                dimension=QualityDimension.RECOMMENDATION_ALIGNMENT,
                score=0.0, passed=False,
                message="No slots to assess",
            )
        # All slots must have a recommendation_id
        linked = sum(1 for s in slots if getattr(s, "recommendation_id", ""))
        score  = round(linked / len(slots), 4)
        return DimensionScore(
            dimension = QualityDimension.RECOMMENDATION_ALIGNMENT,
            score     = score,
            passed    = score >= 0.9,
            message   = f"{linked}/{len(slots)} slots have recommendation IDs",
        )

    def _policy_compliance_score(self, construction_report: Any) -> DimensionScore:
        # Re-use construction report findings in the POLICY_COMPLIANCE category
        findings = getattr(construction_report, "findings", ())
        from iios.investment.portfolio.construction.construction_types import ValidationCategory
        policy_findings = [
            f for f in findings
            if getattr(f, "category", None) == ValidationCategory.POLICY_COMPLIANCE
        ]
        if not policy_findings:
            return DimensionScore(
                dimension=QualityDimension.POLICY_COMPLIANCE,
                score=1.0, passed=True,
                message="No policy findings",
            )
        failed = sum(1 for f in policy_findings if getattr(f, "is_blocking", False))
        score  = round(1.0 - (failed / len(policy_findings)), 4)
        return DimensionScore(
            dimension = QualityDimension.POLICY_COMPLIANCE,
            score     = score,
            passed    = failed == 0,
            message   = f"{failed}/{len(policy_findings)} policy checks failed",
        )

    def _diversity_score(self, bp: Any, stats: Optional[Any]) -> DimensionScore:
        slots = getattr(bp, "slots", ())
        if not slots:
            return DimensionScore(
                dimension=QualityDimension.DIVERSITY,
                score=0.0, passed=False,
                message="No slots",
            )
        n = len(slots)
        # Effective N from HHI if stats available
        if stats and hasattr(stats, "concentration"):
            eff_n = getattr(stats.concentration, "effective_n", n)
        else:
            # Estimate from weight distribution
            weights = [abs(getattr(s, "target_weight", 1.0 / n)) for s in slots]
            total = sum(weights) or 1.0
            norm = [w / total for w in weights]
            hhi  = sum(w ** 2 for w in norm)
            eff_n = 1.0 / hhi if hhi > 0 else n

        # Score: effective_n / actual_n (higher diversity = closer to 1.0)
        score = round(min(1.0, eff_n / max(n, 1)), 4)
        return DimensionScore(
            dimension = QualityDimension.DIVERSITY,
            score     = score,
            passed    = score >= 0.4,
            message   = f"Effective N {eff_n:.1f} vs {n} total slots",
            details   = {"effective_n": round(eff_n, 2), "total_slots": n},
        )

    def _readiness_score(self, readiness: Any) -> DimensionScore:
        is_ready = getattr(readiness, "is_ready", False)
        blocking = list(getattr(readiness, "blocking_reasons", []))
        score    = 1.0 if is_ready else max(0.0, 1.0 - 0.3 * len(blocking))
        return DimensionScore(
            dimension = QualityDimension.READINESS,
            score     = round(score, 4),
            passed    = is_ready,
            message   = "Ready" if is_ready else f"{len(blocking)} blocking issue(s)",
            details   = {"blocking_reasons": blocking[:5]},
        )

    @staticmethod
    def _health(score: float) -> HealthStatus:
        if score >= 0.75:
            return HealthStatus.HEALTHY
        if score >= 0.50:
            return HealthStatus.DEGRADED
        return HealthStatus.UNHEALTHY
