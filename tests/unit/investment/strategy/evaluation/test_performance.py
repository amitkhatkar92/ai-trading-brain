"""tests/unit/investment/strategy/evaluation/test_performance.py"""
from __future__ import annotations

import math
import pytest

from iios.investment.strategy.evaluation.performance_statistics import (
    safe_mean, safe_std, percentile, covariance, annualized_return,
    sharpe_ratio, sortino_ratio, calmar_ratio, profit_factor,
    expectancy, beta, alpha, information_ratio, treynor_ratio,
    scale_metric, clamp,
)
from iios.investment.strategy.evaluation.performance_engine import PerformanceEngine
from iios.investment.strategy.evaluation.equity_curve import EquityCurve
from tests.unit.investment.strategy.evaluation.conftest import (
    make_evaluation_input, make_equity_curve
)


# ── pure stats ───────────────────────────────────────────────────────────────

class TestSafeStats:
    def test_mean_empty(self):
        assert safe_mean([]) == 0.0

    def test_mean_values(self):
        assert safe_mean([1.0, 2.0, 3.0]) == pytest.approx(2.0)

    def test_std_empty(self):
        assert safe_std([]) == 0.0

    def test_std_single(self):
        assert safe_std([5.0]) == 0.0

    def test_std_known(self):
        # [0, 1, 2, 3, 4] → std = sqrt(2.5)
        result = safe_std([0.0, 1.0, 2.0, 3.0, 4.0])
        assert result == pytest.approx(math.sqrt(2.5), rel=1e-6)

    def test_percentile_empty(self):
        assert percentile([], 50) == 0.0

    def test_percentile_single(self):
        assert percentile([7.0], 50) == 7.0

    def test_percentile_p50(self):
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert percentile(sorted(xs), 50) == pytest.approx(3.0)

    def test_percentile_p0(self):
        xs = [1.0, 2.0, 3.0]
        assert percentile(sorted(xs), 0) == pytest.approx(1.0)

    def test_percentile_p100(self):
        xs = [1.0, 2.0, 3.0]
        assert percentile(sorted(xs), 100) == pytest.approx(3.0)

    def test_covariance_identical(self):
        xs = [1.0, 2.0, 3.0]
        cov = covariance(xs, xs)
        var = safe_std(xs) ** 2
        assert cov == pytest.approx(var)

    def test_covariance_mismatched_length(self):
        assert covariance([1.0, 2.0], [1.0]) == 0.0

    def test_scale_metric_low(self):
        assert scale_metric(0.0, low=0.0, high=1.0) == pytest.approx(0.0)

    def test_scale_metric_high(self):
        assert scale_metric(1.0, low=0.0, high=1.0) == pytest.approx(100.0)

    def test_scale_metric_invert(self):
        assert scale_metric(0.0, low=0.0, high=1.0, invert=True) == pytest.approx(100.0)

    def test_clamp(self):
        assert clamp(150.0, 0.0, 100.0) == 100.0
        assert clamp(-5.0, 0.0, 100.0) == 0.0


class TestAnnualizedReturn:
    def test_flat(self):
        assert annualized_return(0.0, 1.0) == pytest.approx(0.0)

    def test_100pct_over_2_years(self):
        # (1 + 1.0)^(1/2) - 1 = sqrt(2) - 1 ≈ 0.4142
        r = annualized_return(1.0, 2.0)
        assert r == pytest.approx(math.sqrt(2) - 1.0, rel=1e-6)

    def test_zero_years_returns_zero(self):
        assert annualized_return(0.5, 0.0) == 0.0


class TestSharpeRatio:
    def test_zero_std(self):
        returns = [0.001] * 20
        assert sharpe_ratio(returns, rf_per_period=0.0) == 0.0

    def test_positive_sharpe(self):
        returns = [0.005] * 50 + [-0.002] * 50
        sr = sharpe_ratio(returns, rf_per_period=0.0, periods_per_year=252)
        assert sr > 0.0

    def test_negative_sharpe_when_below_rf(self):
        # Mix of returns whose mean is below the per-period rf → negative Sharpe
        returns = [0.001, 0.002, -0.001, 0.001, 0.0, 0.002, -0.002, 0.001] * 10
        # rf_per_period=0.003 exceeds the mean of these returns
        sr = sharpe_ratio(returns, rf_per_period=0.003, periods_per_year=252)
        assert sr < 0.0


class TestSortinoRatio:
    def test_no_downside(self):
        returns = [0.01] * 20
        srt = sortino_ratio(returns, rf_per_period=0.0)
        assert srt == 0.0  # zero downside dev → 0

    def test_positive_sortino(self):
        returns = [0.01, -0.005, 0.01, -0.003, 0.02]
        srt = sortino_ratio(returns, rf_per_period=0.0, periods_per_year=252)
        assert srt > 0.0


class TestProfitFactor:
    def test_no_losses(self):
        assert profit_factor([10.0, 20.0]) == math.inf

    def test_no_gains(self):
        assert profit_factor([-10.0, -20.0]) == 0.0

    def test_balanced(self):
        pf = profit_factor([10.0, -10.0])
        assert pf == pytest.approx(1.0)

    def test_typical(self):
        pf = profit_factor([15.0, 15.0, -10.0])
        assert pf == pytest.approx(3.0)


class TestExpectancy:
    def test_zero_win_rate(self):
        assert expectancy(0.0, 200.0, 100.0) == pytest.approx(-100.0)

    def test_full_win_rate(self):
        assert expectancy(1.0, 200.0, 100.0) == pytest.approx(200.0)

    def test_typical(self):
        # 0.55 * 200 - 0.45 * 100 = 110 - 45 = 65
        assert expectancy(0.55, 200.0, 100.0) == pytest.approx(65.0)


# ── PerformanceEngine integration ────────────────────────────────────────────

class TestPerformanceEngine:
    def test_empty_curve_returns_zeros(self):
        from iios.investment.strategy.evaluation.evaluation_input import EvaluationInput
        from iios.investment.strategy.evaluation.equity_curve import EquityCurve
        inp = EvaluationInput(
            strategy_id="s1", strategy_name="s", trades=[],
            equity_curve=EquityCurve([]),
        )
        pm = PerformanceEngine().compute(inp)
        assert pm.sharpe_ratio == 0.0
        assert pm.n_trades == 0

    def test_typical_strategy_metrics(self):
        inp = make_evaluation_input(n_trades=60, win_rate=0.55)
        pm = PerformanceEngine().compute(inp)
        assert pm.n_trades == 60
        assert math.isfinite(pm.sharpe_ratio)
        assert math.isfinite(pm.sortino_ratio)
        assert pm.profit_factor >= 0.0

    def test_annualized_return_positive_for_profitable(self):
        inp = make_evaluation_input(n_trades=80, win_rate=0.65, avg_win=300.0, avg_loss=-100.0)
        pm = PerformanceEngine().compute(inp)
        assert pm.total_return > 0.0

    def test_all_losers_negative_returns(self):
        trades = []
        from tests.unit.investment.strategy.evaluation.conftest import make_trade
        for i in range(30):
            trades.append(make_trade(i, -100.0, pnl_pct=-0.01))
        eq_vals = [100_000.0 - 100.0 * i for i in range(31)]
        curve = make_equity_curve(eq_vals)
        from iios.investment.strategy.evaluation.evaluation_input import EvaluationInput
        inp = EvaluationInput("s", "s", trades, curve)
        pm = PerformanceEngine().compute(inp)
        assert pm.total_return < 0.0
        assert pm.profit_factor == 0.0
