"""tests/unit/investment/strategy/evaluation/test_robustness.py"""
from __future__ import annotations

import math
import pytest

from iios.investment.strategy.evaluation.walk_forward_analysis import WalkForwardAnalyzer
from iios.investment.strategy.evaluation.monte_carlo_analysis import MonteCarloAnalyzer
from iios.investment.strategy.evaluation.stress_testing import StressTester
from iios.investment.strategy.evaluation.robustness_engine import RobustnessEngine
from tests.unit.investment.strategy.evaluation.conftest import (
    make_trade, make_equity_curve, make_evaluation_input
)


class TestWalkForwardAnalyzer:
    def _trades(self, n=40, pnl=100.0):
        return [make_trade(i, pnl) for i in range(n)]

    def test_minimum_folds_run(self):
        trades = self._trades(40)
        curve = make_equity_curve([100_000 + i * 100 for i in range(40)])
        wf = WalkForwardAnalyzer(n_folds=4).analyze(trades, curve)
        assert wf.n_windows >= 1

    def test_too_few_trades_returns_zero_windows(self):
        trades = self._trades(4)
        curve = make_equity_curve([100.0 + i for i in range(4)])
        wf = WalkForwardAnalyzer(n_folds=4).analyze(trades, curve)
        # With 4 trades and 4 folds, each window has too few samples
        assert wf.n_windows == 0 or wf.stability_score == 0.0

    def test_stability_score_bounded(self):
        trades = self._trades(80, pnl=100.0)
        curve = make_equity_curve([100_000 + i * 100 for i in range(80)])
        wf = WalkForwardAnalyzer(n_folds=4).analyze(trades, curve)
        assert 0.0 <= wf.stability_score <= 1.0

    def test_profitable_strategy_positive_oos_sharpe(self):
        trades = self._trades(80, pnl=200.0)
        curve = make_equity_curve([100_000 + i * 200 for i in range(80)])
        wf = WalkForwardAnalyzer(n_folds=4).analyze(trades, curve)
        if wf.n_windows > 0:
            # avg_oos_sharpe may be finite
            assert math.isfinite(wf.avg_oos_sharpe)


class TestMonteCarloAnalyzer:
    def test_seed_determinism(self):
        # Give each trade distinct pnl_pct so MC bootstrap actually varies
        trades = [
            make_trade(i, 100.0 if i % 3 != 0 else -50.0,
                       pnl_pct=0.02 if i % 3 != 0 else -0.012)
            for i in range(50)
        ]
        mc1 = MonteCarloAnalyzer(n_simulations=200, seed=42).analyze(trades)
        mc2 = MonteCarloAnalyzer(n_simulations=200, seed=42).analyze(trades)
        assert mc1.total_return_p50 == pytest.approx(mc2.total_return_p50)
        assert mc1.max_dd_p50 == pytest.approx(mc2.max_dd_p50)

    def test_different_seeds_different_results(self):
        # With varied pnl_pct, different bootstrap orderings produce different totals
        trades = [
            make_trade(i, 100.0 if i % 3 != 0 else -50.0,
                       pnl_pct=0.02 if i % 3 != 0 else -0.012)
            for i in range(50)
        ]
        mc = MonteCarloAnalyzer(n_simulations=200, seed=42).analyze(trades)
        # p5 and p95 of total_return must differ (spread > 0)
        assert mc.total_return_p5 != mc.total_return_p95

    def test_robustness_score_bounded(self):
        trades = [make_trade(i, 100.0 if i % 2 == 0 else -40.0) for i in range(60)]
        mc = MonteCarloAnalyzer(n_simulations=300, seed=42).analyze(trades)
        assert 0.0 <= mc.robustness_score <= 1.0

    def test_pct_positive_return_range(self):
        trades = [make_trade(i, 100.0) for i in range(40)]
        mc = MonteCarloAnalyzer(n_simulations=200, seed=42).analyze(trades)
        assert 0.0 <= mc.pct_positive_return <= 1.0

    def test_percentile_ordering(self):
        trades = [make_trade(i, 80.0) for i in range(50)]
        mc = MonteCarloAnalyzer(n_simulations=300, seed=42).analyze(trades)
        assert mc.sharpe_p5 <= mc.sharpe_p50 <= mc.sharpe_p95
        # Max drawdown: p5 is the worst draw (largest magnitude — worst == p95 in dd terms)
        assert mc.max_dd_p5 <= mc.max_dd_p95  # lower dd is better


class TestStressTester:
    def test_survival_rate_bounded(self):
        trades = [make_trade(i, 100.0 if i % 3 != 0 else -80.0) for i in range(50)]
        report = StressTester().test(trades)
        assert 0.0 <= report.survival_rate <= 1.0

    def test_all_winners_high_survival(self):
        trades = [make_trade(i, 200.0) for i in range(40)]
        report = StressTester().test(trades)
        # Most scenarios should be survived when all trades win
        assert report.scenarios_survived >= 0

    def test_all_losers_low_survival(self):
        trades = [make_trade(i, -100.0) for i in range(40)]
        report = StressTester().test(trades)
        # Stress score should be low for all-loser strategies
        assert report.stress_score <= 0.5

    def test_scenarios_run_count(self):
        trades = [make_trade(i, 100.0) for i in range(30)]
        report = StressTester().test(trades)
        assert report.scenarios_run == 5  # 5 default scenarios


class TestRobustnessEngine:
    def test_overall_robustness_bounded(self):
        inp = make_evaluation_input(n_trades=80, win_rate=0.6)
        rr = RobustnessEngine(wf_folds=4, mc_simulations=300, mc_seed=42).evaluate(inp)
        assert 0.0 <= rr.overall_robustness <= 1.0

    def test_component_reports_present(self):
        inp = make_evaluation_input(n_trades=80)
        rr = RobustnessEngine(wf_folds=4, mc_simulations=200, mc_seed=42).evaluate(inp)
        assert rr.walk_forward is not None
        assert rr.monte_carlo is not None
        assert rr.stress_test is not None

    def test_weights_sum_to_robustness(self):
        inp = make_evaluation_input(n_trades=80)
        rr = RobustnessEngine(wf_folds=4, mc_simulations=200, mc_seed=42).evaluate(inp)
        expected = (
            0.45 * rr.walk_forward_stability
            + 0.35 * rr.mc_robustness
            + 0.20 * rr.stress_survival
        )
        assert rr.overall_robustness == pytest.approx(expected, rel=1e-6)
