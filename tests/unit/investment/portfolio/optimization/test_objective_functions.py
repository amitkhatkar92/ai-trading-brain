"""test_objective_functions.py — Tests for ObjectiveEvaluator."""
import math
import pytest

from iios.investment.portfolio.optimization.objective_engine import ObjectiveEvaluator
from iios.investment.portfolio.optimization.optimization_engine import AssetProxy
from iios.investment.portfolio.optimization.optimization_types import ObjectiveType


@pytest.fixture
def evaluator():
    return ObjectiveEvaluator()


@pytest.fixture
def assets_equal():
    return [
        AssetProxy("A", expected_return=0.70, risk=0.25, confidence=0.80, prior_weight=0.50),
        AssetProxy("B", expected_return=0.50, risk=0.20, confidence=0.70, prior_weight=0.50),
    ]


@pytest.fixture
def equal_weights():
    return {"A": 0.50, "B": 0.50}


class TestObjectiveEvaluatorBasic:
    def test_returns_evaluation(self, evaluator, assets_equal, equal_weights):
        ev = evaluator.evaluate(equal_weights, assets_equal, ObjectiveType.MAXIMIZE_SHARPE)
        assert ev.expected_return > 0
        assert ev.portfolio_risk > 0
        assert ev.value != 0

    def test_expected_return_weighted_avg(self, evaluator, assets_equal, equal_weights):
        ev = evaluator.evaluate(equal_weights, assets_equal, ObjectiveType.MAXIMIZE_RETURN)
        # 0.5*0.70 + 0.5*0.50 = 0.60
        assert abs(ev.expected_return - 0.60) < 1e-6

    def test_all_objectives_return_float(self, evaluator, assets_equal, equal_weights):
        for obj in ObjectiveType:
            ev = evaluator.evaluate(equal_weights, assets_equal, obj)
            assert isinstance(ev.value, float)


class TestObjectiveComparisons:
    def test_higher_return_weights_improve_return_objective(self, evaluator, assets_equal):
        # More weight on A (higher return 0.70)
        w_better = {"A": 0.80, "B": 0.20}
        w_worse  = {"A": 0.20, "B": 0.80}
        ev_b = evaluator.evaluate(w_better, assets_equal, ObjectiveType.MAXIMIZE_RETURN)
        ev_w = evaluator.evaluate(w_worse,  assets_equal, ObjectiveType.MAXIMIZE_RETURN)
        assert ev_b.value > ev_w.value

    def test_lower_risk_weights_reduce_risk_objective(self, evaluator, assets_equal):
        # More weight on B (lower risk 0.20)
        w_low  = {"A": 0.20, "B": 0.80}
        w_high = {"A": 0.80, "B": 0.20}
        ev_low  = evaluator.evaluate(w_low,  assets_equal, ObjectiveType.MINIMIZE_RISK)
        ev_high = evaluator.evaluate(w_high, assets_equal, ObjectiveType.MINIMIZE_RISK)
        # MINIMIZE_RISK: higher value = less risk (negated)
        assert ev_low.value > ev_high.value

    def test_diversification_ratio_positive(self, evaluator, assets_equal, equal_weights):
        ev = evaluator.evaluate(equal_weights, assets_equal, ObjectiveType.MAXIMIZE_DIVERSIFICATION)
        assert ev.diversification_ratio > 0

    def test_sharpe_proxy_formula(self, evaluator, assets_equal, equal_weights):
        ev = evaluator.evaluate(equal_weights, assets_equal, ObjectiveType.MAXIMIZE_SHARPE)
        expected_sharpe = ev.expected_return / max(1e-8, ev.portfolio_risk)
        assert abs(ev.sharpe_proxy - expected_sharpe) < 1e-6


class TestEdgeCases:
    def test_zero_weights_still_evaluates(self, evaluator):
        assets = [AssetProxy("X", 0.5, 0.3, 0.7, 0.0)]
        weights = {"X": 1.0}
        ev = evaluator.evaluate(weights, assets, ObjectiveType.MAXIMIZE_SHARPE)
        assert ev.portfolio_risk > 0

    def test_single_asset(self, evaluator):
        assets  = [AssetProxy("Z", 0.65, 0.25, 0.80, 1.0)]
        weights = {"Z": 1.0}
        ev = evaluator.evaluate(weights, assets, ObjectiveType.MAXIMIZE_RETURN)
        assert abs(ev.expected_return - 0.65) < 1e-6
