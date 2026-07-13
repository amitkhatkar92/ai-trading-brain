"""tests/unit/investment/company/integration/test_snapshot.py
Tests for CompanyIntelligenceSnapshot.
"""
from __future__ import annotations

import pytest

from iios.investment.company.integration.company_snapshot import CompanyIntelligenceSnapshot
from iios.investment.company.integration.company_state import (
    IntelligenceCompleteness, SCORED_ENGINES, score_to_grade,
)


class TestCompanyIntelligenceSnapshot:
    def _snap(self, overall=65.0, completeness=0.75, quality=70.0,
              confidence=0.70, conflict_count=0, critical_conflicts=0,
              available=None):
        available = available or ["financials", "earnings", "business_quality"]
        return CompanyIntelligenceSnapshot(
            ticker="INFY",
            company_name="Infosys",
            sector="IT",
            industry="Software",
            exchange="NSE",
            financial_score=70.0,
            earnings_score=72.0,
            business_quality_score=68.0,
            overall_score=overall,
            completeness=completeness,
            quality_score=quality,
            confidence=confidence,
            conflict_count=conflict_count,
            critical_conflict_count=critical_conflicts,
            available_engines=available,
            missing_engines=[e for e in SCORED_ENGINES if e not in available],
        )

    def test_identity(self):
        snap = self._snap()
        assert snap.ticker == "INFY"
        assert snap.company_name == "Infosys"
        assert snap.sector == "IT"

    def test_generated_at_timezone_aware(self):
        snap = self._snap()
        assert snap.generated_at.tzinfo is not None

    def test_snapshot_id_not_empty(self):
        snap = self._snap()
        assert snap.snapshot_id and len(snap.snapshot_id) > 5

    def test_intelligence_grade(self):
        snap_a = self._snap(overall=85.0)
        snap_f = self._snap(overall=20.0)
        assert snap_a.intelligence_grade in ("A+", "A", "B+", "B")
        assert snap_f.intelligence_grade in ("D", "F")

    def test_completeness_label_partial(self):
        snap = self._snap(completeness=4/8, available=["financials", "earnings",
                                                        "business_quality", "valuation"])
        assert snap.completeness_label == IntelligenceCompleteness.PARTIAL

    def test_completeness_label_complete(self):
        snap = self._snap(completeness=1.0, available=list(SCORED_ENGINES))
        assert snap.completeness_label == IntelligenceCompleteness.COMPLETE

    def test_is_high_quality_true(self):
        assert self._snap(quality=80.0).is_high_quality is True

    def test_is_high_quality_false(self):
        assert self._snap(quality=60.0).is_high_quality is False

    def test_has_conflicts(self):
        snap_with = self._snap(conflict_count=2)
        snap_without = self._snap(conflict_count=0)
        assert snap_with.has_conflicts is True
        assert snap_without.has_conflicts is False

    def test_has_critical_conflicts(self):
        assert self._snap(critical_conflicts=1).has_critical_conflicts is True
        assert self._snap(critical_conflicts=0).has_critical_conflicts is False

    def test_is_complete_false(self):
        assert self._snap(completeness=0.5).is_complete is False

    def test_is_complete_true(self):
        snap = self._snap(completeness=1.0, available=list(SCORED_ENGINES))
        assert snap.is_complete is True

    def test_engine_scores(self):
        snap = self._snap()
        scores = snap.engine_scores
        assert scores["financials"] == pytest.approx(70.0)
        assert scores["earnings"]   == pytest.approx(72.0)
        assert scores["valuation"]  is None   # not set

    def test_score_for_engine(self):
        snap = self._snap()
        assert snap.score_for_engine("financials") == pytest.approx(70.0)
        assert snap.score_for_engine("unknown") is None

    def test_to_dict_complete(self):
        snap = self._snap()
        d = snap.to_dict()
        required_keys = [
            "ticker", "snapshot_id", "company_name", "sector", "industry",
            "overall_score", "intelligence_grade",
            "financial_score", "earnings_score", "business_quality_score",
            "completeness", "consistency_score", "freshness_score", "quality_score",
            "confidence", "validation_passed", "conflict_count",
            "available_engines", "missing_engines",
        ]
        for key in required_keys:
            assert key in d, f"Missing key: {key}"

    def test_to_dict_values(self):
        snap = self._snap(overall=65.0)
        d = snap.to_dict()
        assert d["ticker"] == "INFY"
        assert d["overall_score"] == pytest.approx(65.0, abs=0.01)


class TestScoreToGrade:
    def test_grade_boundaries(self):
        assert score_to_grade(95.0) == "A+"
        assert score_to_grade(85.0) == "A"
        assert score_to_grade(76.0) == "B+"
        assert score_to_grade(68.0) == "B"
        assert score_to_grade(58.0) == "C+"
        assert score_to_grade(50.0) == "C"
        assert score_to_grade(38.0) == "D"
        assert score_to_grade(20.0) == "F"
