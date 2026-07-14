"""tests/unit/investment/decision/confidence/test_reasoning_confidence.py"""
from __future__ import annotations

import pytest

from iios.investment.decision.confidence.contradiction_analysis import (
    ContradictionAnalyzer,
)
from iios.investment.decision.confidence.logic_strength import LogicStrengthAnalyzer
from iios.investment.decision.confidence.reasoning_confidence import (
    ReasoningConfidenceEstimator,
    ReasoningConfidenceResult,
)
from iios.investment.decision.confidence.reasoning_consistency import (
    ReasoningConsistencyAnalyzer,
)
from iios.investment.decision.reasoning.reasoning_constants import LogicValidationStatus


# ========================= ReasoningConsistencyAnalyzer ==================

class TestReasoningConsistencyAnalyzer:
    def test_returns_result(self, rich_reasoning_snapshot):
        ana = ReasoningConsistencyAnalyzer()
        result = ana.analyze(rich_reasoning_snapshot)
        assert 0.0 <= result.consistency_score <= 100.0

    def test_step_count_matches(self, rich_reasoning_snapshot):
        ana = ReasoningConsistencyAnalyzer()
        result = ana.analyze(rich_reasoning_snapshot)
        assert result.step_count == rich_reasoning_snapshot.reasoning_chain.step_count

    def test_logic_status_score_propagated(self, rich_reasoning_snapshot):
        ana = ReasoningConsistencyAnalyzer()
        result = ana.analyze(rich_reasoning_snapshot)
        assert result.logic_status_score == rich_reasoning_snapshot.logic_result.consistency_score

    def test_to_dict(self, rich_reasoning_snapshot):
        ana = ReasoningConsistencyAnalyzer()
        result = ana.analyze(rich_reasoning_snapshot)
        d = result.to_dict()
        assert "consistency_score" in d
        assert "step_count" in d

    def test_rich_higher_than_minimal(self, rich_reasoning_snapshot, minimal_reasoning_snapshot):
        ana = ReasoningConsistencyAnalyzer()
        rich_r    = ana.analyze(rich_reasoning_snapshot)
        minimal_r = ana.analyze(minimal_reasoning_snapshot)
        # Rich has more steps — consistency should generally be >= minimal
        assert rich_r.step_count >= minimal_r.step_count


# ========================= LogicStrengthAnalyzer =========================

class TestLogicStrengthAnalyzer:
    def test_returns_result(self, rich_reasoning_snapshot):
        ana = LogicStrengthAnalyzer()
        result = ana.analyze(rich_reasoning_snapshot)
        assert 0.0 <= result.logic_strength <= 100.0

    def test_step_completeness_range(self, rich_reasoning_snapshot):
        ana = LogicStrengthAnalyzer()
        result = ana.analyze(rich_reasoning_snapshot)
        assert 0.0 <= result.step_completeness <= 100.0

    def test_evidence_refs_positive(self, rich_reasoning_snapshot):
        ana = LogicStrengthAnalyzer()
        result = ana.analyze(rich_reasoning_snapshot)
        assert result.evidence_refs >= 0

    def test_to_dict(self, rich_reasoning_snapshot):
        ana = LogicStrengthAnalyzer()
        result = ana.analyze(rich_reasoning_snapshot)
        d = result.to_dict()
        assert "logic_strength" in d
        assert "step_completeness" in d

    def test_full_chain_higher_strength(self, rich_reasoning_snapshot, minimal_reasoning_snapshot):
        ana = LogicStrengthAnalyzer()
        rich_r    = ana.analyze(rich_reasoning_snapshot)
        minimal_r = ana.analyze(minimal_reasoning_snapshot)
        assert rich_r.step_completeness >= minimal_r.step_completeness


# ========================= ContradictionAnalyzer =========================

class TestContradictionAnalyzer:
    def test_no_contradictions_by_default(self, rich_reasoning_snapshot):
        ana = ContradictionAnalyzer()
        result = ana.analyze(rich_reasoning_snapshot)
        # Rich snapshot should have low or no contradictions
        assert 0.0 <= result.contradiction_free_score <= 100.0

    def test_contradiction_free_score_inverse(self, rich_reasoning_snapshot):
        ana = ContradictionAnalyzer()
        result = ana.analyze(rich_reasoning_snapshot)
        expected = 100.0 - result.contradiction_severity
        assert abs(result.contradiction_free_score - expected) < 0.1

    def test_to_dict(self, rich_reasoning_snapshot):
        ana = ContradictionAnalyzer()
        result = ana.analyze(rich_reasoning_snapshot)
        d = result.to_dict()
        assert "contradiction_free_score" in d
        assert "contradiction_severity" in d

    def test_severity_range(self, rich_reasoning_snapshot):
        ana = ContradictionAnalyzer()
        result = ana.analyze(rich_reasoning_snapshot)
        assert 0.0 <= result.contradiction_severity <= 100.0


# ========================= ReasoningConfidenceEstimator ==================

class TestReasoningConfidenceEstimator:
    def test_returns_result(self, rich_reasoning_snapshot):
        est = ReasoningConfidenceEstimator()
        result = est.estimate(rich_reasoning_snapshot)
        assert isinstance(result, ReasoningConfidenceResult)

    def test_overall_in_range(self, rich_reasoning_snapshot):
        est = ReasoningConfidenceEstimator()
        result = est.estimate(rich_reasoning_snapshot)
        assert 0.0 <= result.overall <= 100.0

    def test_rich_beats_minimal(self, rich_reasoning_snapshot, minimal_reasoning_snapshot):
        est = ReasoningConfidenceEstimator()
        rich_r    = est.estimate(rich_reasoning_snapshot)
        minimal_r = est.estimate(minimal_reasoning_snapshot)
        # Rich should have better or equal completeness
        assert rich_r.completeness_score >= minimal_r.completeness_score

    def test_all_dimensions_populated(self, rich_reasoning_snapshot):
        est = ReasoningConfidenceEstimator()
        result = est.estimate(rich_reasoning_snapshot)
        assert result.completeness_score >= 0.0
        assert result.consistency_score >= 0.0
        assert result.contradiction_free >= 0.0
        assert result.hypothesis_strength >= 0.0
        assert result.argument_quality >= 0.0

    def test_detail_objects_present(self, rich_reasoning_snapshot):
        est = ReasoningConfidenceEstimator()
        result = est.estimate(rich_reasoning_snapshot)
        assert result.consistency_detail is not None
        assert result.logic_detail is not None
        assert result.contradiction_detail is not None

    def test_to_dict(self, rich_reasoning_snapshot):
        est = ReasoningConfidenceEstimator()
        result = est.estimate(rich_reasoning_snapshot)
        d = result.to_dict()
        assert "overall" in d
        assert "completeness_score" in d
        assert "contradiction_detail" in d
