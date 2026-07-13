"""tests/unit/investment/strategy/evaluation/test_trade_quality.py"""
from __future__ import annotations

import math
import pytest

from iios.investment.strategy.evaluation.trade_statistics import TradeStatisticsCalculator
from iios.investment.strategy.evaluation.execution_quality import ExecutionQualityAnalyzer
from iios.investment.strategy.evaluation.trade_distribution import TradeDistributionAnalyzer
from iios.investment.strategy.evaluation.trade_quality import TradeQualityAnalyzer
from tests.unit.investment.strategy.evaluation.conftest import (
    make_trade, make_evaluation_input
)


class TestTradeStatistics:
    def _calc(self, trades):
        return TradeStatisticsCalculator().compute(trades)

    def test_empty_trades(self):
        ts = self._calc([])
        assert ts.total_trades == 0
        assert ts.win_rate == 0.0

    def test_all_winners(self):
        trades = [make_trade(i, 100.0) for i in range(10)]
        ts = self._calc(trades)
        assert ts.winning_trades == 10
        assert ts.losing_trades == 0
        assert ts.win_rate == pytest.approx(1.0)
        assert ts.gross_profit > 0.0
        assert ts.gross_loss == 0.0

    def test_all_losers(self):
        trades = [make_trade(i, -80.0) for i in range(10)]
        ts = self._calc(trades)
        assert ts.losing_trades == 10
        assert ts.win_rate == pytest.approx(0.0)
        assert ts.gross_profit == 0.0

    def test_mixed(self):
        trades = [make_trade(i, 100.0) for i in range(6)] + \
                 [make_trade(6 + i, -60.0) for i in range(4)]
        ts = self._calc(trades)
        assert ts.total_trades == 10
        assert ts.win_rate == pytest.approx(0.6)
        assert ts.risk_reward_ratio > 0.0

    def test_consecutive_wins(self):
        # 5 wins, 2 losses, 3 wins → max consecutive wins = 5
        pnls = [100.0] * 5 + [-50.0] * 2 + [100.0] * 3
        trades = [make_trade(i, p) for i, p in enumerate(pnls)]
        ts = self._calc(trades)
        assert ts.max_consecutive_wins == 5
        assert ts.max_consecutive_losses == 2

    def test_avg_winner_gt_avg_loser(self):
        trades = [make_trade(i, 200.0) for i in range(5)] + \
                 [make_trade(5 + i, -80.0) for i in range(5)]
        ts = self._calc(trades)
        assert ts.avg_winner > abs(ts.avg_loser)

    def test_largest_winner(self):
        pnls = [50.0, 200.0, 100.0, -80.0]
        trades = [make_trade(i, p) for i, p in enumerate(pnls)]
        ts = self._calc(trades)
        assert ts.largest_winner == pytest.approx(200.0)

    def test_trade_consistency_bounded(self):
        trades = [make_trade(i, 100.0 if i % 2 == 0 else -50.0) for i in range(20)]
        ts = self._calc(trades)
        assert 0.0 <= ts.trade_consistency <= 1.0


class TestExecutionQuality:
    def test_no_slippage(self):
        trades = [make_trade(i, 100.0, entry_slip=0.0) for i in range(20)]
        em = ExecutionQualityAnalyzer().analyze(trades)
        assert em.avg_total_slippage == pytest.approx(0.0)

    def test_positive_commission_drag(self):
        trades = [make_trade(i, 100.0, commission=20.0) for i in range(20)]
        em = ExecutionQualityAnalyzer().analyze(trades)
        assert em.total_commission == pytest.approx(20.0 * 20)
        assert em.commission_drag >= 0.0

    def test_execution_efficiency_bounded(self):
        trades = [make_trade(i, 100.0, entry_slip=1.0) for i in range(30)]
        em = ExecutionQualityAnalyzer().analyze(trades)
        assert 0.0 <= em.execution_efficiency <= 1.0

    def test_empty_trades(self):
        em = ExecutionQualityAnalyzer().analyze([])
        assert em.avg_entry_slippage == 0.0
        assert em.total_commission == 0.0


class TestTradeDistribution:
    def test_single_symbol(self):
        trades = [make_trade(i, 100.0, symbol="RELIANCE") for i in range(10)]
        td = TradeDistributionAnalyzer().analyze(trades)
        assert td.symbol_count == 1
        assert td.top_symbol_pct == pytest.approx(1.0)

    def test_pnl_percentiles_ordered(self):
        pnls = list(range(-50, 100, 3))
        trades = [make_trade(i, float(p)) for i, p in enumerate(pnls)]
        td = TradeDistributionAnalyzer().analyze(trades)
        assert td.pnl_p5 <= td.pnl_p25 <= td.pnl_p50 <= td.pnl_p75 <= td.pnl_p95

    def test_trades_per_day_positive(self):
        trades = [make_trade(i, 100.0) for i in range(20)]
        td = TradeDistributionAnalyzer().analyze(trades)
        assert td.trades_per_day > 0.0


class TestTradeQualityAnalyzer:
    def test_full_report(self):
        inp = make_evaluation_input(n_trades=50)
        report = TradeQualityAnalyzer().analyze(inp)
        assert report.statistics.total_trades == 50
        assert 0.0 <= report.win_rate <= 1.0
        assert 0.0 <= report.execution_efficiency <= 1.0

    def test_win_rate_matches_trades(self):
        inp = make_evaluation_input(n_trades=60, win_rate=0.70)
        report = TradeQualityAnalyzer().analyze(inp)
        # win_rate should be close to the requested 0.70
        assert abs(report.win_rate - 0.70) < 0.02  # within 2pp
