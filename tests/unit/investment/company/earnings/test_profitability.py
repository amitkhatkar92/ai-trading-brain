"""tests/unit/investment/company/earnings/test_profitability.py"""
import pytest

from iios.investment.company.earnings.margin_analysis import MarginAnalyzer
from iios.investment.company.earnings.return_analysis import ReturnAnalyzer
from iios.investment.company.earnings.cost_efficiency import CostEfficiencyAnalyzer
from iios.investment.company.earnings.profitability_engine import ProfitabilityEngine
from tests.unit.investment.company.earnings.conftest import make_report


@pytest.fixture
def steady_history():
    return [
        make_report(fy, net_margin=12.0, gross_margin=38.0, roe=14.0, roic=12.0)
        for fy in range(2019, 2025)
    ]


class TestMarginAnalyzer:
    def test_current_margin_from_latest(self, steady_history):
        m = MarginAnalyzer().analyze(steady_history, steady_history[-1])
        assert m.net_margin == pytest.approx(12.0)
        assert m.gross_margin == pytest.approx(38.0)

    def test_avg_margins_computed(self, steady_history):
        m = MarginAnalyzer().analyze(steady_history, steady_history[-1])
        assert m.avg_net_margin == pytest.approx(12.0, abs=0.5)

    def test_expanding_margin_detected(self):
        history = [
            make_report(fy, net_margin=8.0 + (fy - 2019) * 1.5)
            for fy in range(2019, 2025)
        ]
        m = MarginAnalyzer().analyze(history, history[-1])
        assert m.is_margin_expanding is True

    def test_contracting_margin_detected(self):
        history = [
            make_report(fy, net_margin=15.0 - (fy - 2019) * 1.5)
            for fy in range(2019, 2025)
        ]
        m = MarginAnalyzer().analyze(history, history[-1])
        assert m.is_margin_contracting is True

    def test_empty_history_returns_baseline(self):
        m = MarginAnalyzer().analyze([], None)
        assert m.net_margin is None

    def test_peak_trough_detected(self, steady_history):
        m = MarginAnalyzer().analyze(steady_history, steady_history[-1])
        assert m.peak_net_margin is not None
        assert m.trough_net_margin is not None
        assert m.peak_net_margin >= m.trough_net_margin


class TestReturnAnalyzer:
    def test_current_returns(self, steady_history):
        r = ReturnAnalyzer().analyze(steady_history, steady_history[-1])
        assert r.roe  == pytest.approx(14.0)
        assert r.roic == pytest.approx(12.0)

    def test_value_creator(self):
        history = [make_report(fy, roic=15.0) for fy in range(2019, 2025)]
        r = ReturnAnalyzer().analyze(history, history[-1])
        assert r.is_value_creator is True

    def test_not_value_creator_when_low_roic(self):
        history = [make_report(fy, roic=5.0) for fy in range(2019, 2025)]
        r = ReturnAnalyzer().analyze(history, history[-1])
        assert r.is_value_creator is False

    def test_high_return_flag(self):
        history = [make_report(fy, roic=20.0) for fy in range(2019, 2025)]
        r = ReturnAnalyzer().analyze(history, history[-1])
        assert r.is_high_return is True

    def test_avg_return(self, steady_history):
        r = ReturnAnalyzer().analyze(steady_history, steady_history[-1])
        assert r.avg_roic == pytest.approx(12.0, abs=0.5)


class TestCostEfficiencyAnalyzer:
    def test_cost_fields_populated(self, steady_history):
        p = CostEfficiencyAnalyzer().analyze(steady_history, steady_history[-1])
        assert p.cost_of_revenue_pct is not None

    def test_improving_structure_flag(self):
        history = [
            make_report(fy, gross_margin=30.0 + (fy - 2019) * 1.5)
            for fy in range(2019, 2025)
        ]
        p = CostEfficiencyAnalyzer().analyze(history, history[-1])
        assert p.is_improving_cost_structure is True


class TestProfitabilityEngine:
    def test_returns_full_intelligence(self, steady_history):
        fi = ProfitabilityEngine().analyze(steady_history, steady_history[-1])
        assert fi.margins is not None
        assert fi.returns is not None
        assert fi.costs is not None

    def test_as_profitability_profile(self, steady_history):
        fi = ProfitabilityEngine().analyze(steady_history, steady_history[-1])
        pp = fi.as_profitability_profile()
        assert pp.net_margin     == pytest.approx(12.0)
        assert pp.avg_net_margin == pytest.approx(12.0, abs=0.5)
        assert pp.avg_roic       == pytest.approx(12.0, abs=0.5)

    def test_handles_no_latest(self, steady_history):
        fi = ProfitabilityEngine().analyze(steady_history, None)
        assert fi is not None
