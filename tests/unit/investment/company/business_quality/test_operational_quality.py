"""tests/unit/investment/company/business_quality/test_operational_quality.py"""
import pytest

from iios.investment.company.business_quality.capital_efficiency import CapitalEfficiencyAnalyzer
from iios.investment.company.business_quality.execution_quality import ExecutionQualityAnalyzer
from iios.investment.company.business_quality.efficiency_engine import EfficiencyEngine
from tests.unit.investment.company.business_quality.conftest import make_ctx


class TestCapitalEfficiencyAnalyzer:
    def test_roic_populated(self, ctx_high_quality):
        p = CapitalEfficiencyAnalyzer().analyze(ctx_high_quality)
        assert p.current_roic is not None
        assert p.current_roic > 0

    def test_avg_roic_from_earnings(self, ctx_high_quality):
        p = CapitalEfficiencyAnalyzer().analyze(ctx_high_quality)
        assert p.avg_roic is not None

    def test_asset_turnover(self, ctx_high_quality):
        p = CapitalEfficiencyAnalyzer().analyze(ctx_high_quality)
        assert p.asset_turnover is not None
        assert p.asset_turnover > 0

    def test_receivables_days_populated(self, ctx_high_quality):
        p = CapitalEfficiencyAnalyzer().analyze(ctx_high_quality)
        assert p.receivables_days is not None

    def test_ccc_computed(self, ctx_high_quality):
        p = CapitalEfficiencyAnalyzer().analyze(ctx_high_quality)
        assert p.cash_conversion_cycle is not None

    def test_capital_efficiency_score_range(self, ctx_high_quality):
        p = CapitalEfficiencyAnalyzer().analyze(ctx_high_quality)
        assert 0.0 <= p.capital_efficiency_score <= 100.0

    def test_high_quality_is_capital_efficient(self, ctx_high_quality):
        p = CapitalEfficiencyAnalyzer().analyze(ctx_high_quality)
        assert p.is_capital_efficient is True

    def test_commodity_not_capital_efficient(self, ctx_commodity):
        p = CapitalEfficiencyAnalyzer().analyze(ctx_commodity)
        assert p.capital_efficiency_score < 70.0

    def test_minimal_context_no_crash(self, ctx_minimal):
        p = CapitalEfficiencyAnalyzer().analyze(ctx_minimal)
        assert p.capital_efficiency_score == pytest.approx(0.0, abs=10)

    def test_fcf_negative_flag(self):
        ctx = make_ctx(fcf_margin=-5.0)
        p = CapitalEfficiencyAnalyzer().analyze(ctx)
        assert "negative_fcf" in p.flags

    def test_exceptional_roic_flag(self):
        ctx = make_ctx(roic=25.0)
        p = CapitalEfficiencyAnalyzer().analyze(ctx)
        assert "exceptional_roic" in p.flags

    def test_to_dict_keys(self, ctx_high_quality):
        d = CapitalEfficiencyAnalyzer().analyze(ctx_high_quality).to_dict()
        assert "capital_efficiency_score" in d
        assert "is_capital_efficient" in d


class TestExecutionQualityAnalyzer:
    def test_execution_score_range(self, ctx_high_quality):
        p = ExecutionQualityAnalyzer().analyze(ctx_high_quality)
        assert 0.0 <= p.execution_score <= 100.0

    def test_high_quality_earns_good_execution_score(self, ctx_high_quality):
        p = ExecutionQualityAnalyzer().analyze(ctx_high_quality)
        assert p.execution_score > 40.0

    def test_periods_analyzed_populated(self, ctx_high_quality):
        p = ExecutionQualityAnalyzer().analyze(ctx_high_quality)
        assert p.periods_analyzed >= 0

    def test_wc_efficiency_score_range(self, ctx_high_quality):
        p = ExecutionQualityAnalyzer().analyze(ctx_high_quality)
        assert 0.0 <= p.wc_efficiency_score <= 100.0

    def test_minimal_context_no_crash(self, ctx_minimal):
        p = ExecutionQualityAnalyzer().analyze(ctx_minimal)
        assert 0.0 <= p.execution_score <= 100.0

    def test_to_dict_keys(self, ctx_high_quality):
        d = ExecutionQualityAnalyzer().analyze(ctx_high_quality).to_dict()
        assert "execution_score" in d
        assert "consistency_score" in d


class TestEfficiencyEngine:
    def test_returns_operational_profile(self, ctx_high_quality):
        p = EfficiencyEngine().analyze(ctx_high_quality)
        assert p.capital_efficiency is not None
        assert p.execution_quality is not None

    def test_score_in_range(self, ctx_high_quality):
        p = EfficiencyEngine().analyze(ctx_high_quality)
        assert 0.0 <= p.operational_quality_score <= 100.0

    def test_high_quality_operationally_excellent(self, ctx_high_quality):
        p = EfficiencyEngine().analyze(ctx_high_quality)
        assert p.operational_quality_score > 50.0

    def test_high_quality_better_than_commodity(self, ctx_high_quality, ctx_commodity):
        e = EfficiencyEngine()
        hq_score = e.analyze(ctx_high_quality).operational_quality_score
        cm_score = e.analyze(ctx_commodity).operational_quality_score
        assert hq_score > cm_score

    def test_flags_populated(self, ctx_high_quality):
        p = EfficiencyEngine().analyze(ctx_high_quality)
        assert isinstance(p.flags, list)

    def test_to_dict_keys(self, ctx_high_quality):
        d = EfficiencyEngine().analyze(ctx_high_quality).to_dict()
        assert "operational_quality_score" in d
        assert "capital_efficiency" in d
        assert "execution_quality" in d
