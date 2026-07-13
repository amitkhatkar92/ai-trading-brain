"""tests/unit/investment/strategy/learning/test_learning_models.py
Tests for LearningObservation and learning_statistics helpers.
"""
import math
import pytest
from datetime import datetime, timezone

from tests.unit.investment.strategy.learning.conftest import make_observation
from iios.investment.strategy.learning.learning_input import LearningObservation
from iios.investment.strategy.learning.learning_statistics import (
    clamp, safe_div, ewma, rolling_mean, linear_trend, normalised_trend,
    drift_magnitude, drift_score, z_score, coefficient_of_variation,
    consistency_score, improvement_rate, last_n, split_baseline_recent,
    percentile, above_threshold_rate,
)


class TestLearningObservation:
    def test_basic_creation(self):
        obs = make_observation()
        assert obs.strategy_id == "s1"
        assert obs.evaluation_score == 70.0

    def test_observation_id_is_uuid(self):
        obs = make_observation()
        import uuid
        uuid.UUID(obs.observation_id)   # raises if not valid UUID

    def test_frozen(self):
        obs = make_observation()
        with pytest.raises(Exception):
            obs.evaluation_score = 99.0  # type: ignore[misc]

    def test_regime_mismatch_false_when_regime_supported(self):
        obs = make_observation(regime="trending")
        assert not obs.regime_mismatch

    def test_regime_mismatch_true_when_regime_not_supported(self):
        obs = make_observation(regime="bear_market")  # not in supported_regimes
        assert obs.regime_mismatch

    def test_win_loss_ratio(self):
        obs = make_observation(avg_win=0.02, avg_loss=0.01)
        assert pytest.approx(obs.win_loss_ratio, rel=1e-3) == 2.0

    def test_win_loss_ratio_zero_loss(self):
        obs = make_observation(avg_win=0.02, avg_loss=0.0)
        assert obs.win_loss_ratio == 0.0    # safe division

    def test_is_profitable(self):
        obs = make_observation(eval_score=70.0, sharpe=1.2, win_rate=0.55)
        assert obs.is_profitable

    def test_is_profitable_false(self):
        obs = make_observation(eval_score=30.0, sharpe=-0.5, win_rate=0.30, annualized_return=-0.05)
        assert not obs.is_profitable

    def test_has_trade_data(self):
        obs = make_observation(trade_count=10, winning_trades=6, losing_trades=4)
        assert obs.has_trade_data

    def test_has_trade_data_false(self):
        obs = make_observation(trade_count=0, winning_trades=0, losing_trades=0)
        assert not obs.has_trade_data

    def test_composite_quality(self):
        obs = make_observation(eval_score=80.0, risk_score=20.0)
        expected = 80.0 * (1 - 20.0 / 100.0)
        assert pytest.approx(obs.composite_quality, rel=1e-3) == expected

    def test_daily_vol(self):
        obs = make_observation()
        expected = 0.14 / math.sqrt(252)
        assert pytest.approx(obs.daily_vol, rel=1e-3) == expected


class TestLearningStatistics:
    def test_clamp_within(self):
        assert clamp(50.0) == 50.0

    def test_clamp_above(self):
        assert clamp(120.0) == 100.0

    def test_clamp_below(self):
        assert clamp(-5.0) == 0.0

    def test_safe_div_normal(self):
        assert safe_div(10.0, 4.0) == 2.5

    def test_safe_div_zero_den(self):
        assert safe_div(10.0, 0.0, default=99.0) == 99.0

    def test_ewma_empty(self):
        assert ewma([], 0.2) == 0.0

    def test_ewma_single(self):
        assert ewma([50.0], 0.2) == 50.0

    def test_ewma_recent_weighted_higher(self):
        vals = [50.0, 60.0, 70.0, 80.0, 90.0]
        result = ewma(vals, alpha=0.5)
        # Most recent (90) has highest weight; result should be > simple mean
        assert result > sum(vals) / len(vals)

    def test_rolling_mean_full_window(self):
        vals = [10.0, 20.0, 30.0, 40.0, 50.0]
        result = rolling_mean(vals, window=3)
        # rolling_mean uses partial windows for initial elements; check the last 3 (full windows)
        assert len(result) == len(vals)
        assert result[-1] == pytest.approx((30.0 + 40.0 + 50.0) / 3)
        assert result[-2] == pytest.approx((20.0 + 30.0 + 40.0) / 3)

    def test_linear_trend_increasing(self):
        slope = linear_trend([10.0, 20.0, 30.0, 40.0, 50.0])
        assert slope > 0

    def test_linear_trend_decreasing(self):
        slope = linear_trend([50.0, 40.0, 30.0, 20.0, 10.0])
        assert slope < 0

    def test_linear_trend_flat(self):
        slope = linear_trend([30.0, 30.0, 30.0, 30.0])
        assert abs(slope) < 1e-9

    def test_linear_trend_empty(self):
        assert linear_trend([]) == 0.0

    def test_normalised_trend_clamped(self):
        result = normalised_trend([1.0, 50.0, 100.0])
        assert -100.0 <= result <= 100.0

    def test_drift_magnitude_positive(self):
        dm = drift_magnitude(100.0, 110.0)
        assert pytest.approx(dm, rel=1e-3) == 0.10

    def test_drift_magnitude_negative(self):
        dm = drift_magnitude(100.0, 90.0)
        assert pytest.approx(dm, rel=1e-3) == -0.10

    def test_drift_score_zero_change(self):
        # 50 = no change (function uses 50-centred scale)
        assert drift_score(100.0, 100.0) == pytest.approx(50.0)

    def test_drift_score_at_ceiling(self):
        # 30% drop equals ceiling → score 100
        assert drift_score(100.0, 70.0, ceiling=0.30) == 100.0

    def test_z_score_mean(self):
        assert z_score(10.0, 10.0, 2.0) == 0.0

    def test_z_score_one_sigma(self):
        assert pytest.approx(z_score(12.0, 10.0, 2.0)) == 1.0

    def test_cv_uniform(self):
        cv = coefficient_of_variation([50.0, 50.0, 50.0])
        assert cv == 0.0

    def test_consistency_score_perfect(self):
        score = consistency_score([70.0, 70.0, 70.0, 70.0, 70.0])
        assert score == 100.0

    def test_consistency_score_high_variance(self):
        score = consistency_score([10.0, 90.0, 10.0, 90.0, 10.0])
        assert score < 50.0

    def test_improvement_rate_positive(self):
        rate = improvement_rate(50.0, 60.0)
        assert rate > 0

    def test_improvement_rate_negative(self):
        rate = improvement_rate(60.0, 50.0)
        assert rate < 0

    def test_last_n(self):
        assert last_n([1, 2, 3, 4, 5], 3) == [3, 4, 5]

    def test_last_n_more_than_list(self):
        assert last_n([1, 2], 5) == [1, 2]

    def test_split_baseline_recent(self):
        baseline, recent = split_baseline_recent(list(range(20)), 5, 5)
        assert baseline == [0, 1, 2, 3, 4]
        assert recent == [15, 16, 17, 18, 19]

    def test_percentile_median(self):
        vals = list(range(1, 101))
        # Python's statistics.median of [1..100] is 50.5
        assert percentile(vals, 50) == pytest.approx(50.5)

    def test_above_threshold_rate_all_above(self):
        assert above_threshold_rate([80.0, 90.0, 100.0], 70.0) == 1.0

    def test_above_threshold_rate_none_above(self):
        assert above_threshold_rate([10.0, 20.0], 70.0) == 0.0
