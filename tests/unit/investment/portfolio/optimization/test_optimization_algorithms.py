"""test_optimization_algorithms.py — Tests for all 13 optimization algorithms."""
import math
import pytest

from iios.investment.portfolio.optimization.optimization_engine import (
    AssetProxy,
    EqualWeightOptimizer,
    MinimumVarianceOptimizer,
    RiskParityOptimizer,
    EqualRiskContributionOptimizer,
    MaximumDiversificationOptimizer,
    MaximumSharpeOptimizer,
    MaximumSortinoOptimizer,
    MaximumCalmarOptimizer,
    MeanVarianceOptimizer,
    MaximumUtilityOptimizer,
    MinimumTurnoverOptimizer,
    BlackLittermanOptimizer,
    HierarchicalRiskParityOptimizer,
)
from iios.investment.portfolio.optimization.optimization_types import (
    ConvergenceStatus,
    OptimizationMethod,
)

WEIGHT_TOL = 1e-4


def _weights_valid(weights: dict, n: int) -> bool:
    """Weights sum to 1, all non-negative, all symbols present."""
    if len(weights) != n:
        return False
    if any(w < -WEIGHT_TOL for w in weights.values()):
        return False
    if abs(sum(weights.values()) - 1.0) > WEIGHT_TOL:
        return False
    return True


@pytest.fixture
def assets_5(five_assets):
    return five_assets


ALL_ALGOS = [
    EqualWeightOptimizer(),
    MinimumVarianceOptimizer(),
    RiskParityOptimizer(),
    EqualRiskContributionOptimizer(),
    MaximumDiversificationOptimizer(),
    MaximumSharpeOptimizer(),
    MaximumSortinoOptimizer(),
    MaximumCalmarOptimizer(),
    MeanVarianceOptimizer(),
    MaximumUtilityOptimizer(),
    MinimumTurnoverOptimizer(),
    BlackLittermanOptimizer(),
    HierarchicalRiskParityOptimizer(),
]


class TestAllAlgorithmsReturnValidWeights:
    @pytest.mark.parametrize("algo", ALL_ALGOS, ids=[type(a).__name__ for a in ALL_ALGOS])
    def test_weights_sum_to_one(self, algo, five_assets):
        weights, conv = algo.optimize(five_assets, min_weight=0.0, max_weight=0.40)
        total = sum(weights.values())
        assert abs(total - 1.0) < WEIGHT_TOL, f"{type(algo).__name__}: sum={total}"

    @pytest.mark.parametrize("algo", ALL_ALGOS, ids=[type(a).__name__ for a in ALL_ALGOS])
    def test_weights_non_negative(self, algo, five_assets):
        weights, _ = algo.optimize(five_assets, min_weight=0.0, max_weight=0.40)
        for sym, w in weights.items():
            assert w >= -WEIGHT_TOL, f"{type(algo).__name__}: {sym}={w}"

    @pytest.mark.parametrize("algo", ALL_ALGOS, ids=[type(a).__name__ for a in ALL_ALGOS])
    def test_all_symbols_present(self, algo, five_assets):
        weights, _ = algo.optimize(five_assets, min_weight=0.0, max_weight=0.40)
        symbols = {a.symbol for a in five_assets}
        assert set(weights.keys()) == symbols

    @pytest.mark.parametrize("algo", ALL_ALGOS, ids=[type(a).__name__ for a in ALL_ALGOS])
    def test_max_weight_respected(self, algo, five_assets):
        weights, _ = algo.optimize(five_assets, min_weight=0.0, max_weight=0.30)
        for w in weights.values():
            assert w <= 0.30 + WEIGHT_TOL

    @pytest.mark.parametrize("algo", ALL_ALGOS, ids=[type(a).__name__ for a in ALL_ALGOS])
    def test_convergence_result_has_status(self, algo, five_assets):
        _, conv = algo.optimize(five_assets)
        assert conv.status in ConvergenceStatus


class TestEqualWeight:
    def test_equal_weights(self, five_assets):
        algo = EqualWeightOptimizer()
        weights, _ = algo.optimize(five_assets)
        for w in weights.values():
            assert abs(w - 0.20) < WEIGHT_TOL

    def test_method(self):
        assert EqualWeightOptimizer().method == OptimizationMethod.EQUAL_WEIGHT


class TestMinimumVariance:
    def test_high_risk_assets_get_lower_weight(self, five_assets):
        algo = MinimumVarianceOptimizer()
        weights, _ = algo.optimize(five_assets, min_weight=0.0, max_weight=0.50)
        # Asset E has highest risk (0.35), should have lower weight than A (0.25)
        assert weights["E"] <= weights["A"] + WEIGHT_TOL


class TestMaximumSharpe:
    def test_high_sharpe_asset_gets_higher_weight(self, five_assets):
        # Asset B has best sharpe: 0.68/0.20=3.4 vs Asset E: 0.58/0.35=1.66
        algo = MaximumSharpeOptimizer()
        weights, _ = algo.optimize(five_assets, min_weight=0.0, max_weight=0.60)
        assert weights["B"] >= weights["E"] - WEIGHT_TOL


class TestMinimumTurnover:
    def test_weights_equal_prior(self, five_assets):
        algo = MinimumTurnoverOptimizer()
        weights, _ = algo.optimize(five_assets)
        for a in five_assets:
            assert abs(weights[a.symbol] - a.prior_weight) < WEIGHT_TOL


class TestHierarchicalRiskParity:
    def test_concentrates_within_sectors(self):
        # tech cluster should have more weight than single-asset clusters
        assets = [
            AssetProxy("T1", 0.7, 0.2, 0.8, 0.20, sector="tech"),
            AssetProxy("T2", 0.6, 0.2, 0.7, 0.20, sector="tech"),
            AssetProxy("T3", 0.6, 0.2, 0.7, 0.20, sector="tech"),
            AssetProxy("E1", 0.5, 0.3, 0.6, 0.20, sector="energy"),
            AssetProxy("F1", 0.5, 0.4, 0.6, 0.20, sector="finance"),
        ]
        algo = HierarchicalRiskParityOptimizer()
        weights, _ = algo.optimize(assets, min_weight=0.0, max_weight=0.50)
        tech_total = weights["T1"] + weights["T2"] + weights["T3"]
        # Tech cluster (3 assets) should get ~1/3 of portfolio
        assert 0.15 < tech_total < 0.70


class TestSingleAsset:
    @pytest.mark.parametrize("algo", ALL_ALGOS, ids=[type(a).__name__ for a in ALL_ALGOS])
    def test_single_asset_gets_full_weight(self, algo):
        assets = [AssetProxy("ONLY", 0.65, 0.30, 0.70, 1.0, sector="equity")]
        weights, _ = algo.optimize(assets, min_weight=0.0, max_weight=1.0)
        assert abs(weights["ONLY"] - 1.0) < WEIGHT_TOL
