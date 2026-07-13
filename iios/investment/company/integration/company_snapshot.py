"""iios/investment/company/integration/company_snapshot.py
CompanyIntelligenceSnapshot — the primary canonical output of the
Company Intelligence Integration Engine.

All downstream IIOS components must consume ONLY this object.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.company.integration.company_state import (
    IntelligenceCompleteness, SCORED_ENGINES,
    completeness_from_fraction, score_to_grade,
)
from iios.investment.company.integration.company_summary import CompanySummary
from iios.investment.company.integration.validation_report import ValidationReport


@dataclass
class CompanyIntelligenceSnapshot:
    """
    Single canonical point-in-time view of a company's integrated intelligence.

    This is the ONLY object that downstream IIOS components should consume.
    NOT a buy/sell/hold recommendation.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    ticker:           str
    snapshot_id:      str     = field(default_factory=lambda: f"cis-{uuid.uuid4().hex[:10]}")
    company_name:     Optional[str] = None
    sector:           Optional[str] = None
    industry:         Optional[str] = None
    exchange:         Optional[str] = None
    generated_at:     datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    evaluation_count: int = 0

    # ── Dimension scores (0-100 each; None = unavailable) ────────────────────
    financial_score:       Optional[float] = None
    earnings_score:        Optional[float] = None
    business_quality_score: Optional[float] = None
    valuation_score:       Optional[float] = None
    growth_score:          Optional[float] = None
    management_score:      Optional[float] = None
    ownership_score:       Optional[float] = None
    opportunity_score:     Optional[float] = None

    # ── Overall intelligence score ────────────────────────────────────────────
    overall_score: float = 0.0   # 0-100, weighted composite of dimension scores

    # ── Dimension labels ──────────────────────────────────────────────────────
    financial_label:       str = "unavailable"
    earnings_label:        str = "unavailable"
    business_quality_label: str = "unavailable"
    valuation_label:       str = "unavailable"
    growth_label:          str = "unavailable"
    management_label:      str = "unavailable"
    ownership_label:       str = "unavailable"
    opportunity_label:     str = "unavailable"

    # ── Quality dimensions (0-1 each) ─────────────────────────────────────────
    completeness:      float = 0.0   # fraction of SCORED_ENGINES providing data
    consistency_score: float = 0.0   # fraction of consistency checks passed
    freshness_score:   float = 0.0   # how recent the data is
    reliability_score: float = 0.0   # based on conflicts and error rates
    quality_score:     float = 0.0   # 0-100 composite quality
    confidence:        float = 0.0   # 0-1 overall confidence in this snapshot

    # ── Validation ────────────────────────────────────────────────────────────
    validation_passed:       bool = True
    validation_report:       Optional[ValidationReport] = None
    conflict_count:          int  = 0
    critical_conflict_count: int  = 0
    conflict_messages:       List[str] = field(default_factory=list)

    # ── Narrative ─────────────────────────────────────────────────────────────
    summary:          Optional[CompanySummary] = None
    key_strengths:    List[str] = field(default_factory=list)
    key_risks:        List[str] = field(default_factory=list)
    key_opportunities: List[str] = field(default_factory=list)
    alerts:           List[str] = field(default_factory=list)

    # ── Coverage ──────────────────────────────────────────────────────────────
    available_engines:  List[str] = field(default_factory=list)
    missing_engines:    List[str] = field(default_factory=list)
    engine_staleness:   Dict[str, float] = field(default_factory=dict)  # engine→seconds

    # ── Convenience properties ────────────────────────────────────────────────

    @property
    def intelligence_grade(self) -> str:
        return score_to_grade(self.overall_score)

    @property
    def completeness_label(self) -> IntelligenceCompleteness:
        return completeness_from_fraction(self.completeness)

    @property
    def is_high_quality(self) -> bool:
        return self.quality_score >= 75.0

    @property
    def has_conflicts(self) -> bool:
        return self.conflict_count > 0

    @property
    def has_critical_conflicts(self) -> bool:
        return self.critical_conflict_count > 0

    @property
    def is_complete(self) -> bool:
        return self.completeness >= 8 / len(SCORED_ENGINES)

    @property
    def engine_scores(self) -> Dict[str, Optional[float]]:
        return {
            "financials":       self.financial_score,
            "earnings":         self.earnings_score,
            "business_quality": self.business_quality_score,
            "valuation":        self.valuation_score,
            "growth":           self.growth_score,
            "management":       self.management_score,
            "ownership":        self.ownership_score,
            "opportunity":      self.opportunity_score,
        }

    def score_for_engine(self, engine: str) -> Optional[float]:
        return self.engine_scores.get(engine)

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker":                  self.ticker,
            "snapshot_id":             self.snapshot_id,
            "company_name":            self.company_name,
            "sector":                  self.sector,
            "industry":                self.industry,
            "exchange":                self.exchange,
            "generated_at":            self.generated_at.isoformat(),
            "evaluation_count":        self.evaluation_count,
            # Scores
            "financial_score":         self.financial_score,
            "earnings_score":          self.earnings_score,
            "business_quality_score":  self.business_quality_score,
            "valuation_score":         self.valuation_score,
            "growth_score":            self.growth_score,
            "management_score":        self.management_score,
            "ownership_score":         self.ownership_score,
            "opportunity_score":       self.opportunity_score,
            "overall_score":           round(self.overall_score, 2),
            "intelligence_grade":      self.intelligence_grade,
            # Labels
            "financial_label":         self.financial_label,
            "earnings_label":          self.earnings_label,
            "business_quality_label":  self.business_quality_label,
            "valuation_label":         self.valuation_label,
            "growth_label":            self.growth_label,
            "management_label":        self.management_label,
            "ownership_label":         self.ownership_label,
            "opportunity_label":       self.opportunity_label,
            # Quality
            "completeness":            round(self.completeness, 3),
            "completeness_label":      self.completeness_label.value,
            "consistency_score":       round(self.consistency_score, 3),
            "freshness_score":         round(self.freshness_score, 3),
            "reliability_score":       round(self.reliability_score, 3),
            "quality_score":           round(self.quality_score, 1),
            "confidence":              round(self.confidence, 3),
            # Validation
            "validation_passed":       self.validation_passed,
            "conflict_count":          self.conflict_count,
            "critical_conflict_count": self.critical_conflict_count,
            "conflict_messages":       self.conflict_messages,
            # Narrative
            "key_strengths":           self.key_strengths,
            "key_risks":               self.key_risks,
            "key_opportunities":       self.key_opportunities,
            "alerts":                  self.alerts,
            # Coverage
            "available_engines":       self.available_engines,
            "missing_engines":         self.missing_engines,
            "engine_staleness":        {k: round(v, 1) for k, v in self.engine_staleness.items()},
        }
