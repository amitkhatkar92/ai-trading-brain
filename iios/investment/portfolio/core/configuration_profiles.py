"""iios/investment/portfolio/core/configuration_profiles.py

Pre-built configuration profiles for the nine canonical portfolio domains.
Profiles define sensible institutional defaults; all values are overridable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from iios.investment.portfolio.core.portfolio_configuration import (
    AllocationPolicy,
    CapitalLimits,
    InvestmentObjective,
    PortfolioConfiguration,
    RebalancingPolicy,
    RiskPolicy,
)
from iios.investment.portfolio.core.portfolio_types import PortfolioDomain


@dataclass(frozen=True)
class ConfigurationProfile:
    """Named, reusable configuration template."""

    profile_name: str
    domain:       PortfolioDomain
    description:  str
    configuration: PortfolioConfiguration

    def to_dict(self) -> dict:
        return {
            "profile_name":  self.profile_name,
            "domain":        self.domain.value,
            "description":   self.description,
            "configuration": self.configuration.to_dict(),
        }


# ---------------------------------------------------------------------------
# Profile definitions
# ---------------------------------------------------------------------------

_LONG_TERM_PROFILE = ConfigurationProfile(
    profile_name  = "long_term_default",
    domain        = PortfolioDomain.LONG_TERM,
    description   = "Long-term investment portfolio — buy-and-hold, low turnover.",
    configuration = PortfolioConfiguration(
        profile_name      = "long_term_default",
        environment       = "production",
        objective         = InvestmentObjective(
            primary_objective   = "growth",
            target_return_pct   = 0.15,
            benchmark           = "NIFTY50",
        ),
        capital_limits    = CapitalLimits(
            initial_capital      = 1_000_000.0,
            min_capital          = 100_000.0,
            max_capital          = 1e11,
            min_cash_reserve_pct = 0.03,
            max_cash_pct         = 0.20,
        ),
        allocation_policy = AllocationPolicy(
            max_single_position_pct = 0.12,
            max_sector_pct          = 0.30,
            min_positions           = 10,
            max_positions           = 50,
        ),
        risk_policy       = RiskPolicy(
            max_drawdown_pct          = 0.30,
            max_daily_loss_pct        = 0.05,
            max_volatility_annual_pct = 0.20,
        ),
        rebalancing_policy= RebalancingPolicy(
            trigger          = "calendar",
            frequency_days   = 90,
            drift_threshold_pct = 0.10,
            cooldown_hours   = 72.0,
        ),
    ),
)

_SWING_PROFILE = ConfigurationProfile(
    profile_name  = "swing_default",
    domain        = PortfolioDomain.SWING,
    description   = "Swing trading portfolio — 2–14 day holding periods.",
    configuration = PortfolioConfiguration(
        profile_name      = "swing_default",
        environment       = "production",
        objective         = InvestmentObjective(primary_objective = "total_return"),
        capital_limits    = CapitalLimits(
            initial_capital      = 500_000.0,
            min_capital          = 50_000.0,
            max_capital          = 1e10,
            min_cash_reserve_pct = 0.05,
        ),
        allocation_policy = AllocationPolicy(
            max_single_position_pct = 0.15,
            max_sector_pct          = 0.35,
            min_positions           = 5,
            max_positions           = 20,
        ),
        risk_policy       = RiskPolicy(
            max_drawdown_pct    = 0.15,
            max_daily_loss_pct  = 0.03,
            stop_loss_pct       = 0.05,
        ),
        rebalancing_policy= RebalancingPolicy(
            trigger             = "signal",
            rebalance_on_signal = True,
            cooldown_hours      = 4.0,
        ),
    ),
)

_INTRADAY_PROFILE = ConfigurationProfile(
    profile_name  = "intraday_default",
    domain        = PortfolioDomain.INTRADAY,
    description   = "Intraday trading portfolio — all positions closed by end of session.",
    configuration = PortfolioConfiguration(
        profile_name      = "intraday_default",
        environment       = "production",
        objective         = InvestmentObjective(primary_objective = "total_return"),
        capital_limits    = CapitalLimits(
            initial_capital      = 200_000.0,
            min_capital          = 25_000.0,
            max_capital          = 5e9,
            min_cash_reserve_pct = 0.10,
            allow_leverage       = True,
            max_leverage_ratio   = 5.0,
        ),
        allocation_policy = AllocationPolicy(
            max_single_position_pct = 0.20,
            max_sector_pct          = 0.50,
            min_positions           = 1,
            max_positions           = 10,
        ),
        risk_policy       = RiskPolicy(
            max_drawdown_pct   = 0.05,
            max_daily_loss_pct = 0.02,
            stop_loss_pct      = 0.01,
        ),
        rebalancing_policy= RebalancingPolicy(
            trigger             = "signal",
            rebalance_on_signal = True,
            cooldown_hours      = 0.25,
        ),
    ),
)

_ETF_PROFILE = ConfigurationProfile(
    profile_name  = "etf_default",
    domain        = PortfolioDomain.ETF,
    description   = "ETF portfolio — diversified, low-cost, index-adjacent.",
    configuration = PortfolioConfiguration(
        profile_name      = "etf_default",
        environment       = "production",
        objective         = InvestmentObjective(
            primary_objective = "growth",
            benchmark         = "NIFTY50",
            tracking_error_max= 0.05,
        ),
        capital_limits    = CapitalLimits(
            initial_capital = 500_000.0,
            min_capital     = 50_000.0,
        ),
        allocation_policy = AllocationPolicy(
            max_single_position_pct = 0.25,
            max_sector_pct          = 0.40,
            min_positions           = 5,
            max_positions           = 30,
        ),
        risk_policy       = RiskPolicy(
            max_drawdown_pct          = 0.25,
            max_daily_loss_pct        = 0.04,
            max_volatility_annual_pct = 0.18,
        ),
        rebalancing_policy= RebalancingPolicy(
            trigger        = "calendar",
            frequency_days = 30,
            cooldown_hours = 24.0,
        ),
    ),
)

_DIVIDEND_PROFILE = ConfigurationProfile(
    profile_name  = "dividend_default",
    domain        = PortfolioDomain.DIVIDEND,
    description   = "Dividend income portfolio — high yield, stable businesses.",
    configuration = PortfolioConfiguration(
        profile_name      = "dividend_default",
        environment       = "production",
        objective         = InvestmentObjective(
            primary_objective = "income",
            target_yield_pct  = 0.04,
        ),
        capital_limits    = CapitalLimits(
            initial_capital      = 2_000_000.0,
            min_capital          = 200_000.0,
            min_cash_reserve_pct = 0.05,
        ),
        allocation_policy = AllocationPolicy(
            max_single_position_pct = 0.10,
            max_sector_pct          = 0.25,
            min_positions           = 15,
            max_positions           = 50,
        ),
        risk_policy       = RiskPolicy(
            max_drawdown_pct          = 0.20,
            max_daily_loss_pct        = 0.03,
            max_volatility_annual_pct = 0.15,
        ),
        rebalancing_policy= RebalancingPolicy(
            trigger        = "calendar",
            frequency_days = 180,
            cooldown_hours = 48.0,
        ),
    ),
)

_OPTIONS_PROFILE = ConfigurationProfile(
    profile_name  = "options_default",
    domain        = PortfolioDomain.OPTIONS,
    description   = "Options portfolio — derivatives-centric, volatility-aware.",
    configuration = PortfolioConfiguration(
        profile_name      = "options_default",
        environment       = "production",
        objective         = InvestmentObjective(primary_objective = "total_return"),
        capital_limits    = CapitalLimits(
            initial_capital      = 300_000.0,
            min_capital          = 50_000.0,
            min_cash_reserve_pct = 0.20,  # Higher buffer for margin
        ),
        allocation_policy = AllocationPolicy(
            max_single_position_pct = 0.15,
            max_sector_pct          = 0.40,
            min_positions           = 2,
            max_positions           = 30,
        ),
        risk_policy       = RiskPolicy(
            max_drawdown_pct   = 0.25,
            max_daily_loss_pct = 0.04,
            max_var_95_pct     = 0.05,
        ),
        rebalancing_policy= RebalancingPolicy(
            trigger             = "signal",
            rebalance_on_signal = True,
            cooldown_hours      = 1.0,
        ),
    ),
)

_FUTURES_PROFILE = ConfigurationProfile(
    profile_name  = "futures_default",
    domain        = PortfolioDomain.FUTURES,
    description   = "Futures portfolio — systematic trend and carry.",
    configuration = PortfolioConfiguration(
        profile_name      = "futures_default",
        environment       = "production",
        objective         = InvestmentObjective(primary_objective = "total_return"),
        capital_limits    = CapitalLimits(
            initial_capital      = 500_000.0,
            min_capital          = 100_000.0,
            min_cash_reserve_pct = 0.25,
            allow_leverage       = True,
            max_leverage_ratio   = 3.0,
        ),
        allocation_policy = AllocationPolicy(
            max_single_position_pct = 0.20,
            max_sector_pct          = 0.40,
            min_positions           = 2,
            max_positions           = 20,
        ),
        risk_policy       = RiskPolicy(
            max_drawdown_pct   = 0.20,
            max_daily_loss_pct = 0.03,
            max_var_95_pct     = 0.04,
        ),
        rebalancing_policy= RebalancingPolicy(
            trigger             = "signal",
            rebalance_on_signal = True,
            cooldown_hours      = 2.0,
        ),
    ),
)

_CRYPTO_PROFILE = ConfigurationProfile(
    profile_name  = "crypto_default",
    domain        = PortfolioDomain.CRYPTO,
    description   = "Crypto portfolio — digital assets with high volatility tolerance.",
    configuration = PortfolioConfiguration(
        profile_name      = "crypto_default",
        environment       = "production",
        objective         = InvestmentObjective(primary_objective = "growth"),
        capital_limits    = CapitalLimits(
            initial_capital      = 100_000.0,
            min_capital          = 10_000.0,
            min_cash_reserve_pct = 0.10,
        ),
        allocation_policy = AllocationPolicy(
            max_single_position_pct = 0.25,
            max_sector_pct          = 1.0,
            min_positions           = 3,
            max_positions           = 20,
        ),
        risk_policy       = RiskPolicy(
            max_drawdown_pct          = 0.50,
            max_daily_loss_pct        = 0.10,
            max_volatility_annual_pct = 1.00,
        ),
        rebalancing_policy= RebalancingPolicy(
            trigger        = "calendar",
            frequency_days = 7,
            cooldown_hours = 1.0,
        ),
    ),
)

_MULTI_ASSET_PROFILE = ConfigurationProfile(
    profile_name  = "multi_asset_default",
    domain        = PortfolioDomain.MULTI_ASSET,
    description   = "Multi-asset portfolio — all asset classes, institutional-grade diversification.",
    configuration = PortfolioConfiguration(
        profile_name      = "multi_asset_default",
        environment       = "production",
        objective         = InvestmentObjective(
            primary_objective = "total_return",
            benchmark         = "MULTI_ASSET_60_40",
        ),
        capital_limits    = CapitalLimits(
            initial_capital      = 10_000_000.0,
            min_capital          = 1_000_000.0,
            min_cash_reserve_pct = 0.05,
        ),
        allocation_policy = AllocationPolicy(
            max_single_position_pct = 0.08,
            max_sector_pct          = 0.25,
            max_asset_class_pct     = 0.60,
            min_positions           = 20,
            max_positions           = 200,
        ),
        risk_policy       = RiskPolicy(
            max_drawdown_pct          = 0.20,
            max_daily_loss_pct        = 0.03,
            max_volatility_annual_pct = 0.15,
            min_sharpe_ratio          = 0.50,
        ),
        rebalancing_policy= RebalancingPolicy(
            trigger             = "drift",
            drift_threshold_pct = 0.05,
            frequency_days      = 30,
            cooldown_hours      = 24.0,
        ),
    ),
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_PROFILES: dict[str, ConfigurationProfile] = {
    p.profile_name: p
    for p in (
        _LONG_TERM_PROFILE, _SWING_PROFILE, _INTRADAY_PROFILE,
        _ETF_PROFILE, _DIVIDEND_PROFILE, _OPTIONS_PROFILE,
        _FUTURES_PROFILE, _CRYPTO_PROFILE, _MULTI_ASSET_PROFILE,
    )
}

_DOMAIN_DEFAULT: dict[PortfolioDomain, str] = {
    PortfolioDomain.LONG_TERM:   "long_term_default",
    PortfolioDomain.SWING:       "swing_default",
    PortfolioDomain.INTRADAY:    "intraday_default",
    PortfolioDomain.ETF:         "etf_default",
    PortfolioDomain.DIVIDEND:    "dividend_default",
    PortfolioDomain.OPTIONS:     "options_default",
    PortfolioDomain.FUTURES:     "futures_default",
    PortfolioDomain.CRYPTO:      "crypto_default",
    PortfolioDomain.MULTI_ASSET: "multi_asset_default",
}


def get_profile(name: str) -> Optional[ConfigurationProfile]:
    """Return a profile by name, or None if not found."""
    return _PROFILES.get(name)


def get_default_profile(domain: PortfolioDomain) -> Optional[ConfigurationProfile]:
    """Return the default profile for a domain."""
    name = _DOMAIN_DEFAULT.get(domain)
    return _PROFILES.get(name) if name else None


def list_profiles() -> list[str]:
    """All registered profile names."""
    return sorted(_PROFILES.keys())


def register_profile(profile: ConfigurationProfile, *, overwrite: bool = False) -> None:
    """Register a custom profile. Thread-unsafe at module level — call at startup only."""
    if profile.profile_name in _PROFILES and not overwrite:
        raise ValueError(f"Profile already registered: {profile.profile_name!r}")
    _PROFILES[profile.profile_name] = profile
