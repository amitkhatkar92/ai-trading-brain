"""iios/investment/company/financials/quality_statistics.py
Aggregated financial quality statistics for a company.
Combines completeness, consistency, and restatement signals into a single score.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.company.financials.statement_consistency import ConsistencyReport


@dataclass
class FinancialQualityScore:
    """
    Overall quality score (0–100) and its components.
    100 = perfectly complete, internally consistent, never restated.
    This is a data-quality metric, NOT an investment quality signal.
    """
    # Component scores (0–100 each)
    completeness_score:  float = 100.0   # avg field completeness across statements
    consistency_score:   float = 100.0   # from ConsistencyReport
    restatement_score:   float = 100.0   # penalised per restatement event
    reporting_score:     float = 100.0   # regularity / freshness of filings

    # Weights
    _WEIGHT_COMPLETE  = 0.35
    _WEIGHT_CONSIST   = 0.35
    _WEIGHT_RESTATE   = 0.20
    _WEIGHT_REPORTING = 0.10

    # Composite
    overall_score: float = 100.0

    # Flags (plain-text issues)
    flags: List[str] = field(default_factory=list)

    # Consistency report attached for reference
    consistency_report: Optional[ConsistencyReport] = None

    # Metadata
    periods_assessed: int = 0
    restatements:     int = 0

    metadata: Dict[str, Any] = field(default_factory=dict)

    def recompute(self) -> None:
        """Recalculate overall_score from components."""
        self.overall_score = (
            self.completeness_score  * self._WEIGHT_COMPLETE
            + self.consistency_score * self._WEIGHT_CONSIST
            + self.restatement_score * self._WEIGHT_RESTATE
            + self.reporting_score   * self._WEIGHT_REPORTING
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score":      round(self.overall_score, 1),
            "completeness_score": round(self.completeness_score, 1),
            "consistency_score":  round(self.consistency_score, 1),
            "restatement_score":  round(self.restatement_score, 1),
            "reporting_score":    round(self.reporting_score, 1),
            "flags":              self.flags,
            "periods_assessed":   self.periods_assessed,
            "restatements":       self.restatements,
        }


class QualityStatisticsEngine:
    """Produces FinancialQualityScore from raw quality inputs."""

    _RESTATEMENT_PENALTY = 10.0   # points per restatement
    _MIN_RESTATEMENT     = 30.0   # floor after many restatements

    def compute(
        self,
        completeness_pct:    float,
        consistency_report:  Optional[ConsistencyReport],
        restatement_count:   int,
        periods_with_data:   int,
        periods_expected:    int,
    ) -> FinancialQualityScore:
        score = FinancialQualityScore()
        score.completeness_score = completeness_pct
        score.periods_assessed   = periods_with_data
        score.restatements       = restatement_count
        score.consistency_report = consistency_report

        if consistency_report is not None:
            score.consistency_score = consistency_report.score
            for issue in consistency_report.issues:
                score.flags.append(f"consistency:{issue.check}:{issue.severity}")

        # Restatement score
        penalty = self._RESTATEMENT_PENALTY * restatement_count
        score.restatement_score = max(self._MIN_RESTATEMENT, 100.0 - penalty)
        if restatement_count > 0:
            score.flags.append(f"restatements:{restatement_count}")

        # Reporting regularity
        if periods_expected > 0:
            coverage = 100.0 * periods_with_data / periods_expected
            score.reporting_score = min(100.0, coverage)
            if coverage < 80.0:
                score.flags.append(f"low_coverage:{coverage:.0f}%")

        score.recompute()
        return score
