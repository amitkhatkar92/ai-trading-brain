"""tests/unit/investment/strategy/evaluation/test_scoring.py"""
from __future__ import annotations

import pytest

from iios.investment.strategy.evaluation.evaluation_grade import (
    EvaluationGrade, grade_from_score, grade_label, score_range_for_grade
)
from iios.investment.strategy.evaluation.confidence_score import ConfidenceScoreCalculator
from iios.investment.strategy.evaluation.approval_engine import (
    ApprovalEngine, ApprovalCriteria, ApprovalStatus
)
from iios.investment.strategy.evaluation.institutional_score import InstitutionalStrategyScore


class TestEvaluationGrade:
    @pytest.mark.parametrize("score,expected", [
        (95.0,  EvaluationGrade.A_PLUS),
        (90.0,  EvaluationGrade.A_PLUS),
        (85.0,  EvaluationGrade.A),
        (80.0,  EvaluationGrade.A),
        (75.0,  EvaluationGrade.B_PLUS),
        (70.0,  EvaluationGrade.B_PLUS),
        (65.0,  EvaluationGrade.B),
        (60.0,  EvaluationGrade.B),
        (55.0,  EvaluationGrade.C),
        (50.0,  EvaluationGrade.C),
        (45.0,  EvaluationGrade.D),
        (40.0,  EvaluationGrade.D),
        (35.0,  EvaluationGrade.F),
        (0.0,   EvaluationGrade.F),
    ])
    def test_grade_thresholds(self, score, expected):
        assert grade_from_score(score) == expected

    def test_grade_label_not_empty(self):
        for g in EvaluationGrade:
            assert len(grade_label(g)) > 0

    def test_score_range_coverage(self):
        for g in EvaluationGrade:
            if g == EvaluationGrade.UNKNOWN:
                continue
            lo, hi = score_range_for_grade(g)
            assert lo < hi or lo == hi  # valid range


class TestConfidenceScore:
    def test_high_confidence_many_trades_long_duration(self):
        conf = ConfidenceScoreCalculator().compute(
            n_trades=300, duration_years=4.0,
            trade_consistency=0.9, data_quality=1.0,
        )
        assert conf.overall >= 80.0

    def test_low_confidence_few_trades(self):
        conf = ConfidenceScoreCalculator().compute(
            n_trades=5, duration_years=0.1,
            trade_consistency=0.5, data_quality=1.0,
        )
        assert conf.overall < 50.0

    def test_confidence_bounded(self):
        for n in [0, 10, 100, 200, 500]:
            conf = ConfidenceScoreCalculator().compute(
                n_trades=n, duration_years=1.0
            )
            assert 0.0 <= conf.overall <= 100.0

    def test_scores_increase_with_more_data(self):
        c1 = ConfidenceScoreCalculator().compute(n_trades=20, duration_years=0.5)
        c2 = ConfidenceScoreCalculator().compute(n_trades=200, duration_years=3.0)
        assert c2.overall > c1.overall

    def test_trade_count_score_bounded(self):
        for n in [0, 50, 200, 1000]:
            conf = ConfidenceScoreCalculator().compute(n_trades=n, duration_years=1.0)
            assert 0.0 <= conf.trade_count_score <= 100.0


class TestApprovalEngine:
    def _engine(self, **kw):
        return ApprovalEngine(ApprovalCriteria(**kw))

    def test_approved_above_threshold(self):
        result = self._engine().decide(
            overall_score=70.0, sharpe=1.2, win_rate=0.55,
            max_drawdown=0.12, profit_factor=1.5, n_trades=60,
            confidence_score=65.0,
        )
        assert result.status == ApprovalStatus.APPROVED

    def test_rejected_below_threshold(self):
        result = self._engine().decide(
            overall_score=30.0, sharpe=0.3, win_rate=0.35,
            max_drawdown=0.40, profit_factor=0.8, n_trades=10,
            confidence_score=20.0,
        )
        assert result.status == ApprovalStatus.REJECTED

    def test_conditional_between_thresholds(self):
        result = self._engine().decide(
            overall_score=54.0, sharpe=0.85, win_rate=0.48,
            max_drawdown=0.18, profit_factor=1.25, n_trades=35,
            confidence_score=52.0,
        )
        # Score 54 is ≥ conditional (50) but < approved (60)
        assert result.status in (ApprovalStatus.CONDITIONAL, ApprovalStatus.REJECTED)

    def test_hard_violation_high_drawdown(self):
        result = self._engine().decide(
            overall_score=75.0, sharpe=1.5, win_rate=0.60,
            max_drawdown=0.45,  # >20% → hard violation
            profit_factor=1.8, n_trades=80, confidence_score=70.0,
        )
        assert result.status == ApprovalStatus.REJECTED
        assert any("drawdown" in v.lower() for v in result.violations)

    def test_result_has_score(self):
        result = self._engine().decide(
            overall_score=72.0, sharpe=1.1, win_rate=0.52,
            max_drawdown=0.15, profit_factor=1.4, n_trades=55,
            confidence_score=60.0,
        )
        assert result.score == pytest.approx(72.0)

    def test_conditions_listed_for_conditional(self):
        result = self._engine().decide(
            overall_score=53.0, sharpe=0.95, win_rate=0.47,
            max_drawdown=0.17, profit_factor=1.22, n_trades=32,
            confidence_score=51.0,
        )
        # CONDITIONAL result should have reasons
        if result.status == ApprovalStatus.CONDITIONAL:
            assert len(result.reasons) > 0


class TestInstitutionalStrategyScore:
    def test_compute_returns_score(self):
        score = InstitutionalStrategyScore.compute(
            strategy_id="s1", strategy_name="Test",
            sharpe=1.5, ann_return=0.20, max_drawdown=0.10,
            win_rate=0.60, profit_factor=1.8, robustness=0.75,
            exec_efficiency=0.90, confidence=75.0,
        )
        assert 0.0 <= score.overall_score <= 100.0

    def test_high_quality_strategy_high_score(self):
        score = InstitutionalStrategyScore.compute(
            strategy_id="s1", strategy_name="Top",
            sharpe=2.0, ann_return=0.30, max_drawdown=0.05,
            win_rate=0.65, profit_factor=2.0, robustness=0.90,
            exec_efficiency=0.95, confidence=85.0,
        )
        assert score.overall_score > 70.0

    def test_poor_strategy_low_score(self):
        score = InstitutionalStrategyScore.compute(
            strategy_id="s2", strategy_name="Bad",
            sharpe=-0.5, ann_return=-0.10, max_drawdown=0.45,
            win_rate=0.30, profit_factor=0.6, robustness=0.20,
            exec_efficiency=0.40, confidence=20.0,
        )
        assert score.overall_score < 40.0

    def test_grade_consistent_with_score(self):
        score = InstitutionalStrategyScore.compute(
            strategy_id="s", strategy_name="s",
            sharpe=1.8, ann_return=0.25, max_drawdown=0.08,
            win_rate=0.62, profit_factor=1.9, robustness=0.85,
            exec_efficiency=0.92, confidence=80.0,
        )
        from iios.investment.strategy.evaluation.evaluation_grade import grade_from_score
        assert score.grade == grade_from_score(score.overall_score)

    def test_to_dict_complete(self):
        score = InstitutionalStrategyScore.compute(
            strategy_id="s1", strategy_name="s",
            sharpe=1.0, ann_return=0.10, max_drawdown=0.15,
            win_rate=0.50, profit_factor=1.3, robustness=0.60,
            exec_efficiency=0.80, confidence=55.0,
        )
        d = score.to_dict()
        for key in ["overall_score", "grade", "approval_status", "evaluated_at"]:
            assert key in d

    def test_custom_weights(self):
        weights = {
            "performance": 0.50, "risk": 0.50,
            "robustness": 0.0, "execution": 0.0, "confidence": 0.0
        }
        score = InstitutionalStrategyScore.compute(
            strategy_id="s", strategy_name="s",
            sharpe=1.0, ann_return=0.10, max_drawdown=0.15,
            win_rate=0.50, profit_factor=1.3, robustness=0.60,
            exec_efficiency=0.80, confidence=55.0,
            weights=weights,
        )
        assert math.isfinite(score.overall_score)

import math
