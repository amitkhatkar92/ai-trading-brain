"""iios/investment/company/earnings/earnings_quality.py
Core earnings quality evaluator. Combines cash quality, accruals, and
consistency signals into a single EarningsQualityScore.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.company.earnings.earnings_report import EarningsReport, EarningsQualityLabel
from iios.investment.company.earnings.earnings_snapshot import EarningsQualityScore
from iios.investment.company.earnings.earnings_statistics import (
    safe_mean, coefficient_of_variation, _clean,
)
from iios.investment.company.earnings.earnings_consistency import EarningsConsistencyChecker
from iios.investment.company.earnings.earnings_persistence import EarningsPersistenceAnalyzer


def _score_to_label(score: float) -> EarningsQualityLabel:
    if score >= 80:
        return EarningsQualityLabel.HIGH
    if score >= 65:
        return EarningsQualityLabel.ABOVE_AVERAGE
    if score >= 50:
        return EarningsQualityLabel.AVERAGE
    if score >= 35:
        return EarningsQualityLabel.BELOW_AVERAGE
    return EarningsQualityLabel.LOW


class EarningsQualityAnalyzer:
    """
    Evaluates earnings quality from a historical series of EarningsReports.

    Dimensions:
    1. Cash quality  — is net income backed by operating cash flow?
    2. Accruals       — low accruals ratio = real cash earnings
    3. Consistency    — stable margins across periods
    4. Persistence    — recurring, structural earnings
    """

    _W_CASH        = 0.30
    _W_ACCRUALS    = 0.25
    _W_CONSISTENCY = 0.25
    _W_PERSISTENCE = 0.20

    def __init__(self) -> None:
        self._consistency  = EarningsConsistencyChecker()
        self._persistence  = EarningsPersistenceAnalyzer()

    def analyze(self, history: List[EarningsReport]) -> EarningsQualityScore:
        q = EarningsQualityScore()
        if not history:
            q.label = EarningsQualityLabel.INSUFFICIENT
            return q

        # ── 1. Cash quality score ─────────────────────────────────────────────
        ocf_ratios = _clean([r.ocf_to_net_income for r in history])
        if ocf_ratios:
            avg_ocf = sum(ocf_ratios) / len(ocf_ratios)
            q.avg_ocf_to_ni = round(avg_ocf, 3)
            # Map ocf ratio to score: 1.0 → 100, 0.5 → 50, <0 → 0
            q.cash_quality_score = max(0.0, min(100.0, avg_ocf * 100.0))
        else:
            q.cash_quality_score = 50.0   # neutral when no data
            q.flags.append("no_ocf_data")

        # ── 2. Accruals score ─────────────────────────────────────────────────
        accruals = _clean([r.accruals_ratio for r in history])
        if accruals:
            avg_acc = sum(accruals) / len(accruals)
            q.avg_accruals_ratio = round(avg_acc, 4)
            # Sloan: accruals near 0 → 100; ±0.25 → 0
            raw = max(0.0, 1.0 - abs(avg_acc) / 0.25)
            q.accruals_score = raw * 100.0
        else:
            q.accruals_score = 50.0
            q.flags.append("no_accruals_data")

        # ── 3. Consistency score ──────────────────────────────────────────────
        cm = self._consistency.analyze(history)
        q.consistency_score = cm.score
        q.margin_cv         = cm.net_margin_cv
        q.flags.extend(cm.flags)

        # ── 4. Persistence score ──────────────────────────────────────────────
        pm = self._persistence.analyze(history)
        q.persistence_score = pm.score
        q.flags.extend(pm.flags)

        # ── Composite ─────────────────────────────────────────────────────────
        q.reliability_score = q.consistency_score   # same as consistency for now
        q.overall_score = (
            q.cash_quality_score  * self._W_CASH
            + q.accruals_score    * self._W_ACCRUALS
            + q.consistency_score * self._W_CONSISTENCY
            + q.persistence_score * self._W_PERSISTENCE
        )
        q.label = _score_to_label(q.overall_score)
        return q
