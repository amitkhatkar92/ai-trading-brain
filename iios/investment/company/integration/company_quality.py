"""iios/investment/company/integration/company_quality.py
Computes multi-dimensional quality for a Company Intelligence evaluation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.company.integration.quality_statistics import (
    coverage_score, freshness_from_ages, consistency_from_checks,
    overall_quality, quality_grade, reliability_from_conflicts,
)
from iios.investment.company.integration.quality_history import QualityHistory, QualityRecord
from iios.investment.company.integration.validation_report import ValidationReport
from iios.investment.company.integration.company_state import SCORED_ENGINES


@dataclass
class CompanyQualityScore:
    """Multi-dimensional quality assessment for a single company evaluation."""
    ticker:        str

    # Dimensions (0-1)
    completeness:  float = 0.0   # fraction of SCORED_ENGINES providing data
    consistency:   float = 0.0   # fraction of consistency checks passed
    freshness:     float = 0.0   # recency of data
    reliability:   float = 0.0   # conflict-adjusted trustworthiness
    coverage:      float = 0.0   # depth within each engine

    # Composite
    quality_score: float = 0.0   # 0-100
    quality_grade: str   = "F"

    # Metadata
    available_engines: int = 0
    conflict_count:    int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker":            self.ticker,
            "completeness":      round(self.completeness, 3),
            "consistency":       round(self.consistency, 3),
            "freshness":         round(self.freshness, 3),
            "reliability":       round(self.reliability, 3),
            "coverage":          round(self.coverage, 3),
            "quality_score":     round(self.quality_score, 1),
            "quality_grade":     self.quality_grade,
            "available_engines": self.available_engines,
            "conflict_count":    self.conflict_count,
        }


def compute_company_quality(
    ticker:               str,
    available_engines:    List[str],
    engine_ages:          Dict[str, float],    # engine → age in seconds
    validation_report:    Optional[ValidationReport],
    conflict_count:       int,
    critical_conflicts:   int,
    score_history:        Optional[List[float]] = None,
) -> CompanyQualityScore:
    """
    Compute the multi-dimensional quality for one company evaluation.
    All dimensions are computed independently and then combined.
    """
    # 1. Completeness — fraction of SCORED_ENGINES present
    scored_present = sum(1 for e in SCORED_ENGINES if e in available_engines)
    completeness = coverage_score(scored_present, len(SCORED_ENGINES))

    # 2. Freshness — based on age of each engine's update
    ages = [engine_ages[e] for e in available_engines if e in engine_ages]
    freshness = freshness_from_ages(ages) if ages else 0.0

    # 3. Consistency — from validation report
    if validation_report is not None:
        consistency = consistency_from_checks(
            validation_report.passed_count,
            validation_report.total_checks,
            validation_report.critical_failure_count,
        )
    else:
        consistency = 1.0  # no checks → assume consistent

    # 4. Reliability — conflicts penalise; coverage enhances
    reliability = reliability_from_conflicts(
        conflict_count, critical_conflicts, completeness
    )

    # 5. Coverage depth — proxy: more engines with data → deeper coverage
    # Bonus for high-value engines (financials, earnings, BQ are core)
    core_engines = {"financials", "earnings", "business_quality"}
    core_present = sum(1 for e in core_engines if e in available_engines)
    coverage = min(1.0, completeness * 0.7 + (core_present / len(core_engines)) * 0.3)

    # 6. Composite
    q_score = overall_quality(completeness, consistency, freshness, reliability)
    grade   = quality_grade(q_score)

    return CompanyQualityScore(
        ticker=ticker,
        completeness=round(completeness, 4),
        consistency=round(consistency, 4),
        freshness=round(freshness, 4),
        reliability=round(reliability, 4),
        coverage=round(coverage, 4),
        quality_score=q_score,
        quality_grade=grade,
        available_engines=len(available_engines),
        conflict_count=conflict_count,
    )


def record_quality(
    history:  QualityHistory,
    quality:  CompanyQualityScore,
    confidence: float,
) -> None:
    """Persist a QualityRecord into the history buffer."""
    record = QualityRecord(
        ticker=quality.ticker,
        captured_at=datetime.now(timezone.utc),
        completeness=quality.completeness,
        consistency=quality.consistency,
        freshness=quality.freshness,
        reliability=quality.reliability,
        quality_score=quality.quality_score,
        confidence=confidence,
        conflict_count=quality.conflict_count,
        available_engines=quality.available_engines,
    )
    history.record(record)
