"""tests/unit/investment/decision/confidence/test_evidence_confidence.py"""
from __future__ import annotations

import pytest

from iios.investment.decision.confidence.coverage_analysis import CoverageAnalyzer
from iios.investment.decision.confidence.evidence_confidence import (
    EvidenceConfidenceEstimator,
    EvidenceConfidenceResult,
)
from iios.investment.decision.confidence.freshness_analysis import FreshnessAnalyzer
from iios.investment.decision.confidence.source_reliability import (
    SourceReliabilityAnalyzer,
)
from iios.investment.decision.evidence.evidence_constants import EvidenceSourceType


# ========================= SourceReliabilityAnalyzer =====================

class TestSourceReliabilityAnalyzer:
    def test_empty_items(self):
        sra = SourceReliabilityAnalyzer()
        scores, overall = sra.analyze([])
        assert scores == []
        assert overall == 0.0

    def test_single_source(self, rich_evidence_snapshot, make_ev_item):
        items = [
            make_ev_item("price", 100, EvidenceSourceType.MARKET, 90.0),
            make_ev_item("rsi", 50, EvidenceSourceType.MARKET, 80.0),
        ]
        sra = SourceReliabilityAnalyzer()
        scores, overall = sra.analyze(items)
        assert len(scores) == 1
        assert scores[0].source_type == "market"
        assert 0.0 <= overall <= 100.0

    def test_multiple_sources(self, rich_evidence_snapshot):
        sra = SourceReliabilityAnalyzer()
        scores, overall = sra.analyze(list(rich_evidence_snapshot.items))
        source_types = {s.source_type for s in scores}
        assert "market" in source_types
        assert "risk" in source_types
        assert 0.0 <= overall <= 100.0

    def test_high_confidence_raises_reliability(self, make_ev_item):
        items = [make_ev_item("price", 100, EvidenceSourceType.MARKET, 99.0) for _ in range(5)]
        sra = SourceReliabilityAnalyzer()
        _, overall = sra.analyze(items)
        low_conf_items = [make_ev_item("price", 100, EvidenceSourceType.MARKET, 20.0) for _ in range(5)]
        _, low_overall = sra.analyze(low_conf_items)
        assert overall > low_overall

    def test_score_in_range(self, make_ev_item):
        items = [make_ev_item("x", 1, EvidenceSourceType.RESEARCH, 60.0)]
        sra = SourceReliabilityAnalyzer()
        scores, overall = sra.analyze(items)
        assert 0.0 <= scores[0].final_score <= 100.0


# ========================= FreshnessAnalyzer =============================

class TestFreshnessAnalyzer:
    def test_empty_items(self):
        fa = FreshnessAnalyzer()
        result = fa.analyze([])
        assert result.item_count == 0
        assert result.freshness_conf == 0.0

    def test_fresh_items_high_score(self, rich_evidence_snapshot):
        fa = FreshnessAnalyzer()
        result = fa.analyze(list(rich_evidence_snapshot.items))
        assert result.freshness_conf > 50.0

    def test_stale_count(self, make_ev_item):
        from iios.investment.decision.evidence.evidence_item import make_evidence_item
        from iios.investment.decision.evidence.evidence_constants import EvidenceCategory, EvidenceSourceType
        stale = make_evidence_item(
            decision_id="D1", source_type=EvidenceSourceType.MARKET, source_provider="p",
            subject_id="S", subject_type="equity", category=EvidenceCategory.TECHNICAL,
            key="p", value=1, confidence=50.0, freshness_score=0.20,
        )
        fa = FreshnessAnalyzer()
        result = fa.analyze([stale])
        assert result.stale_items == 1

    def test_all_fresh(self, rich_evidence_snapshot):
        fa = FreshnessAnalyzer()
        result = fa.analyze(list(rich_evidence_snapshot.items))
        assert result.fresh_items == len(rich_evidence_snapshot.items)

    def test_to_dict(self, rich_evidence_snapshot):
        fa = FreshnessAnalyzer()
        result = fa.analyze(list(rich_evidence_snapshot.items))
        d = result.to_dict()
        assert "freshness_conf" in d
        assert "decayed_score" in d


# ========================= CoverageAnalyzer ==============================

class TestCoverageAnalyzer:
    def test_empty(self):
        ca = CoverageAnalyzer()
        result = ca.analyze([])
        assert result.required_met is False
        assert result.coverage_conf == 0.0

    def test_required_sources_met(self, rich_evidence_snapshot):
        ca = CoverageAnalyzer()
        result = ca.analyze(list(rich_evidence_snapshot.items))
        assert result.required_met is True

    def test_missing_required(self, make_ev_item):
        items = [make_ev_item("pe", 20, EvidenceSourceType.COMPANY)]  # no market or risk
        ca = CoverageAnalyzer()
        result = ca.analyze(items)
        assert result.required_met is False
        assert "market" in result.missing_required or "risk" in result.missing_required

    def test_high_coverage_fraction_rich(self, rich_evidence_snapshot):
        ca = CoverageAnalyzer()
        result = ca.analyze(list(rich_evidence_snapshot.items))
        assert result.coverage_fraction > 0.5

    def test_to_dict(self, rich_evidence_snapshot):
        ca = CoverageAnalyzer()
        result = ca.analyze(list(rich_evidence_snapshot.items))
        d = result.to_dict()
        assert "coverage_conf" in d
        assert "required_met" in d

    def test_coverage_conf_range(self, rich_evidence_snapshot):
        ca = CoverageAnalyzer()
        result = ca.analyze(list(rich_evidence_snapshot.items))
        assert 0.0 <= result.coverage_conf <= 100.0


# ========================= EvidenceConfidenceEstimator ===================

class TestEvidenceConfidenceEstimator:
    def test_returns_result(self, rich_evidence_snapshot):
        est = EvidenceConfidenceEstimator()
        result = est.estimate(rich_evidence_snapshot)
        assert isinstance(result, EvidenceConfidenceResult)

    def test_overall_in_range(self, rich_evidence_snapshot):
        est = EvidenceConfidenceEstimator()
        result = est.estimate(rich_evidence_snapshot)
        assert 0.0 <= result.overall <= 100.0

    def test_rich_beats_minimal(self, rich_evidence_snapshot, minimal_evidence_snapshot):
        est = EvidenceConfidenceEstimator()
        rich   = est.estimate(rich_evidence_snapshot)
        minimal = est.estimate(minimal_evidence_snapshot)
        assert rich.overall >= minimal.overall

    def test_item_count(self, rich_evidence_snapshot):
        est = EvidenceConfidenceEstimator()
        result = est.estimate(rich_evidence_snapshot)
        assert result.item_count == rich_evidence_snapshot.item_count

    def test_source_scores_populated(self, rich_evidence_snapshot):
        est = EvidenceConfidenceEstimator()
        result = est.estimate(rich_evidence_snapshot)
        assert len(result.source_scores) > 0

    def test_to_dict(self, rich_evidence_snapshot):
        est = EvidenceConfidenceEstimator()
        result = est.estimate(rich_evidence_snapshot)
        d = result.to_dict()
        assert "overall" in d
        assert "coverage_score" in d
        assert "freshness_score" in d
        assert "reliability_score" in d
        assert "consistency_score" in d
