"""tests/unit/investment/decision/evidence/test_quality.py"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from iios.investment.decision.evidence.evidence_constants import (
    EvidenceCategory, EvidencePriority, EvidenceSourceType,
)
from iios.investment.decision.evidence.evidence_item import make_evidence_item
from iios.investment.decision.evidence.quality_score import QualityScore, compute_quality_score
from iios.investment.decision.evidence.quality_statistics import QualityStatisticsTracker
from iios.investment.decision.evidence.quality_history import QualityHistory
from iios.investment.decision.evidence.evidence_quality import EvidenceQuality


def _qs(overall=80.0):
    return compute_quality_score(
        coverage=80.0, freshness=85.0, consistency=90.0, reliability=75.0, completeness=70.0,
    )


def _item(src=EvidenceSourceType.MARKET, confidence=80.0, freshness=1.0, key="x", required=False):
    return make_evidence_item(
        decision_id="D1", source_type=src, source_provider="p",
        subject_id="INFY", subject_type="equity",
        category=EvidenceCategory.TECHNICAL, key=key, value=1.0,
        confidence=confidence, freshness_score=freshness, is_required=required,
    )


# =========================== QualityScore ================================

class TestQualityScore:
    def test_compute_quality_score_range(self):
        qs = compute_quality_score(80, 90, 100, 70, 60)
        assert 0.0 <= qs.overall <= 100.0

    def test_all_max_gives_near_100(self):
        qs = compute_quality_score(100, 100, 100, 100, 100)
        assert qs.overall == pytest.approx(100.0)

    def test_all_zero_gives_zero(self):
        qs = compute_quality_score(0, 0, 0, 0, 0)
        assert qs.overall == 0.0

    def test_grade_a(self):
        qs = compute_quality_score(100, 100, 100, 100, 100)
        assert qs.grade == "A"

    def test_grade_f(self):
        qs = compute_quality_score(0, 0, 0, 0, 0)
        assert qs.grade == "F"

    def test_to_dict(self):
        qs = _qs()
        d  = qs.to_dict()
        for k in ("overall", "grade", "coverage", "freshness", "consistency",
                  "reliability", "completeness", "computed_at"):
            assert k in d

    def test_weights_sum_to_1(self):
        from iios.investment.decision.evidence.evidence_constants import EvidenceQualityDimension
        total = sum(dim.default_weight for dim in EvidenceQualityDimension)
        assert total == pytest.approx(1.0)


# =========================== QualityStatisticsTracker ====================

class TestQualityStatisticsTracker:
    def test_empty(self):
        t = QualityStatisticsTracker()
        s = t.summary()
        assert s.total_computed == 0

    def test_records_grade(self):
        t = QualityStatisticsTracker()
        t.record(_qs())
        s = t.summary()
        assert s.total_computed == 1
        assert len(s.grade_dist) >= 1

    def test_reset(self):
        t = QualityStatisticsTracker()
        t.record(_qs())
        t.reset()
        assert t.summary().total_computed == 0


# =========================== QualityHistory ==============================

class TestQualityHistory:
    def test_record_and_get(self):
        h = QualityHistory()
        qs = _qs()
        h.record("INFY", qs)
        got = h.get("INFY")
        assert qs in got

    def test_latest(self):
        h = QualityHistory()
        h.record("INFY", _qs())
        assert h.latest("INFY") is not None

    def test_trend_needs_at_least_two(self):
        h = QualityHistory()
        h.record("INFY", _qs())
        assert h.trend("INFY") is None

    def test_trend_positive(self):
        h = QualityHistory()
        h.record("INFY", compute_quality_score(60, 60, 60, 60, 60))
        h.record("INFY", compute_quality_score(90, 90, 90, 90, 90))
        t = h.trend("INFY")
        assert t is not None and t > 0


# =========================== EvidenceQuality =============================

class TestEvidenceQuality:
    def _all_items(self):
        return [
            _item(EvidenceSourceType.MARKET,    confidence=80.0, key="price",    required=True),
            _item(EvidenceSourceType.RISK,       confidence=75.0, key="risk_score", required=True),
            _item(EvidenceSourceType.COMPANY,    confidence=70.0, key="pe"),
            _item(EvidenceSourceType.STRATEGY,   confidence=72.0, key="signal"),
            _item(EvidenceSourceType.KNOWLEDGE,  confidence=60.0, key="news"),
            _item(EvidenceSourceType.RESEARCH,   confidence=65.0, key="target"),
        ]

    def test_score_returns_quality_score(self):
        eq = EvidenceQuality()
        qs = eq.score(self._all_items(), subject_id="INFY")
        assert isinstance(qs, QualityScore)
        assert 0.0 <= qs.overall <= 100.0

    def test_empty_items_gives_low_score(self):
        eq = EvidenceQuality()
        qs = eq.score([], subject_id="X")
        # consistency=100 (no conflicts) × 0.20 = 20; all other dims are 0
        assert qs.overall <= 25.0
        assert qs.coverage == 0.0
        assert qs.freshness == 0.0

    def test_records_to_stats(self):
        eq = EvidenceQuality()
        eq.score(self._all_items(), subject_id="INFY")
        s = eq.stats()
        assert s["total_computed"] == 1

    def test_history_recorded(self):
        eq = EvidenceQuality()
        eq.score(self._all_items(), subject_id="INFY")
        hist = eq.history("INFY")
        assert len(hist) == 1

    def test_high_confidence_gives_higher_score(self):
        eq   = EvidenceQuality()
        low  = [_item(EvidenceSourceType.MARKET, confidence=20.0, key="p1", required=True),
                _item(EvidenceSourceType.RISK,   confidence=20.0, key="r1", required=True)]
        high = [_item(EvidenceSourceType.MARKET, confidence=95.0, key="p2", required=True),
                _item(EvidenceSourceType.RISK,   confidence=95.0, key="r2", required=True)]
        assert eq.score(high).overall > eq.score(low).overall
