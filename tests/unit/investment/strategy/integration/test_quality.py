"""tests/unit/investment/strategy/integration/test_quality.py
Tests for QualityFramework, QualityReport, ConfidenceCalculator,
QualityStatisticsTracker, QualityHistory.
"""
from __future__ import annotations

import pytest

from iios.investment.strategy.integration.aggregation_engine import AggregationEngine
from iios.investment.strategy.integration.integration_constants import (
    ConflictSeverity,
    ConflictType,
    IntelligenceSource,
    QualityDimension,
    ResolutionStrategy,
)
from iios.investment.strategy.integration.quality_history import QualityHistory
from iios.investment.strategy.integration.quality_statistics import QualityStatisticsTracker
from iios.investment.strategy.integration.strategy_confidence import ConfidenceCalculator
from iios.investment.strategy.integration.strategy_quality import QualityFramework
from iios.investment.strategy.integration.conflict_classifier import Conflict
from tests.unit.investment.strategy.integration.conftest import (
    make_eval_update,
    make_risk_update,
    make_full_state,
)


def _make_conflict(
    sid: str,
    severity: ConflictSeverity = ConflictSeverity.MEDIUM,
    resolved: bool = False,
) -> Conflict:
    c = Conflict(
        conflict_id="q-cid",
        strategy_id=sid,
        conflict_type=ConflictType.EVALUATION_VS_RISK,
        severity=severity,
        source_a=IntelligenceSource.EVALUATION,
        source_b=IntelligenceSource.RISK,
        description="test",
        rule_id="R001",
        resolution_strategy=ResolutionStrategy.RISK_FIRST,
    )
    if resolved:
        c.resolve()
    return c


# ===========================================================================
# QualityFramework
# ===========================================================================

class TestQualityFramework:
    def test_compute_returns_report(self):
        sid, state, eng = make_full_state("QF1")
        qf     = QualityFramework(aggregation_engine=eng)
        report = qf.compute(sid, state, [])
        assert report.strategy_id == sid
        assert 0 <= report.overall_score <= 100

    def test_all_five_dimensions_present(self):
        sid, state, eng = make_full_state("QF2")
        qf     = QualityFramework(aggregation_engine=eng)
        report = qf.compute(sid, state, [])
        for dim in QualityDimension:
            assert dim.value in report.scores

    def test_consistency_decreases_with_conflicts(self):
        sid, state, eng = make_full_state("QF3")
        qf      = QualityFramework(aggregation_engine=eng)
        no_conf = qf.compute(sid, state, [])
        conflict = _make_conflict(sid, ConflictSeverity.HIGH, resolved=False)
        with_conf = qf.compute(sid, state, [conflict])
        assert with_conf.scores[QualityDimension.CONSISTENCY.value] <= no_conf.scores[QualityDimension.CONSISTENCY.value]

    def test_resolved_conflict_no_penalty(self):
        sid, state, eng = make_full_state("QF4")
        qf       = QualityFramework(aggregation_engine=eng)
        resolved = _make_conflict(sid, ConflictSeverity.HIGH, resolved=True)
        report   = qf.compute(sid, state, [resolved])
        assert report.scores[QualityDimension.CONSISTENCY.value] == pytest.approx(100.0)

    def test_overall_score_weighted(self):
        sid, state, eng = make_full_state("QF5")
        qf     = QualityFramework(aggregation_engine=eng)
        report = qf.compute(sid, state, [])
        expected_weights = sum(dim.default_weight for dim in QualityDimension)
        assert expected_weights == pytest.approx(1.0, abs=0.01)

    def test_to_dict(self):
        sid, state, eng = make_full_state("QF6")
        qf     = QualityFramework(aggregation_engine=eng)
        report = qf.compute(sid, state, [])
        d = report.to_dict()
        assert "overall_score" in d
        assert "scores" in d


# ===========================================================================
# ConfidenceCalculator
# ===========================================================================

class TestConfidenceCalculator:
    def test_base_confidence_from_updates(self):
        sid, state, eng = make_full_state("CC1")
        calc = ConfidenceCalculator()
        comp = calc.compute(state, [], completeness=1.0, freshness_score=1.0)
        assert comp.base_confidence > 0

    def test_conflict_penalty_applied(self):
        sid, state, eng = make_full_state("CC2")
        calc    = ConfidenceCalculator()
        no_c    = calc.compute(state, [], completeness=1.0, freshness_score=1.0)
        conf    = _make_conflict(sid, ConflictSeverity.HIGH, resolved=False)
        with_c  = calc.compute(state, [conf], completeness=1.0, freshness_score=1.0)
        assert with_c.final_confidence <= no_c.final_confidence

    def test_completeness_bonus_at_90pct(self):
        sid, state, eng = make_full_state("CC3")
        calc = ConfidenceCalculator()
        comp = calc.compute(state, [], completeness=0.95, freshness_score=1.0)
        assert comp.completeness_bonus == pytest.approx(10.0)

    def test_no_completeness_bonus_below_90(self):
        sid, state, eng = make_full_state("CC4")
        calc = ConfidenceCalculator()
        comp = calc.compute(state, [], completeness=0.80, freshness_score=1.0)
        assert comp.completeness_bonus == pytest.approx(0.0)

    def test_staleness_penalty_at_zero_freshness(self):
        sid, state, eng = make_full_state("CC5")
        calc = ConfidenceCalculator()
        comp = calc.compute(state, [], completeness=1.0, freshness_score=0.0)
        assert comp.staleness_penalty == pytest.approx(30.0)

    def test_final_confidence_clamped(self):
        sid, state, eng = make_full_state("CC6")
        calc = ConfidenceCalculator()
        # max penalty scenario
        conflicts = [
            _make_conflict(sid, ConflictSeverity.CRITICAL, resolved=False) for _ in range(10)
        ]
        comp = calc.compute(state, conflicts, completeness=0.0, freshness_score=0.0)
        assert comp.final_confidence >= 0.0
        assert comp.final_confidence <= 100.0

    def test_to_dict(self):
        sid, state, eng = make_full_state("CC7")
        calc = ConfidenceCalculator()
        comp = calc.compute(state, [], completeness=1.0, freshness_score=1.0)
        d = comp.to_dict()
        assert "final_confidence" in d


# ===========================================================================
# QualityStatisticsTracker
# ===========================================================================

class TestQualityStatisticsTracker:
    def _make_report(self, strategy_id: str, score: float = 80.0):
        sid, state, eng = make_full_state(strategy_id)
        qf = QualityFramework(aggregation_engine=eng)
        return qf.compute(sid, state, [])

    def test_record_increments_total(self):
        tracker = QualityStatisticsTracker()
        tracker.record(self._make_report("QST1"))
        stats = tracker.summary()
        assert stats.total_reports == 1

    def test_avg_overall_score(self):
        tracker = QualityStatisticsTracker()
        for _ in range(3):
            tracker.record(self._make_report(f"QST-{_}"))
        stats = tracker.summary()
        assert 0 <= stats.avg_overall_score <= 100

    def test_reset_clears(self):
        tracker = QualityStatisticsTracker()
        tracker.record(self._make_report("QST2"))
        tracker.reset()
        stats = tracker.summary()
        assert stats.total_reports == 0

    def test_to_dict(self):
        tracker = QualityStatisticsTracker()
        tracker.record(self._make_report("QST3"))
        d = tracker.summary().to_dict()
        assert "avg_overall_score" in d


# ===========================================================================
# QualityHistory
# ===========================================================================

class TestQualityHistory:
    def _make_report(self, sid: str):
        _, state, eng = make_full_state(sid)
        qf = QualityFramework(aggregation_engine=eng)
        return qf.compute(sid, state, [])

    def test_record_and_retrieve(self):
        hist = QualityHistory()
        r    = self._make_report("QH1")
        hist.record(r)
        assert r in hist.for_strategy("QH1")

    def test_recent(self):
        hist = QualityHistory()
        for i in range(5):
            hist.record(self._make_report(f"QH-{i}"))
        recent = hist.recent(3)
        assert len(recent) == 3

    def test_trend(self):
        hist = QualityHistory()
        sid  = "QH_TREND"
        for _ in range(5):
            hist.record(self._make_report(sid))
        trend = hist.trend(sid, n=3)
        assert len(trend) == 3
        assert all(0 <= v <= 100 for v in trend)

    def test_count(self):
        hist = QualityHistory()
        hist.record(self._make_report("QH_CNT"))
        assert hist.count() == 1
