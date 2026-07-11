"""iios/investment/market/integration/market_quality.py
Computes the multi-dimensional QualityScore from aggregation/validation state.

Dimensions:
  - completeness  (30%): fraction of expected engines that provided data
  - consistency   (30%): 100 minus weighted conflict penalty
  - freshness     (20%): age of oldest payload vs max_stale_bars
  - reliability   (20%): validation pass rate + error rate penalty
"""
from __future__ import annotations

from typing import List

from iios.investment.market.integration.aggregation_state import AggregationState
from iios.investment.market.integration.aggregation_engine import KNOWN_ENGINES
from iios.investment.market.integration.models import (
    ConflictSeverity,
    ConflictSummary,
    QualityDimension,
    QualityScore,
    ValidationReport,
    ValidationStatus,
)

_CONFLICT_PENALTY = {
    ConflictSeverity.LOW:      3.0,
    ConflictSeverity.MEDIUM:   8.0,
    ConflictSeverity.HIGH:     18.0,
    ConflictSeverity.CRITICAL: 35.0,
}

_W_COMPLETENESS = 0.30
_W_CONSISTENCY  = 0.30
_W_FRESHNESS    = 0.20
_W_RELIABILITY  = 0.20


class MarketQualityEngine:
    """Computes a QualityScore for one bar."""

    def __init__(
        self,
        expected_engines:  List[str] = None,
        max_stale_bars:    int = 5,
        current_bar_index: int = 0,
    ) -> None:
        self._expected     = expected_engines or KNOWN_ENGINES
        self._max_stale    = max_stale_bars
        self._current_bar  = current_bar_index

    def advance_bar(self, bar_index: int) -> None:
        self._current_bar = bar_index

    def score(
        self,
        state:     AggregationState,
        report:    ValidationReport,
        conflicts: ConflictSummary,
    ) -> QualityScore:
        completeness = self._completeness(state)
        consistency  = self._consistency(conflicts)
        freshness    = self._freshness(state)
        reliability  = self._reliability(report)

        overall = (
            completeness * _W_COMPLETENESS
            + consistency * _W_CONSISTENCY
            + freshness   * _W_FRESHNESS
            + reliability * _W_RELIABILITY
        )

        dimensions = [
            QualityDimension(
                "completeness", completeness, _W_COMPLETENESS,
                f"{len(state.engines_received)}/{len(self._expected)} engines received",
            ),
            QualityDimension(
                "consistency", consistency, _W_CONSISTENCY,
                f"{conflicts.total} conflicts ({conflicts.unresolved} unresolved)",
            ),
            QualityDimension(
                "freshness", freshness, _W_FRESHNESS,
                f"missing_engines={len(state.missing_engines)}",
            ),
            QualityDimension(
                "reliability", reliability, _W_RELIABILITY,
                f"validation={report.status.value} "
                f"passed={report.passed_rules} failed={report.failed_rules}",
            ),
        ]

        return QualityScore(
            bar_index=state.bar_index,
            overall=round(min(max(overall, 0.0), 100.0), 2),
            completeness=round(completeness, 2),
            consistency=round(consistency, 2),
            freshness=round(freshness, 2),
            reliability=round(reliability, 2),
            dimensions=dimensions,
        )

    # ── dimension calculators ─────────────────────────────────────────────────

    def _completeness(self, state: AggregationState) -> float:
        n_expected = len(self._expected)
        if n_expected == 0:
            return 100.0
        received = len(
            state.engines_received & set(self._expected)
        )
        return 100.0 * received / n_expected

    @staticmethod
    def _consistency(conflicts: ConflictSummary) -> float:
        penalty = 0.0
        for c in conflicts.conflicts:
            if not c.resolved:
                penalty += _CONFLICT_PENALTY[c.severity]
            else:
                # Resolved conflicts add a small penalty
                penalty += _CONFLICT_PENALTY[c.severity] * 0.2
        return max(0.0, 100.0 - penalty)

    def _freshness(self, state: AggregationState) -> float:
        stale_count = len(state.missing_engines)
        n_expected  = len(self._expected)
        if n_expected == 0:
            return 100.0
        # Linear decay per missing engine, capped at 0
        return max(0.0, 100.0 - stale_count * (100.0 / n_expected))

    @staticmethod
    def _reliability(report: ValidationReport) -> float:
        total = report.passed_rules + report.failed_rules + report.warned_rules
        if total == 0:
            return 100.0
        fail_penalty  = report.failed_rules  * 15.0
        warn_penalty  = report.warned_rules  * 5.0
        base          = 100.0 - fail_penalty - warn_penalty
        return max(0.0, base)
