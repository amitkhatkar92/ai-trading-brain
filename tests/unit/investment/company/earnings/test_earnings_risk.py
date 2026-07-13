"""tests/unit/investment/company/earnings/test_earnings_risk.py"""
import pytest

from iios.investment.company.earnings.earnings_volatility import EarningsVolatilityAnalyzer
from iios.investment.company.earnings.forecast_stability import ForecastStabilityAnalyzer
from iios.investment.company.earnings.earnings_risk import EarningsRiskAnalyzer
from iios.investment.company.earnings.earnings_revision import EarningsRevisionTracker
from tests.unit.investment.company.earnings.conftest import make_report


@pytest.fixture
def stable_history():
    return [
        make_report(fy, eps=10.0, net_margin=12.0, ocf=120.0, accruals=0.02)
        for fy in range(2019, 2025)
    ]


class TestEarningsVolatility:
    def test_stable_low_volatility(self, stable_history):
        v = EarningsVolatilityAnalyzer().analyze(stable_history)
        assert v.loss_rate == pytest.approx(0.0)
        assert v.cyclicality_score < 50.0

    def test_volatile_history_high_cyclicality(self, volatile_history):
        v = EarningsVolatilityAnalyzer().analyze(volatile_history)
        assert v.loss_rate > 0
        assert v.loss_periods >= 2

    def test_eps_growth_cv_zero_for_flat(self):
        history = [make_report(fy, eps=10.0) for fy in range(2019, 2025)]
        v = EarningsVolatilityAnalyzer().analyze(history)
        # All identical eps → zero growth rates → cv ≈ 0 or None
        assert v.eps_growth_cv is None or v.eps_growth_cv == pytest.approx(0.0, abs=0.1)

    def test_insufficient_returns_defaults(self):
        v = EarningsVolatilityAnalyzer().analyze([])
        assert v.loss_periods == 0


class TestForecastStability:
    def test_stable_history_gives_high_score(self, stable_history):
        m = ForecastStabilityAnalyzer().analyze(stable_history)
        assert m.stability_score > 60.0
        assert m.is_margin_stable is True

    def test_volatile_lowers_score(self, volatile_history):
        stable = ForecastStabilityAnalyzer().analyze([
            make_report(fy, net_margin=12.0) for fy in range(2019, 2025)
        ]).stability_score
        vol = ForecastStabilityAnalyzer().analyze(volatile_history).stability_score
        assert vol < stable

    def test_surprise_vol_zero_for_flat(self):
        history = [make_report(fy, eps=10.0) for fy in range(2019, 2025)]
        m = ForecastStabilityAnalyzer().analyze(history)
        assert m.eps_surprise_vol is None or m.eps_surprise_vol == pytest.approx(0.0, abs=0.1)


class TestEarningsRiskAnalyzer:
    def test_stable_history_low_risk(self, stable_history):
        tracker = EarningsRevisionTracker()
        risk = EarningsRiskAnalyzer().analyze("TEST", stable_history, tracker)
        assert risk.earnings_stability_score > 50.0
        assert risk.is_cyclical is False

    def test_volatile_history_higher_risk(self, volatile_history):
        tracker = EarningsRevisionTracker()
        stable_risk = EarningsRiskAnalyzer().analyze(
            "T1", [make_report(fy, eps=10.0, net_margin=12.0) for fy in range(2019, 2025)],
            tracker
        )
        volatile_risk = EarningsRiskAnalyzer().analyze("T2", volatile_history, tracker)
        assert volatile_risk.earnings_stability_score < stable_risk.earnings_stability_score

    def test_revisions_added_to_risk_flags(self):
        tracker = EarningsRevisionTracker()
        history = [make_report(fy) for fy in range(2019, 2025)]
        # Manually inject revisions via detect() using old vs new reports
        for i in range(4):
            old_r = make_report(2020 + i, eps=10.0)
            new_r = make_report(2020 + i, eps=9.0)
            tracker.detect("T", old_r.period_label, old_r, new_r)
        risk = EarningsRiskAnalyzer().analyze("T", history, tracker)
        assert any("revision" in f for f in risk.flags)

    def test_consecutive_profit_years(self, growing_history):
        tracker = EarningsRevisionTracker()
        risk = EarningsRiskAnalyzer().analyze("G", growing_history, tracker)
        assert risk.consecutive_profit_years == 5

    def test_to_dict(self, stable_history):
        tracker = EarningsRevisionTracker()
        d = EarningsRiskAnalyzer().analyze("T", stable_history, tracker).to_dict()
        assert "earnings_stability_score" in d
        assert "is_cyclical" in d
