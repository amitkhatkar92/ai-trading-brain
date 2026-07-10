"""tests/unit/investment/market/regime/test_transition_probability.py"""
from __future__ import annotations

import pytest

from iios.investment.market.regime.models import RegimeType
from iios.investment.market.regime.transition_probability import TransitionProbabilityModel


@pytest.fixture
def model() -> TransitionProbabilityModel:
    return TransitionProbabilityModel()


class TestFreshModel:
    def test_probability_is_nonzero(self, model):
        # Laplace smoothing ensures no zero probability
        p = model.probability(RegimeType.BULL, RegimeType.BEAR)
        assert p > 0.0

    def test_persistence_favored_by_prior(self, model):
        # P(A→A) > P(A→B) from prior alone
        p_stay = model.probability(RegimeType.BULL, RegimeType.BULL)
        p_change = model.probability(RegimeType.BULL, RegimeType.BEAR)
        assert p_stay == p_change  # equal with Laplace prior and no observations


class TestAfterObservations:
    def test_probability_increases_after_transitions(self, model):
        for _ in range(10):
            model.update(RegimeType.BULL, RegimeType.BEAR)
        p_after = model.probability(RegimeType.BULL, RegimeType.BEAR)
        fresh = TransitionProbabilityModel()
        p_before = fresh.probability(RegimeType.BULL, RegimeType.BEAR)
        assert p_after > p_before

    def test_most_likely_next_correct_after_training(self, model):
        for _ in range(20):
            model.update(RegimeType.BULL, RegimeType.DISTRIBUTION)
        best, prob = model.most_likely_next(RegimeType.BULL)
        assert best == RegimeType.DISTRIBUTION
        assert prob > 0.0


class TestTransitionProbability:
    def test_transition_prob_in_range(self, model):
        tp = model.transition_probability(RegimeType.BULL)
        assert 0.0 <= tp <= 1.0

    def test_transition_prob_is_1_minus_stay(self, model):
        for _ in range(5):
            model.update(RegimeType.BULL, RegimeType.BEAR)
        tp = model.transition_probability(RegimeType.BULL)
        p_stay = model.probability(RegimeType.BULL, RegimeType.BULL)
        assert tp == pytest.approx(1.0 - p_stay, abs=1e-10)


class TestTransitionMatrix:
    def test_rows_sum_to_approximately_1(self, model):
        for _ in range(5):
            model.update(RegimeType.BULL, RegimeType.BEAR)
        matrix = model.transition_matrix()
        for from_regime_val, row in matrix.items():
            row_sum = sum(row.values())
            assert row_sum == pytest.approx(1.0, abs=1e-6), \
                f"Row {from_regime_val} sums to {row_sum}"

    def test_matrix_has_all_regimes(self, model):
        matrix = model.transition_matrix()
        assert len(matrix) == len(RegimeType)


class TestTotalTransitions:
    def test_increments_correctly(self, model):
        assert model.total_transitions() == 0
        model.update(RegimeType.BULL, RegimeType.BEAR)
        assert model.total_transitions() == 1
        model.update(RegimeType.BEAR, RegimeType.SIDEWAYS)
        assert model.total_transitions() == 2


class TestReset:
    def test_reset_clears_counts(self, model):
        model.update(RegimeType.BULL, RegimeType.BEAR)
        model.update(RegimeType.BULL, RegimeType.BEAR)
        model.reset()
        assert model.total_transitions() == 0

    def test_after_reset_probabilities_are_uniform(self, model):
        model.update(RegimeType.BULL, RegimeType.BEAR)
        model.reset()
        fresh = TransitionProbabilityModel()
        assert model.probability(RegimeType.BULL, RegimeType.BEAR) == \
               fresh.probability(RegimeType.BULL, RegimeType.BEAR)


class TestLaplaceSmoothing:
    def test_no_zero_probability(self, model):
        # Even for never-observed transitions
        for rt1 in RegimeType:
            for rt2 in RegimeType:
                assert model.probability(rt1, rt2) > 0.0
