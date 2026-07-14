"""tests/unit/investment/portfolio/core/test_types_and_config.py

Tests for types, asset support, investment style, metadata, configuration,
parameters, and configuration profiles/engine.
"""
from __future__ import annotations

import pytest

from iios.investment.portfolio.core.asset_support import (
    ASSET_SUPPORT_MATRIX,
    get_asset_descriptor,
)
from iios.investment.portfolio.core.configuration_engine import ConfigurationEngine
from iios.investment.portfolio.core.configuration_profiles import (
    get_default_profile,
    get_profile,
    list_profiles,
)
from iios.investment.portfolio.core.investment_style import (
    InvestmentStyle,
    InvestmentHorizon,
    STYLE_REGISTRY,
)
from iios.investment.portfolio.core.parameter_registry import (
    PARAMETER_REGISTRY,
    ParameterDefinition,
    ParameterType,
)
from iios.investment.portfolio.core.parameter_validation import (
    AllowedValuesRule,
    MaxValueRule,
    MinValueRule,
    ParameterValidator,
    RangeRule,
    RequiredRule,
    ValidationOutcome,
)
from iios.investment.portfolio.core.portfolio_configuration import (
    AllocationPolicy,
    CapitalLimits,
    PortfolioConfigurationError,
    PortfolioConfiguration,
    RiskPolicy,
)
from iios.investment.portfolio.core.portfolio_metadata import build_metadata
from iios.investment.portfolio.core.portfolio_types import (
    PortfolioCapability,
    PortfolioDomain,
    PortfolioLifecycleState,
    FrameworkStatus,
    ValidationOutcome as VO,
)
from iios.investment.portfolio.portfolio_constants import AssetClass


class TestPortfolioLifecycleState:
    def test_terminal_states(self):
        assert PortfolioLifecycleState.ARCHIVED.is_terminal
        assert PortfolioLifecycleState.FAILED.is_terminal
        assert not PortfolioLifecycleState.ACTIVE.is_terminal

    def test_operational_states(self):
        assert PortfolioLifecycleState.ACTIVE.is_operational
        assert PortfolioLifecycleState.MONITORING.is_operational
        assert not PortfolioLifecycleState.PAUSED.is_operational

    def test_accepts_orders(self):
        assert PortfolioLifecycleState.ACTIVE.accepts_orders
        assert not PortfolioLifecycleState.ARCHIVED.accepts_orders


class TestPortfolioDomain:
    def test_all_nine_domains_defined(self):
        expected = {
            "long_term", "swing", "intraday", "etf", "dividend",
            "options", "futures", "crypto", "multi_asset",
        }
        defined = {d.value for d in PortfolioDomain if d != PortfolioDomain.CUSTOM}
        assert expected.issubset(defined)

    def test_default_horizon(self):
        assert PortfolioDomain.INTRADAY.default_horizon_days == 1
        assert PortfolioDomain.LONG_TERM.default_horizon_days > 365


class TestAssetSupportMatrix:
    def test_intraday_supports_equity(self):
        assert ASSET_SUPPORT_MATRIX.supports(PortfolioDomain.INTRADAY, AssetClass.EQUITY)

    def test_dividend_supports_equity(self):
        assert ASSET_SUPPORT_MATRIX.supports(PortfolioDomain.DIVIDEND, AssetClass.EQUITY)

    def test_options_does_not_support_equity(self):
        assert not ASSET_SUPPORT_MATRIX.supports(PortfolioDomain.OPTIONS, AssetClass.EQUITY)

    def test_multi_asset_supports_all(self):
        for ac in (AssetClass.EQUITY, AssetClass.DEBT, AssetClass.COMMODITY,
                   AssetClass.DERIVATIVE):
            assert ASSET_SUPPORT_MATRIX.supports(PortfolioDomain.MULTI_ASSET, ac)

    def test_domains_for_asset(self):
        domains = ASSET_SUPPORT_MATRIX.domains_for_asset(AssetClass.EQUITY)
        assert PortfolioDomain.LONG_TERM in domains

    def test_to_dict_keys(self):
        d = ASSET_SUPPORT_MATRIX.to_dict()
        assert "long_term" in d

    def test_get_asset_descriptor(self):
        desc = get_asset_descriptor(AssetClass.EQUITY)
        assert desc.display_name == "Equity"
        assert "NSE" in desc.exchanges


class TestInvestmentStyle:
    def test_index_is_passive(self):
        assert not InvestmentStyle.INDEX.is_active

    def test_value_is_active(self):
        assert InvestmentStyle.VALUE.is_active

    def test_style_registry_contains_value(self):
        profile = STYLE_REGISTRY.get(InvestmentStyle.VALUE)
        assert profile is not None
        assert profile.primary_style == InvestmentStyle.VALUE

    def test_constraints_for_value(self):
        c = STYLE_REGISTRY.constraints_for(InvestmentStyle.VALUE)
        assert c is not None
        assert c.max_positions <= 50

    def test_horizon_min_holding_days(self):
        assert InvestmentHorizon.INTRADAY.min_holding_days == 0
        assert InvestmentHorizon.LONG_TERM.min_holding_days >= 365

    def test_style_profile_to_dict(self):
        p = STYLE_REGISTRY.get(InvestmentStyle.MOMENTUM)
        if p:
            d = p.to_dict()
            assert "primary_style" in d
            assert "constraints" in d


class TestPortfolioMetadata:
    def test_build_metadata(self):
        m = build_metadata("P1", "My Portfolio", PortfolioDomain.SWING)
        assert m.portfolio_id == "P1"
        assert m.domain == PortfolioDomain.SWING

    def test_has_capability(self):
        m = build_metadata(
            "P1", "Test", PortfolioDomain.INTRADAY,
            capabilities=frozenset({PortfolioCapability.LEVERAGE}),
        )
        assert m.has_capability(PortfolioCapability.LEVERAGE)
        assert not m.has_capability(PortfolioCapability.MULTI_CURRENCY)

    def test_has_tag(self):
        m = build_metadata(
            "P1", "Test", PortfolioDomain.ETF,
            tags=frozenset({"institutional", "nifty50"}),
        )
        assert m.has_tag("institutional")
        assert not m.has_tag("crypto")

    def test_to_dict(self):
        m = build_metadata("P1", "Test", PortfolioDomain.LONG_TERM)
        d = m.to_dict()
        assert d["portfolio_id"] == "P1"
        assert d["domain"] == "long_term"

    def test_frozen(self):
        m = build_metadata("P1", "Test", PortfolioDomain.SWING)
        with pytest.raises((AttributeError, TypeError)):
            m.name = "changed"  # type: ignore


class TestPortfolioConfiguration:
    def test_capital_limits_validate(self):
        cl = CapitalLimits(min_capital=0.0, max_capital=1_000_000.0)
        cl.validate()  # should not raise

    def test_capital_limits_invalid(self):
        cl = CapitalLimits(min_capital=500_000.0, max_capital=100_000.0)
        with pytest.raises(PortfolioConfigurationError):
            cl.validate()

    def test_leverage_without_flag(self):
        cl = CapitalLimits(allow_leverage=False, max_leverage_ratio=3.0)
        with pytest.raises(PortfolioConfigurationError):
            cl.validate()

    def test_allocation_policy_validate(self):
        ap = AllocationPolicy(min_positions=5, max_positions=20)
        ap.validate()  # should not raise

    def test_allocation_policy_invalid(self):
        ap = AllocationPolicy(min_positions=10, max_positions=5)
        with pytest.raises(PortfolioConfigurationError):
            ap.validate()

    def test_risk_policy_validate(self):
        rp = RiskPolicy(max_drawdown_pct=0.20, max_daily_loss_pct=0.03)
        rp.validate()  # should not raise

    def test_full_config_to_dict(self):
        cfg = PortfolioConfiguration()
        d = cfg.to_dict()
        assert "capital_limits" in d
        assert "risk_policy" in d
        assert "allocation_policy" in d


class TestParameterRegistry:
    def test_built_ins_registered(self):
        assert PARAMETER_REGISTRY.count() > 0
        assert "max_drawdown_pct" in PARAMETER_REGISTRY.all_names()

    def test_get_parameter(self):
        defn = PARAMETER_REGISTRY.get("max_drawdown_pct")
        assert defn.param_type == ParameterType.FLOAT
        assert defn.min_value == pytest.approx(0.001)

    def test_by_section(self):
        risk_params = PARAMETER_REGISTRY.by_section("risk_policy")
        assert len(risk_params) >= 2

    def test_required_params(self):
        # No required params by default in our built-ins
        req = PARAMETER_REGISTRY.required_params()
        assert isinstance(req, list)

    def test_register_custom(self):
        reg = PARAMETER_REGISTRY.__class__()  # fresh instance
        defn = ParameterDefinition(
            name="custom_param", param_type=ParameterType.FLOAT, default=1.0
        )
        reg.register(defn)
        assert "custom_param" in reg.all_names()

    def test_no_duplicate_without_overwrite(self):
        reg = PARAMETER_REGISTRY.__class__()
        defn = ParameterDefinition(name="x", param_type=ParameterType.INTEGER)
        reg.register(defn)
        with pytest.raises(ValueError):
            reg.register(defn)


class TestParameterValidation:
    def test_required_pass(self):
        r = RequiredRule().validate("x", 42)
        assert r.passed

    def test_required_fail(self):
        r = RequiredRule().validate("x", None)
        assert not r.passed
        assert r.outcome == ValidationOutcome.FAILED

    def test_min_value_pass(self):
        r = MinValueRule(0.0).validate("x", 10.0)
        assert r.passed

    def test_min_value_fail(self):
        r = MinValueRule(0.0).validate("x", -1.0)
        assert not r.passed

    def test_max_value_pass(self):
        r = MaxValueRule(100.0).validate("x", 50.0)
        assert r.passed

    def test_max_value_fail(self):
        r = MaxValueRule(100.0).validate("x", 200.0)
        assert not r.passed

    def test_range_pass(self):
        r = RangeRule(0.0, 1.0).validate("x", 0.5)
        assert r.passed

    def test_range_fail(self):
        r = RangeRule(0.0, 1.0).validate("x", 1.5)
        assert not r.passed

    def test_allowed_values_pass(self):
        r = AllowedValuesRule({"a", "b"}).validate("x", "a")
        assert r.passed

    def test_allowed_values_fail(self):
        r = AllowedValuesRule({"a", "b"}).validate("x", "c")
        assert not r.passed

    def test_validator_with_defn(self):
        defn = PARAMETER_REGISTRY.get("max_drawdown_pct")
        assert ParameterValidator.is_valid(defn, 0.20)
        assert not ParameterValidator.is_valid(defn, -0.10)

    def test_validation_result_to_dict(self):
        r = RequiredRule().validate("field", None)
        d = r.to_dict()
        assert "outcome" in d
        assert "field_name" in d


class TestConfigurationProfiles:
    def test_list_profiles_non_empty(self):
        profiles = list_profiles()
        assert len(profiles) >= 9

    def test_get_profile_exists(self):
        p = get_profile("long_term_default")
        assert p is not None
        assert p.domain == PortfolioDomain.LONG_TERM

    def test_get_default_profile(self):
        p = get_default_profile(PortfolioDomain.CRYPTO)
        assert p is not None
        assert p.domain == PortfolioDomain.CRYPTO

    def test_profile_config_is_valid(self):
        p = get_profile("swing_default")
        assert p is not None
        p.configuration.validate()  # should not raise

    def test_profile_to_dict(self):
        p = get_profile("etf_default")
        assert p is not None
        d = p.to_dict()
        assert "profile_name" in d
        assert "configuration" in d


class TestConfigurationEngine:
    def test_from_domain(self):
        eng = ConfigurationEngine()
        cfg = eng.from_domain(PortfolioDomain.SWING, portfolio_id="P1")
        assert cfg.portfolio_id == "P1"
        assert cfg.allocation_policy.max_positions > 0

    def test_from_profile(self):
        eng = ConfigurationEngine()
        cfg = eng.from_profile("long_term_default", portfolio_id="P2")
        assert cfg.profile_name == "long_term_default"

    def test_from_dict_round_trip(self):
        eng = ConfigurationEngine()
        cfg1 = eng.from_domain(PortfolioDomain.ETF, portfolio_id="P3")
        d = cfg1.to_dict()
        cfg2 = eng.from_dict(d)
        assert cfg2.portfolio_id == cfg1.portfolio_id
        assert cfg2.environment == cfg1.environment

    def test_merge_overrides(self):
        eng = ConfigurationEngine()
        cfg = eng.from_domain(PortfolioDomain.LONG_TERM, portfolio_id="P4")
        merged = eng.merge(cfg, {"risk_policy.max_drawdown_pct": 0.15})
        assert merged.risk_policy.max_drawdown_pct == pytest.approx(0.15)

    def test_invalid_environment_raises(self):
        eng = ConfigurationEngine()
        with pytest.raises(Exception):
            eng.from_dict({"environment": "invalid_env", "portfolio_id": "P"})

    def test_validate_returns_results(self):
        eng = ConfigurationEngine()
        cfg = eng.from_domain(PortfolioDomain.SWING)
        results = eng.validate(cfg)
        assert isinstance(results, list)
