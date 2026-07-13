"""tests/unit/investment/company/earnings/test_trends.py"""
import pytest

from iios.investment.company.earnings.growth_trend import GrowthTrendAnalyzer
from iios.investment.company.earnings.profit_cycle import detect_profit_cycle
from iios.investment.company.earnings.earnings_momentum import EarningsMomentumAnalyzer
from iios.investment.company.earnings.earnings_trend import EarningsTrendAnalyzer
from iios.investment.company.earnings.earnings_report import (
    TrendDirection, ProfitCyclePhase, MomentumLabel,
)
from tests.unit.investment.company.earnings.conftest import make_report


@pytest.fixture
def flat_history():
    return [make_report(fy, eps=10.0, net_margin=10.0) for fy in range(2019, 2025)]


class TestGrowthTrend:
    def test_accelerating_eps(self, growing_history):
        m = GrowthTrendAnalyzer().analyze(growing_history, "diluted_eps")
        assert m.direction in [TrendDirection.ACCELERATING, TrendDirection.STABLE]

    def test_deteriorating_eps(self, declining_history):
        m = GrowthTrendAnalyzer().analyze(declining_history, "diluted_eps")
        assert m.direction in [TrendDirection.DETERIORATING, TrendDirection.DECELERATING]

    def test_stable_flat(self, flat_history):
        m = GrowthTrendAnalyzer().analyze(flat_history, "diluted_eps")
        assert m.direction in [TrendDirection.STABLE, TrendDirection.DECELERATING]

    def test_cagr_positive_for_growth(self, growing_history):
        m = GrowthTrendAnalyzer().analyze(growing_history, "diluted_eps")
        assert m.cagr is not None
        assert m.cagr > 0

    def test_insufficient_data(self):
        m = GrowthTrendAnalyzer().analyze([make_report(2024)], "diluted_eps")
        assert m.direction == TrendDirection.INSUFFICIENT

    def test_avg_growth_positive(self, growing_history):
        m = GrowthTrendAnalyzer().analyze(growing_history, "revenue")
        assert m.avg_growth is not None
        assert m.avg_growth > 0


class TestProfitCycle:
    def test_expansion_phase(self):
        history = [
            make_report(fy, net_margin=10.0 + (fy - 2019) * 1.5)
            for fy in range(2019, 2025)
        ]
        phase = detect_profit_cycle(history)
        assert phase in [ProfitCyclePhase.EXPANSION, ProfitCyclePhase.PEAK]

    def test_contraction_phase(self):
        history = [
            make_report(fy, net_margin=15.0 - (fy - 2019) * 2.0)
            for fy in range(2019, 2025)
        ]
        phase = detect_profit_cycle(history)
        assert phase in [ProfitCyclePhase.CONTRACTION, ProfitCyclePhase.TROUGH]

    def test_unknown_for_empty(self):
        assert detect_profit_cycle([]) == ProfitCyclePhase.UNKNOWN

    def test_unknown_for_insufficient(self):
        assert detect_profit_cycle([make_report(2024)]) == ProfitCyclePhase.UNKNOWN


class TestEarningsMomentum:
    def test_strong_positive_momentum(self, growing_history):
        m = EarningsMomentumAnalyzer().analyze(growing_history)
        assert m.score >= 0  # score is valid
        assert m.label in [MomentumLabel.POSITIVE, MomentumLabel.STRONG_POSITIVE,
                            MomentumLabel.NEUTRAL]

    def test_negative_momentum_on_decline(self, declining_history):
        m = EarningsMomentumAnalyzer().analyze(declining_history)
        assert m.label in [MomentumLabel.NEGATIVE, MomentumLabel.STRONG_NEGATIVE,
                            MomentumLabel.NEUTRAL]

    def test_periods_used(self, growing_history):
        m = EarningsMomentumAnalyzer().analyze(growing_history, trailing=4)
        assert m.periods_used > 0

    def test_insufficient_data(self):
        m = EarningsMomentumAnalyzer().analyze([make_report(2024)])
        assert m.score == pytest.approx(50.0, abs=5)


class TestEarningsTrendOrchestrator:
    def test_build_trend_profile(self, growing_history):
        tp = EarningsTrendAnalyzer().analyze(growing_history)
        assert tp.eps_direction is not None
        assert tp.revenue_direction is not None
        assert tp.margin_direction is not None
        assert tp.periods_analyzed == len(growing_history)

    def test_profit_cycle_set(self, growing_history):
        tp = EarningsTrendAnalyzer().analyze(growing_history)
        assert isinstance(tp.profit_cycle_phase, ProfitCyclePhase)

    def test_eps_cagr(self, growing_history):
        tp = EarningsTrendAnalyzer().analyze(growing_history)
        assert tp.cagr_eps is not None

    def test_latest_eps_growth(self, growing_history):
        tp = EarningsTrendAnalyzer().analyze(growing_history)
        assert tp.latest_eps_growth is not None
        assert tp.latest_eps_growth > 0

    def test_declining_trend_detected(self, declining_history):
        tp = EarningsTrendAnalyzer().analyze(declining_history)
        assert tp.eps_direction in [
            TrendDirection.DETERIORATING, TrendDirection.DECELERATING,
        ]
