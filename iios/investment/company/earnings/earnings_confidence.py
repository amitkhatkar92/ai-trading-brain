"""iios/investment/company/earnings/earnings_confidence.py
Computes EarningsConfidenceScore based on data sufficiency and quality signals.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.earnings.earnings_report import EarningsReport
from iios.investment.company.earnings.earnings_snapshot import (
    EarningsConfidenceScore, EarningsQualityScore,
)


_MIN_PERIODS_LOW    = 2   # below this → insufficient
_MIN_PERIODS_MEDIUM = 5   # 5-9 → medium
_MIN_PERIODS_HIGH   = 10  # 10+ → high data sufficiency


def _label(score: float) -> str:
    if score >= 75:
        return "high"
    if score >= 50:
        return "medium"
    if score >= 25:
        return "low"
    return "insufficient"


class EarningsConfidenceAnalyzer:
    """
    Computes earnings confidence from data quantity and quality.

    Confidence is NOT an investment signal — it measures how much the
    engine trusts its own analysis of this company.
    """

    def analyze(
        self,
        history:     List[EarningsReport],
        quality:     Optional[EarningsQualityScore],
        revision_count: int = 0,
        restatement_count: int = 0,
    ) -> EarningsConfidenceScore:
        score = EarningsConfidenceScore()
        n = len(history)

        # ── Data sufficiency ──────────────────────────────────────────────────
        if n >= _MIN_PERIODS_HIGH:
            sufficiency = 100.0
        elif n >= _MIN_PERIODS_MEDIUM:
            sufficiency = 50.0 + 50.0 * (n - _MIN_PERIODS_MEDIUM) / (_MIN_PERIODS_HIGH - _MIN_PERIODS_MEDIUM)
        elif n >= _MIN_PERIODS_LOW:
            sufficiency = 25.0 + 25.0 * (n - _MIN_PERIODS_LOW) / (_MIN_PERIODS_MEDIUM - _MIN_PERIODS_LOW)
        else:
            sufficiency = 10.0 * n
        score.data_sufficiency = sufficiency

        if n < _MIN_PERIODS_LOW:
            score.factors.append("insufficient_history")
            score.score = sufficiency
            score.label = _label(score.score)
            return score

        # ── Quality confidence ─────────────────────────────────────────────────
        if quality is not None:
            score.quality_confidence = quality.overall_score
        else:
            score.quality_confidence = 50.0
            score.factors.append("no_quality_data")

        # ── Consistency confidence ─────────────────────────────────────────────
        # Based on missing fields in latest report
        if history:
            latest = history[-1]
            present = sum(1 for f in [
                latest.revenue, latest.net_income, latest.basic_eps,
                latest.gross_margin, latest.net_margin, latest.roe,
                latest.operating_cash_flow,
            ] if f is not None)
            score.consistency_confidence = min(100.0, present / 7 * 100.0)

        # ── Penalties ─────────────────────────────────────────────────────────
        if revision_count > 0:
            penalty = min(20.0, revision_count * 4.0)
            score.quality_confidence = max(0.0, score.quality_confidence - penalty)
            score.factors.append(f"revision_penalty:{revision_count}")
        if restatement_count > 0:
            penalty = min(25.0, restatement_count * 8.0)
            score.quality_confidence = max(0.0, score.quality_confidence - penalty)
            score.factors.append(f"restatement_penalty:{restatement_count}")

        # ── Composite ─────────────────────────────────────────────────────────
        score.score = (
            score.data_sufficiency       * 0.40
            + score.quality_confidence   * 0.35
            + score.consistency_confidence * 0.25
        )
        score.label = _label(score.score)
        return score
