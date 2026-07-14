"""tests/unit/investment/decision/integration/test_quality.py
Tests for DecisionQualityEvaluator, IntegrationConfidenceCalculator,
QualityHistory, QualityStatisticsTracker.
"""
from __future__ import annotations

import pytest

from iios.investment.decision.integration.aggregation_engine import AggregationEngine
from iios.investment.decision.integration.conflict_engine import ConflictEngine
from iios.investment.decision.integration.consistency_validator import ConsistencyValidator
from iios.investment.decision.integration.decision_confidence import (
    IntegrationConfidenceCalculator,
)
from iios.investment.decision.integration.decision_quality import DecisionQualityEvaluator
from iios.investment.decision.integration.integration_constants import (
    ComponentId,
    QualityGrade,
)
from iios.investment.decision.integration.quality_history import QualityHistory
from iios.investment.decision.integration.quality_statistics import QualityStatisticsTracker


def _make_snap(pipeline):
    did, sid, ev, rs, cs, ri, ex, cm = pipeline
    eng   = AggregationEngine()
    state = eng.create(
        decision_id=did+"_DEC", subject_id=sid, subject_type="equity",
        evidence=ev, reasoning=rs, confidence=cs, risk=ri,
        explanation=ex, committee=cm,
    )
    return state.snapshot()


class TestIntegrationConfidenceCalculator:
    def test_in_range(self, _rich_pipeline):
        snap = _make_snap(_rich_pipeline)
        calc = IntegrationConfidenceCalculator()
        conf = calc.calculate(snap)
        assert 0.0 <= conf <= 100.0

    def test_both_states_in_valid_range(self, _rich_pipeline):
        did, sid, ev, rs, cs, ri, ex, cm = _rich_pipeline
        eng   = AggregationEngine()

        full  = eng.create(did+"_DEC", sid, "equity",
                           evidence=ev, reasoning=rs, confidence=cs,
                           risk=ri, explanation=ex, committee=cm)
        part  = eng.create(did+"_DEC2", sid, "equity", evidence=ev)

        calc  = IntegrationConfidenceCalculator()
        c_full = calc.calculate(full.snapshot())
        c_part = calc.calculate(part.snapshot())
        assert 0.0 <= c_full <= 100.0
        assert 0.0 <= c_part <= 100.0

    def test_zero_when_no_components(self):
        eng  = AggregationEngine()
        s    = eng.create("D1", "INFY", "equity")
        calc = IntegrationConfidenceCalculator()
        assert calc.calculate(s.snapshot()) == 0.0


class TestDecisionQualityEvaluator:
    def test_quality_in_range(self, _rich_pipeline):
        snap = _make_snap(_rich_pipeline)
        vr   = ConsistencyValidator().validate(snap)
        cr   = ConflictEngine().run(snap)
        calc = IntegrationConfidenceCalculator()
        conf = calc.calculate(snap)
        ev   = DecisionQualityEvaluator()
        q    = ev.evaluate(snap, vr, cr, conf)
        assert 0.0 <= q <= 100.0

    def test_intelligence_score_in_range(self, _rich_pipeline):
        snap = _make_snap(_rich_pipeline)
        vr   = ConsistencyValidator().validate(snap)
        cr   = ConflictEngine().run(snap)
        calc = IntegrationConfidenceCalculator()
        conf = calc.calculate(snap)
        ev   = DecisionQualityEvaluator()
        q    = ev.evaluate(snap, vr, cr, conf)
        i    = ev.overall_intelligence_score(snap, conf, q, cr)
        assert 0.0 <= i <= 100.0

    def test_quality_grade_from_score(self):
        assert QualityGrade.from_score(90) == QualityGrade.A
        assert QualityGrade.from_score(72) == QualityGrade.B
        assert QualityGrade.from_score(57) == QualityGrade.C
        assert QualityGrade.from_score(41) == QualityGrade.D
        assert QualityGrade.from_score(20) == QualityGrade.F


class TestQualityHistory:
    def test_record_and_retrieve(self):
        h = QualityHistory()
        h.record("D1", "INFY", 75.0, 80.0, 70.0, 1.0)
        recs = h.for_subject("INFY")
        assert len(recs) == 1

    def test_quality_series(self):
        h = QualityHistory()
        h.record("D1", "INFY", 75.0, 80.0, 70.0, 1.0)
        h.record("D2", "INFY", 85.0, 88.0, 80.0, 1.0)
        series = h.quality_series("INFY")
        assert series == pytest.approx([75.0, 85.0])

    def test_average_quality(self):
        h = QualityHistory()
        h.record("D1", "INFY", 60.0, 65.0, 55.0, 0.9)
        h.record("D2", "TCS",  80.0, 85.0, 75.0, 1.0)
        assert h.average_quality() == pytest.approx(70.0)

    def test_reset(self):
        h = QualityHistory()
        h.record("D1", "INFY", 75.0, 80.0, 70.0, 1.0)
        h.reset()
        assert h.for_subject("INFY") == []

    def test_recent(self):
        h = QualityHistory()
        for i in range(5):
            h.record(f"D{i}", "INFY", float(i * 10), float(i * 10), 50.0, 0.8)
        assert len(h.recent(3)) == 3


class TestQualityStatisticsTracker:
    def test_initial_empty(self):
        t = QualityStatisticsTracker()
        s = t.summary()
        assert s.total_evaluations == 0

    def test_record_tracks_grades(self):
        t = QualityStatisticsTracker()
        t.record(90.0, 1.0)
        t.record(72.0, 0.9)
        t.record(20.0, 0.5)
        s = t.summary()
        assert s.total_evaluations == 3
        assert s.grade_a_count == 1
        assert s.grade_b_count == 1
        assert s.grade_f_count == 1

    def test_high_quality_rate(self):
        t = QualityStatisticsTracker()
        t.record(90.0, 1.0)
        t.record(75.0, 1.0)
        t.record(40.0, 0.7)
        s = t.summary()
        assert s.high_quality_rate == pytest.approx(2 / 3, abs=0.01)

    def test_avg_quality_score(self):
        t = QualityStatisticsTracker()
        t.record(60.0, 1.0)
        t.record(80.0, 1.0)
        s = t.summary()
        assert s.avg_quality_score == pytest.approx(70.0, abs=0.5)

    def test_to_dict(self):
        t = QualityStatisticsTracker()
        d = t.summary().to_dict()
        assert "total_evaluations"  in d
        assert "high_quality_rate"  in d

    def test_reset(self):
        t = QualityStatisticsTracker()
        t.record(80.0, 1.0)
        t.reset()
        assert t.summary().total_evaluations == 0
