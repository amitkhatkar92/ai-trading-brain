"""tests/unit/investment/decision/reasoning/test_quality.py"""
from __future__ import annotations

import pytest

from iios.investment.decision.reasoning.reasoning_chain import build_chain
from iios.investment.decision.reasoning.reasoning_confidence import ReasoningConfidence
from iios.investment.decision.reasoning.reasoning_constants import (
    LogicValidationStatus,
    ReasoningQualityDimension,
    ReasoningStepType,
)
from iios.investment.decision.reasoning.reasoning_health import ReasoningHealth
from iios.investment.decision.reasoning.reasoning_quality import ReasoningQuality
from iios.investment.decision.reasoning.reasoning_score import (
    ReasoningQualityScore,
    compute_reasoning_score,
)
from iios.investment.decision.reasoning.reasoning_step import make_step


def _full_chain(decision_id="D1"):
    steps = [
        make_step(t, "d", "c", evidence_trace_ids=("t1",), order=i)
        for i, t in enumerate(ReasoningStepType)
    ]
    return build_chain(decision_id, steps, "Final conclusion.")


def _partial_chain(decision_id="D1"):
    steps = [
        make_step(ReasoningStepType.EVIDENCE_REVIEW, "d", "c", order=0),
        make_step(ReasoningStepType.CONTEXT_ANALYSIS, "d", "c", order=1),
    ]
    return build_chain(decision_id, steps, "Partial conclusion.")


def _logic_result(status=LogicValidationStatus.VALID):
    from iios.investment.decision.reasoning.logic_validator import LogicValidationResult
    return LogicValidationResult(
        status=status,
        hypothesis_issues=0,
        argument_gaps=0,
        contradiction_count=0,
        consistency_score=100.0 if status == LogicValidationStatus.VALID else 50.0,
        issues=(),
    )


# ========================= ReasoningQualityScore =========================

class TestReasoningQualityScore:
    def test_all_max(self):
        qs = compute_reasoning_score(100, 100, 100, 100, 100)
        assert qs.overall == pytest.approx(100.0)

    def test_all_zero(self):
        qs = compute_reasoning_score(0, 0, 0, 0, 0)
        assert qs.overall == 0.0

    def test_grade_a(self):
        qs = compute_reasoning_score(95, 95, 95, 95, 95)
        assert qs.grade == "A"

    def test_grade_f(self):
        qs = compute_reasoning_score(10, 10, 10, 10, 10)
        assert qs.grade == "F"

    def test_to_dict_keys(self):
        qs = compute_reasoning_score(80, 80, 80, 80, 80)
        d = qs.to_dict()
        for k in ("overall", "grade", "completeness", "consistency", "transparency",
                  "evidence_coverage", "chain_depth", "computed_at"):
            assert k in d

    def test_weights_sum_to_1(self):
        total = sum(dim.default_weight for dim in ReasoningQualityDimension)
        assert total == pytest.approx(1.0)


# ========================= ReasoningQuality ==============================

class TestReasoningQuality:
    def test_full_chain_high_score(self, decision_id):
        rq    = ReasoningQuality()
        chain = _full_chain(decision_id)
        lr    = _logic_result(LogicValidationStatus.VALID)
        qs    = rq.score(chain, lr, total_evidence_items=9)
        assert qs.overall >= 50.0   # full step coverage + valid logic

    def test_partial_chain_lower_score(self, decision_id):
        rq    = ReasoningQuality()
        full  = _full_chain(decision_id)
        part  = _partial_chain(decision_id)
        lr    = _logic_result()
        full_q = rq.score(full, lr, total_evidence_items=9).overall
        part_q = rq.score(part, lr, total_evidence_items=9).overall
        assert full_q >= part_q

    def test_contradictory_lowers_consistency(self, decision_id):
        rq    = ReasoningQuality()
        chain = _full_chain(decision_id)
        valid_qs = rq.score(chain, _logic_result(LogicValidationStatus.VALID), 9)
        cont_qs  = rq.score(chain, _logic_result(LogicValidationStatus.CONTRADICTORY), 9)
        assert valid_qs.consistency > cont_qs.consistency

    def test_transparency_full_when_all_traced(self, decision_id):
        rq    = ReasoningQuality()
        chain = _full_chain(decision_id)
        lr    = _logic_result()
        qs    = rq.score(chain, lr, total_evidence_items=9)
        assert qs.transparency == 100.0  # all steps have trace_ids


# ========================= ReasoningConfidence ===========================

class TestReasoningConfidence:
    def test_compute_returns_score(self, decision_id):
        rc    = ReasoningConfidence()
        chain = _full_chain(decision_id)
        lr    = _logic_result()
        conf  = rc.compute(chain, lr, total_evidence_items=9)
        assert 0.0 <= conf.overall <= 100.0

    def test_valid_logic_higher_conf(self, decision_id):
        rc    = ReasoningConfidence()
        chain = _full_chain(decision_id)
        valid = rc.compute(chain, _logic_result(LogicValidationStatus.VALID), 9)
        insuf = rc.compute(chain, _logic_result(LogicValidationStatus.INSUFFICIENT), 9)
        assert valid.logic_confidence > insuf.logic_confidence

    def test_to_dict(self, decision_id):
        rc   = ReasoningConfidence()
        conf = rc.compute(_full_chain(decision_id), _logic_result(), 9)
        d    = conf.to_dict()
        assert "overall" in d
        assert "step_confidence" in d


# ========================= ReasoningHealth ===============================

class TestReasoningHealth:
    def test_empty(self):
        rh = ReasoningHealth()
        r  = rh.report()
        assert r.total_runs == 0
        assert r.success_rate == 0.0

    def test_record_success(self, decision_id):
        rh = ReasoningHealth()
        qs = compute_reasoning_score(80, 80, 80, 80, 80)
        rh.record_success(qs, 120.0)
        r = rh.report()
        assert r.total_runs == 1
        assert r.successful_runs == 1
        assert r.avg_quality == pytest.approx(qs.overall)
        assert r.avg_duration_ms == pytest.approx(120.0)

    def test_record_failure(self):
        rh = ReasoningHealth()
        rh.record_failure()
        r = rh.report()
        assert r.failed_runs == 1

    def test_reset(self):
        rh = ReasoningHealth()
        rh.record_failure()
        rh.reset()
        assert rh.report().total_runs == 0

    def test_grade_distribution(self):
        rh = ReasoningHealth()
        rh.record_success(compute_reasoning_score(90, 90, 90, 90, 90), 50.0)
        r  = rh.report()
        assert "A" in r.grade_distribution

    def test_to_dict(self):
        rh = ReasoningHealth()
        d  = rh.report().to_dict()
        assert "success_rate" in d
        assert "grade_distribution" in d
