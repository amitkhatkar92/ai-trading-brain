"""tests/unit/investment/company/integration/test_quality.py
Tests for quality framework: statistics, history, quality scoring, confidence.
"""
from __future__ import annotations

import pytest

from iios.investment.company.integration.company_confidence import (
    compute_confidence, explain_confidence,
)
from iios.investment.company.integration.company_quality import (
    CompanyQualityScore, compute_company_quality,
)
from iios.investment.company.integration.quality_history import (
    QualityHistory, QualityRecord,
)
from iios.investment.company.integration.quality_statistics import (
    confidence_from_quality, coverage_score, freshness_from_ages,
    overall_quality, quality_grade, reliability_from_conflicts, score_volatility,
)
from iios.investment.company.integration.company_state import SCORED_ENGINES


# ── quality_statistics ────────────────────────────────────────────────────────

class TestQualityStatistics:
    def test_quality_grade_a(self):
        assert quality_grade(90.0) == "A"

    def test_quality_grade_f(self):
        assert quality_grade(20.0) == "F"

    def test_coverage_score_full(self):
        assert coverage_score(8, 8) == pytest.approx(1.0)

    def test_coverage_score_zero(self):
        assert coverage_score(0, 8) == pytest.approx(0.0)

    def test_freshness_fresh_data(self):
        # Age = 60 seconds → should be near 1.0
        score = freshness_from_ages([60.0])
        assert score == pytest.approx(1.0)

    def test_freshness_stale_data(self):
        # Age = 100000 seconds → should be well below 0.5
        score = freshness_from_ages([100_000.0])
        assert score < 0.5

    def test_freshness_empty(self):
        assert freshness_from_ages([]) == pytest.approx(0.0)

    def test_overall_quality_perfect(self):
        q = overall_quality(1.0, 1.0, 1.0, 1.0)
        assert q == pytest.approx(100.0)

    def test_overall_quality_zero(self):
        q = overall_quality(0.0, 0.0, 0.0, 0.0)
        assert q == pytest.approx(0.0)

    def test_reliability_no_conflicts(self):
        r = reliability_from_conflicts(0, 0, completeness=0.8)
        assert r == pytest.approx(0.8)

    def test_reliability_with_conflicts(self):
        r_no = reliability_from_conflicts(0, 0, 0.8)
        r_yes = reliability_from_conflicts(5, 2, 0.8)
        assert r_yes < r_no

    def test_score_volatility_stable(self):
        stdev = score_volatility([60.0, 61.0, 60.5, 60.0])
        assert stdev < 1.0

    def test_score_volatility_volatile(self):
        stdev = score_volatility([20.0, 80.0, 30.0, 70.0])
        assert stdev > 15.0

    def test_confidence_from_quality_perfect(self):
        c = confidence_from_quality(1.0, 1.0, 1.0, 0.0, 10)
        assert c > 0.90

    def test_confidence_from_quality_low(self):
        c = confidence_from_quality(0.2, 0.3, 0.2, 20.0, 1)
        assert c < 0.40


# ── QualityHistory ────────────────────────────────────────────────────────────

class TestQualityHistory:
    def _record(self, ticker="X", q=70.0, conf=0.7):
        from datetime import datetime, timezone
        return QualityRecord(
            ticker=ticker, captured_at=datetime.now(timezone.utc),
            completeness=0.8, consistency=0.9, freshness=1.0,
            reliability=0.8, quality_score=q, confidence=conf,
            conflict_count=0, available_engines=6,
        )

    def test_record_and_retrieve(self):
        hist = QualityHistory()
        hist.record(self._record())
        records = hist.get_history("X", 5)
        assert len(records) == 1

    def test_latest(self):
        hist = QualityHistory()
        hist.record(self._record(q=60.0))
        hist.record(self._record(q=75.0))
        latest = hist.latest("X")
        assert latest.quality_score == pytest.approx(75.0)

    def test_quality_trend_improving(self):
        hist = QualityHistory()
        for q in [50.0, 60.0, 70.0]:
            hist.record(self._record(q=q))
        assert hist.quality_trend("X") > 0

    def test_confidence_series(self):
        hist = QualityHistory()
        for conf in [0.5, 0.6, 0.7]:
            hist.record(self._record(conf=conf))
        series = hist.confidence_series("X", n=5)
        assert len(series) == 3

    def test_unknown_ticker(self):
        hist = QualityHistory()
        assert hist.latest("UNKNOWN") is None
        assert hist.get_history("UNKNOWN") == []


# ── CompanyQualityScore & compute_company_quality ─────────────────────────────

class TestComputeCompanyQuality:
    def _quality(self, available=None, ages=None, validation_report=None,
                 conflicts=0, critical=0):
        available = available or ["financials", "earnings", "business_quality"]
        ages = ages or {e: 60.0 for e in available}
        return compute_company_quality(
            ticker="X",
            available_engines=available,
            engine_ages=ages,
            validation_report=validation_report,
            conflict_count=conflicts,
            critical_conflicts=critical,
        )

    def test_returns_quality_score(self):
        q = self._quality()
        assert isinstance(q, CompanyQualityScore)
        assert q.ticker == "X"

    def test_completeness_partial(self):
        q = self._quality(["financials", "earnings"])
        expected = 2 / len(SCORED_ENGINES)
        assert q.completeness == pytest.approx(expected)

    def test_completeness_full(self):
        q = self._quality(list(SCORED_ENGINES))
        assert q.completeness == pytest.approx(1.0)

    def test_freshness_fresh(self):
        q = self._quality(ages={"financials": 60.0, "earnings": 60.0})
        assert q.freshness > 0.95

    def test_freshness_stale(self):
        q = self._quality(ages={"financials": 200_000.0})
        assert q.freshness < 0.5

    def test_conflicts_reduce_reliability(self):
        q_no  = self._quality(conflicts=0)
        q_yes = self._quality(conflicts=10, critical=3)
        assert q_yes.reliability < q_no.reliability

    def test_quality_score_range(self):
        q = self._quality()
        assert 0.0 <= q.quality_score <= 100.0

    def test_quality_grade_valid(self):
        q = self._quality()
        assert q.quality_grade in ("A", "B", "C", "D", "F")

    def test_to_dict(self):
        q = self._quality()
        d = q.to_dict()
        assert all(k in d for k in ["completeness", "consistency", "quality_score", "quality_grade"])


# ── compute_confidence ────────────────────────────────────────────────────────

class TestComputeConfidence:
    def test_high_coverage_high_confidence(self):
        c = compute_confidence(
            ticker="X",
            completeness=1.0, consistency=0.95, freshness=1.0,
            conflict_count=0, critical_conflicts=0, eval_count=10,
        )
        assert c > 0.80

    def test_low_coverage_low_confidence(self):
        c = compute_confidence(
            ticker="X",
            completeness=0.20, consistency=0.50, freshness=0.30,
            conflict_count=5, critical_conflicts=2, eval_count=1,
        )
        assert c < 0.40

    def test_critical_conflicts_penalise(self):
        c_none = compute_confidence(
            "X", 0.8, 0.9, 0.9, 0, 0, 5
        )
        c_crit = compute_confidence(
            "X", 0.8, 0.9, 0.9, 0, 3, 5
        )
        assert c_crit < c_none

    def test_confidence_bounded(self):
        c = compute_confidence("X", 1.0, 1.0, 1.0, 0, 0, 100)
        assert 0.0 <= c <= 1.0

    def test_explain_confidence_returns_str(self):
        msg = explain_confidence(
            completeness=0.8, consistency=0.9, freshness=1.0,
            conflict_count=0, critical_conflicts=0,
            available_engines=["financials", "earnings"],
        )
        assert isinstance(msg, str) and len(msg) > 10
