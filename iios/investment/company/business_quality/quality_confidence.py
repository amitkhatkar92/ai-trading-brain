"""iios/investment/company/business_quality/quality_confidence.py
Confidence scoring for business quality assessment.
"""
from __future__ import annotations

from iios.investment.company.business_quality.assessment_context import AssessmentContext
from iios.investment.company.business_quality.business_quality_snapshot import (
    QualityConfidenceScore, BusinessQualitySnapshot,
)
from iios.investment.company.business_quality.quality_statistics import clamp


class QualityConfidenceAnalyzer:
    """
    Computes confidence in the business quality assessment based on:
    - Data sufficiency (history depth)
    - Signal coverage (fraction of fields populated)
    - Signal consistency (moat signals agree with operational signals)
    """

    def analyze(
        self,
        ctx:      AssessmentContext,
        snapshot: BusinessQualitySnapshot,
    ) -> QualityConfidenceScore:
        c = QualityConfidenceScore()

        # ── Data sufficiency ───────────────────────────────────────────────────
        history_depth = 0
        if ctx.earnings_snapshot is not None:
            try:
                history_depth = ctx.earnings_snapshot.history_depth
            except Exception:
                pass

        if history_depth == 0:
            c.data_sufficiency = 10.0
        elif history_depth < 3:
            c.data_sufficiency = 30.0
        elif history_depth < 5:
            c.data_sufficiency = 60.0
        elif history_depth < 10:
            c.data_sufficiency = 80.0
        else:
            c.data_sufficiency = 100.0

        # ── Signal quality ─────────────────────────────────────────────────────
        # Agreement between moat score and operational score
        moat_score = snapshot.moat.moat_score
        ops_score  = snapshot.operational.operational_quality_score
        divergence = abs(moat_score - ops_score)
        c.signal_quality = clamp(100.0 - divergence * 0.5)

        # ── Coverage ───────────────────────────────────────────────────────────
        checks = [
            snapshot.business_model.gross_margin_level is not None,
            snapshot.business_model.capex_pct_revenue  is not None,
            snapshot.moat.avg_roic                     is not None,
            snapshot.moat.avg_gross_margin             is not None,
            snapshot.operational.capital_efficiency.current_roic is not None,
            snapshot.resilience.business_risk.debt_to_equity     is not None,
            snapshot.resilience.stress_resilience.avg_fcf_margin is not None,
        ]
        c.coverage_pct = sum(checks) / len(checks)

        # ── Composite confidence ───────────────────────────────────────────────
        c.score = clamp(
            c.data_sufficiency * 0.40
            + c.signal_quality * 0.35
            + c.coverage_pct * 100.0 * 0.25
        )

        c.label = self._label(c.score, history_depth)

        c.factors = [
            f"history_depth:{history_depth}",
            f"coverage:{c.coverage_pct:.0%}",
        ]
        if ctx.earnings_snapshot is None:
            c.factors.append("no_earnings_snapshot")
        if ctx.financial_snapshot is None:
            c.factors.append("no_financial_snapshot")

        return c

    @staticmethod
    def _label(score: float, depth: int) -> str:
        if depth < 2:
            return "insufficient"
        if score >= 70:
            return "high"
        if score >= 50:
            return "medium"
        if score >= 30:
            return "low"
        return "insufficient"
