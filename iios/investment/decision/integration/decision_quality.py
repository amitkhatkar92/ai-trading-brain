"""iios/investment/decision/integration/decision_quality.py
DecisionQualityEvaluator — computes overall Decision Intelligence quality score
and calculates the composite Overall Intelligence Score.
"""
from __future__ import annotations

import math

from iios.investment.decision.integration.aggregation_state import _AggregationStateSnapshot
from iios.investment.decision.integration.conflict_engine import ConflictReport
from iios.investment.decision.integration.integration_constants import (
    QUALITY_WEIGHT_AUDIT,
    QUALITY_WEIGHT_COMPLETENESS,
    QUALITY_WEIGHT_CONFIDENCE,
    QUALITY_WEIGHT_CONSISTENCY,
    QUALITY_WEIGHT_FRESHNESS,
)
from iios.investment.decision.integration.validation_report import (
    ValidationReport,
    ValidationStatus,
)


class DecisionQualityEvaluator:
    """
    Computes a 0–100 quality score and a composite Overall Intelligence Score.
    Neither score is a Buy/Sell recommendation — they measure process quality.
    """

    def evaluate(
        self,
        snap:               _AggregationStateSnapshot,
        validation_report:  ValidationReport,
        conflict_report:    ConflictReport,
        integration_confidence: float,
    ) -> float:
        """Return the overall quality score (0–100)."""
        completeness  = self._completeness_score(snap)
        consistency   = self._consistency_score(validation_report)
        freshness     = self._freshness_score(snap)
        conf_score    = integration_confidence
        audit_score   = self._audit_readiness_score(snap, validation_report, conflict_report)

        raw = (
            completeness * QUALITY_WEIGHT_COMPLETENESS
            + consistency  * QUALITY_WEIGHT_CONSISTENCY
            + freshness    * QUALITY_WEIGHT_FRESHNESS
            + conf_score   * QUALITY_WEIGHT_CONFIDENCE
            + audit_score  * QUALITY_WEIGHT_AUDIT
        )
        return max(0.0, min(100.0, raw))

    def overall_intelligence_score(
        self,
        snap:               _AggregationStateSnapshot,
        integration_confidence: float,
        quality_score:      float,
        conflict_report:    ConflictReport,
    ) -> float:
        """
        Composite 0–100 score that measures the overall intelligence value of
        this decision snapshot.  Not a recommendation.
        """
        # Base: average of individual component quality signals
        signals = []

        if snap.evidence is not None:
            signals.append(snap.evidence.quality_score * snap.evidence.coverage_fraction)

        if snap.reasoning is not None:
            # quality_score is a ReasoningQualityScore; extract a float
            rq = snap.reasoning.quality_score
            rq_val = getattr(rq, "overall_score", None)
            if rq_val is None:
                rq_val = getattr(rq, "score", 70.0)
            signals.append(float(rq_val))

        if snap.confidence is not None:
            signals.append(snap.confidence.overall_confidence)

        if snap.risk is not None:
            signals.append(100.0 - snap.risk.overall_risk)

        if snap.explanation is not None:
            signals.append(snap.explanation.explainability_score)

        if snap.committee is not None:
            signals.append(getattr(snap.committee, "committee_score", 60.0))

        base = (sum(signals) / len(signals)) if signals else 0.0

        # Blend with integration quality
        blended = base * 0.60 + quality_score * 0.40

        # Penalty for unresolved critical conflicts
        if conflict_report.critical_count > 0:
            penalty = min(30.0, conflict_report.critical_count * 10.0)
            blended = max(0.0, blended - penalty)

        return max(0.0, min(100.0, blended))

    # ── Private subscores ─────────────────────────────────────────────────────

    def _completeness_score(self, snap: _AggregationStateSnapshot) -> float:
        return snap.completeness * 100.0

    def _consistency_score(self, vr: ValidationReport) -> float:
        n = len(vr.checks)
        if n == 0:
            return 50.0  # no checks = unknown
        n_valid   = vr.valid_count
        n_warning = vr.warning_count
        n_invalid = vr.invalid_count
        score = (n_valid * 100.0 + n_warning * 60.0 + n_invalid * 0.0) / n
        return max(0.0, min(100.0, score))

    def _freshness_score(self, snap: _AggregationStateSnapshot) -> float:
        from datetime import timezone
        import datetime as _dt
        from iios.investment.decision.integration.integration_constants import (
            COMPONENT_MAX_AGE_SECONDS, ComponentId,
        )
        now    = _dt.datetime.now(timezone.utc)
        scores = []
        for cid in ComponentId:
            val = getattr(snap, cid.value, None)
            if val is None:
                continue
            ts = getattr(val, "created_at", None)
            if ts is None:
                continue
            age_s  = (now - ts).total_seconds()
            fresh  = max(0.0, 1.0 - (age_s / COMPONENT_MAX_AGE_SECONDS))
            scores.append(fresh * 100.0)
        return (sum(scores) / len(scores)) if scores else 50.0

    def _audit_readiness_score(
        self,
        snap: _AggregationStateSnapshot,
        vr:   ValidationReport,
        cr:   ConflictReport,
    ) -> float:
        # Explanation presence is the primary audit readiness signal
        explanation_bonus = 100.0 if snap.explanation is not None else 0.0

        # Unresolved critical conflicts hurt audit readiness
        crit_penalty = min(50.0, cr.critical_count * 15.0)

        # Invalid validation checks hurt
        invalid_penalty = min(30.0, vr.invalid_count * 10.0)

        score = explanation_bonus - crit_penalty - invalid_penalty
        return max(0.0, min(100.0, score))
