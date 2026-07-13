"""tests/unit/investment/strategy/risk/test_risk_analysis.py
Tests for the four risk analyzers and RiskAnalysis orchestrator.
"""
import pytest
from tests.unit.investment.strategy.risk.conftest import make_risk_input
from iios.investment.strategy.risk.market_risk import MarketRiskAnalyzer
from iios.investment.strategy.risk.execution_risk import ExecutionRiskAnalyzer
from iios.investment.strategy.risk.liquidity_risk import LiquidityRiskAnalyzer
from iios.investment.strategy.risk.model_risk import ModelRiskAnalyzer
from iios.investment.strategy.risk.risk_analysis import RiskAnalysis


class TestMarketRiskAnalyzer:
    def test_returns_result(self, risk_input):
        result = MarketRiskAnalyzer().analyse(risk_input)
        assert 0.0 <= result.overall_market_risk <= 100.0

    def test_high_vol_input_raises_market_risk(self, high_risk_input, low_risk_input):
        high = MarketRiskAnalyzer().analyse(high_risk_input).overall_market_risk
        low  = MarketRiskAnalyzer().analyse(low_risk_input).overall_market_risk
        assert high > low

    def test_regime_mismatch_raises_regime_risk(self):
        inp_mis = make_risk_input(
            current_regime="ranging",
            supported_regimes=("trending",),
        )
        inp_ok  = make_risk_input(
            current_regime="trending",
            supported_regimes=("trending",),
        )
        r_mis = MarketRiskAnalyzer().analyse(inp_mis).regime_risk
        r_ok  = MarketRiskAnalyzer().analyse(inp_ok).regime_risk
        assert r_mis > r_ok

    def test_all_sub_scores_in_range(self, risk_input):
        r = MarketRiskAnalyzer().analyse(risk_input)
        for score in (r.vol_risk, r.drawdown_risk, r.tail_risk, r.regime_risk,
                      r.gap_risk, r.volatility_regime_risk, r.overall_market_risk):
            assert 0.0 <= score <= 100.0


class TestExecutionRiskAnalyzer:
    def test_returns_result(self, risk_input):
        result = ExecutionRiskAnalyzer().analyse(risk_input)
        assert 0.0 <= result.overall_execution_risk <= 100.0

    def test_low_liquidity_raises_execution_risk(self):
        low  = make_risk_input(market_liquidity="low")
        high = make_risk_input(market_liquidity="high")
        r_low  = ExecutionRiskAnalyzer().analyse(low).overall_execution_risk
        r_high = ExecutionRiskAnalyzer().analyse(high).overall_execution_risk
        assert r_low >= r_high

    def test_all_sub_scores_in_range(self, risk_input):
        r = ExecutionRiskAnalyzer().analyse(risk_input)
        for s in (r.slippage_risk, r.timing_risk, r.fill_risk,
                  r.complexity_risk, r.overall_execution_risk):
            assert 0.0 <= s <= 100.0


class TestLiquidityRiskAnalyzer:
    def test_returns_result(self, risk_input):
        result = LiquidityRiskAnalyzer().analyse(risk_input)
        assert 0.0 <= result.overall_liquidity_risk <= 100.0

    def test_low_market_liquidity_raises_risk(self):
        low  = make_risk_input(market_liquidity="low")
        high = make_risk_input(market_liquidity="high")
        r_low  = LiquidityRiskAnalyzer().analyse(low).overall_liquidity_risk
        r_high = LiquidityRiskAnalyzer().analyse(high).overall_liquidity_risk
        assert r_low >= r_high

    def test_all_sub_scores_in_range(self, risk_input):
        r = LiquidityRiskAnalyzer().analyse(risk_input)
        for s in (r.asset_liquidity_risk, r.sector_liquidity_risk,
                  r.market_liquidity_risk, r.spread_risk,
                  r.depth_risk, r.overall_liquidity_risk):
            assert 0.0 <= s <= 100.0


class TestModelRiskAnalyzer:
    def test_returns_result(self, risk_input):
        result = ModelRiskAnalyzer().analyse(risk_input)
        assert 0.0 <= result.overall_model_risk <= 100.0

    def test_low_robustness_raises_model_risk(self):
        low  = make_risk_input(robustness_score=0.10)
        high = make_risk_input(robustness_score=0.95)
        r_low  = ModelRiskAnalyzer().analyse(low).overall_model_risk
        r_high = ModelRiskAnalyzer().analyse(high).overall_model_risk
        assert r_low > r_high

    def test_all_sub_scores_in_range(self, risk_input):
        r = ModelRiskAnalyzer().analyse(risk_input)
        for s in (r.overfitting_risk, r.regime_sensitivity_risk,
                  r.confidence_risk, r.complexity_risk,
                  r.data_quality_risk, r.overall_model_risk):
            assert 0.0 <= s <= 100.0


class TestRiskAnalysisOrchestrator:
    def test_analyse_returns_result(self, risk_input):
        result = RiskAnalysis().analyse(risk_input)
        assert 0.0 <= result.composite_risk_score <= 100.0

    def test_high_risk_higher_than_low_risk(self, high_risk_input, low_risk_input):
        high = RiskAnalysis().analyse(high_risk_input).composite_risk_score
        low  = RiskAnalysis().analyse(low_risk_input).composite_risk_score
        assert high > low

    def test_expected_loss_fields_positive(self, risk_input):
        r = RiskAnalysis().analyse(risk_input)
        assert r.expected_daily_loss_95 > 0.0
        assert r.expected_weekly_loss_95 > 0.0
        assert r.expected_monthly_loss_95 > 0.0

    def test_risk_factors_list(self, risk_input):
        r = RiskAnalysis().analyse(risk_input)
        assert isinstance(r.risk_factors, list)
        assert len(r.risk_factors) <= 3
