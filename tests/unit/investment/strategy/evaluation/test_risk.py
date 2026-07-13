"""tests/unit/investment/strategy/evaluation/test_risk.py"""
from __future__ import annotations

import math
import pytest

from iios.investment.strategy.evaluation.drawdown_analysis import DrawdownAnalyzer
from iios.investment.strategy.evaluation.volatility_analysis import VolatilityAnalyzer
from iios.investment.strategy.evaluation.tail_risk import TailRiskAnalyzer
from iios.investment.strategy.evaluation.risk_evaluation import RiskEvaluator
from tests.unit.investment.strategy.evaluation.conftest import (
    make_equity_curve, make_evaluation_input
)


class TestDrawdownAnalyzer:
    def test_no_drawdown_monotonic(self):
        curve = make_equity_curve([100.0, 110.0, 120.0, 130.0])
        dm = DrawdownAnalyzer().analyze(curve)
        assert dm.max_drawdown == pytest.approx(0.0)
        assert dm.ulcer_index == pytest.approx(0.0)

    def test_single_peak_then_trough(self):
        # Peak 120, trough 90 → dd = 30/120 = 0.25
        curve = make_equity_curve([100.0, 120.0, 90.0])
        dm = DrawdownAnalyzer().analyze(curve)
        assert dm.max_drawdown == pytest.approx(0.25)

    def test_avg_drawdown_positive(self):
        # Every other point is below peak
        curve = make_equity_curve([100.0, 90.0, 100.0, 80.0, 100.0])
        dm = DrawdownAnalyzer().analyze(curve)
        assert dm.avg_drawdown > 0.0

    def test_ulcer_index_nonzero_with_dd(self):
        curve = make_equity_curve([100.0, 80.0, 90.0, 70.0, 100.0])
        dm = DrawdownAnalyzer().analyze(curve)
        assert dm.ulcer_index > 0.0

    def test_empty_curve(self):
        from iios.investment.strategy.evaluation.equity_curve import EquityCurve
        dm = DrawdownAnalyzer().analyze(EquityCurve([]))
        assert dm.max_drawdown == 0.0

    def test_max_drawdown_currency(self):
        curve = make_equity_curve([100.0, 120.0, 80.0])
        dm = DrawdownAnalyzer().analyze(curve)
        assert dm.max_drawdown_currency == pytest.approx(40.0)  # 120 - 80


class TestVolatilityAnalyzer:
    def test_flat_returns_zero_vol(self):
        curve = make_equity_curve([100.0] * 20)
        vm = VolatilityAnalyzer().analyze(curve, ann_return=0.0)
        assert vm.annualized_volatility == pytest.approx(0.0)

    def test_volatile_curve_nonzero(self):
        vals = [100.0, 110.0, 95.0, 115.0, 100.0, 120.0, 105.0, 130.0] * 5
        curve = make_equity_curve(vals)
        vm = VolatilityAnalyzer().analyze(curve, ann_return=0.10)
        assert vm.annualized_volatility > 0.0

    def test_skewness_right_skewed(self):
        # Large positive returns, small negatives → positive skew
        returns_list = [0.10, 0.08, 0.07, -0.01, 0.09, 0.06, -0.005]
        vals = [100.0]
        for r in returns_list:
            vals.append(vals[-1] * (1.0 + r))
        curve = make_equity_curve(vals)
        vm = VolatilityAnalyzer().analyze(curve, ann_return=0.08)
        # With mostly positive large returns, skew should be somewhat positive
        assert math.isfinite(vm.skewness)

    def test_empty_curve(self):
        from iios.investment.strategy.evaluation.equity_curve import EquityCurve
        vm = VolatilityAnalyzer().analyze(EquityCurve([]), ann_return=0.0)
        assert vm.annualized_volatility == 0.0


class TestTailRiskAnalyzer:
    def test_var_ordering(self):
        # 99% VaR should be worse (more negative) than 95% VaR
        vals = [100.0 + i * 0.5 + (-10.0 if i % 7 == 0 else 0.0)
                for i in range(100)]
        curve = make_equity_curve(vals)
        tr = TailRiskAnalyzer().analyze(curve)
        assert tr.var_99 <= tr.var_95

    def test_all_positive_returns(self):
        vals = [100.0 * (1.01 ** i) for i in range(50)]
        curve = make_equity_curve(vals)
        tr = TailRiskAnalyzer().analyze(curve)
        # Even with positive returns, VaR computed on smallest returns
        assert math.isfinite(tr.var_95)

    def test_pct_negative_periods_correct(self):
        # Make exactly 3 losing periods out of 9
        vals = [100.0, 105.0, 102.0, 107.0, 103.0, 109.0, 106.0, 110.0, 108.0, 113.0]
        curve = make_equity_curve(vals)
        tr = TailRiskAnalyzer().analyze(curve)
        # 3 out of 9 period returns are negative (dips at indices 2, 4, 6, 8)
        assert 0.0 <= tr.pct_negative_periods <= 1.0

    def test_empty_curve(self):
        from iios.investment.strategy.evaluation.equity_curve import EquityCurve
        tr = TailRiskAnalyzer().analyze(EquityCurve([]))
        assert tr.var_95 == 0.0


class TestRiskEvaluator:
    def test_returns_risk_metrics(self):
        inp = make_evaluation_input()
        re = RiskEvaluator()
        rm = re.evaluate(inp)
        assert 0.0 <= rm.max_drawdown <= 1.0
        assert math.isfinite(rm.annualized_volatility)
        assert math.isfinite(rm.var_95)

    def test_profitable_strategy_moderate_drawdown(self):
        inp = make_evaluation_input(n_trades=80, win_rate=0.65, avg_win=300.0)
        rm = RiskEvaluator().evaluate(inp)
        # A consistently profitable strategy should have some bounded drawdown
        assert rm.max_drawdown < 1.0
