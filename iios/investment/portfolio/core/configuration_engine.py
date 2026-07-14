"""iios/investment/portfolio/core/configuration_engine.py

Configuration engine for the Institutional Portfolio Framework.
Responsible for loading, validating, merging, and applying profiles
to produce a validated PortfolioConfiguration.
"""
from __future__ import annotations

import copy
from dataclasses import replace
from typing import Any, Optional

from iios.investment.portfolio.core.configuration_profiles import (
    ConfigurationProfile,
    get_profile,
    get_default_profile,
)
from iios.investment.portfolio.core.parameter_registry import PARAMETER_REGISTRY
from iios.investment.portfolio.core.parameter_validation import (
    ParameterValidator,
    ValidationResult,
)
from iios.investment.portfolio.core.portfolio_configuration import (
    AllocationPolicy,
    CapitalLimits,
    InvestmentObjective,
    PortfolioConfiguration,
    PortfolioConfigurationError,
    RebalancingPolicy,
    RiskPolicy,
)
from iios.investment.portfolio.core.portfolio_types import (
    PortfolioDomain,
    ValidationOutcome,
)


class ConfigurationEngine:
    """
    Builds and validates PortfolioConfiguration objects.

    Workflow:
        1. Start from a profile (or empty defaults).
        2. Apply caller-supplied overrides.
        3. Validate all parameters.
        4. Return the final, validated configuration.
    """

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def from_profile(
        self,
        profile_name: str,
        *,
        portfolio_id: str = "",
        overrides: Optional[dict[str, Any]] = None,
    ) -> PortfolioConfiguration:
        """Build a configuration starting from a named profile."""
        profile = get_profile(profile_name)
        if profile is None:
            raise PortfolioConfigurationError(
                f"Unknown profile: {profile_name!r}", field="profile_name"
            )
        base = profile.configuration
        if portfolio_id:
            base = replace(base, portfolio_id=portfolio_id)
        if overrides:
            base = self._apply_overrides(base, overrides)
        self._validate_or_raise(base)
        return base

    def from_domain(
        self,
        domain: PortfolioDomain,
        *,
        portfolio_id: str = "",
        overrides: Optional[dict[str, Any]] = None,
    ) -> PortfolioConfiguration:
        """Build a configuration from a domain's default profile."""
        profile = get_default_profile(domain)
        if profile is None:
            # Fall back to empty defaults
            base = PortfolioConfiguration(portfolio_id=portfolio_id)
        else:
            base = profile.configuration
            if portfolio_id:
                base = replace(base, portfolio_id=portfolio_id)
        if overrides:
            base = self._apply_overrides(base, overrides)
        self._validate_or_raise(base)
        return base

    def from_dict(self, data: dict[str, Any]) -> PortfolioConfiguration:
        """
        Build a PortfolioConfiguration from a plain dict.
        Recognises the standard serialisation keys produced by to_dict().
        """
        portfolio_id = data.get("portfolio_id", "")
        profile_name = data.get("profile_name", "custom")
        environment  = data.get("environment", "production")

        # Objective
        obj_d = data.get("objective", {})
        objective = InvestmentObjective(
            primary_objective     = obj_d.get("primary_objective",     "growth"),
            target_return_pct     = float(obj_d.get("target_return_pct",     0.0)),
            target_yield_pct      = float(obj_d.get("target_yield_pct",      0.0)),
            benchmark             = obj_d.get("benchmark",             ""),
            tracking_error_max    = float(obj_d.get("tracking_error_max",    0.0)),
            information_ratio_min = float(obj_d.get("information_ratio_min", 0.0)),
            use_absolute_return   = bool(obj_d.get("use_absolute_return",    False)),
        )

        # Capital limits
        cap_d = data.get("capital_limits", {})
        capital_limits = CapitalLimits(
            min_capital           = float(cap_d.get("min_capital",           0.0)),
            max_capital           = float(cap_d.get("max_capital",           1e12)),
            initial_capital       = float(cap_d.get("initial_capital",       0.0)),
            min_cash_reserve_pct  = float(cap_d.get("min_cash_reserve_pct",  0.02)),
            max_cash_pct          = float(cap_d.get("max_cash_pct",          0.50)),
            capital_currency      = cap_d.get("capital_currency",            "INR"),
            allow_leverage        = bool(cap_d.get("allow_leverage",         False)),
            max_leverage_ratio    = float(cap_d.get("max_leverage_ratio",    1.0)),
        )

        # Allocation policy
        alloc_d = data.get("allocation_policy", {})
        allocation_policy = AllocationPolicy(
            max_single_position_pct = float(alloc_d.get("max_single_position_pct", 0.10)),
            min_single_position_pct = float(alloc_d.get("min_single_position_pct", 0.001)),
            max_sector_pct          = float(alloc_d.get("max_sector_pct",          0.30)),
            max_asset_class_pct     = float(alloc_d.get("max_asset_class_pct",     0.80)),
            min_positions           = int(alloc_d.get("min_positions",             3)),
            max_positions           = int(alloc_d.get("max_positions",             100)),
            allow_short_positions   = bool(alloc_d.get("allow_short_positions",    False)),
            max_short_pct           = float(alloc_d.get("max_short_pct",           0.0)),
            equal_weight            = bool(alloc_d.get("equal_weight",             False)),
        )

        # Risk policy
        risk_d = data.get("risk_policy", {})
        risk_policy = RiskPolicy(
            max_drawdown_pct          = float(risk_d.get("max_drawdown_pct",          0.20)),
            max_daily_loss_pct        = float(risk_d.get("max_daily_loss_pct",        0.03)),
            max_weekly_loss_pct       = float(risk_d.get("max_weekly_loss_pct",       0.08)),
            max_monthly_loss_pct      = float(risk_d.get("max_monthly_loss_pct",      0.15)),
            max_volatility_annual_pct = float(risk_d.get("max_volatility_annual_pct", 0.30)),
            min_sharpe_ratio          = float(risk_d.get("min_sharpe_ratio",          0.0)),
            max_beta                  = float(risk_d.get("max_beta",                  2.0)),
            max_var_95_pct            = float(risk_d.get("max_var_95_pct",            0.05)),
            stop_loss_pct             = float(risk_d.get("stop_loss_pct",             0.0)),
            risk_on_flag              = bool(risk_d.get("risk_on_flag",               True)),
        )

        # Rebalancing policy
        reb_d = data.get("rebalancing_policy", {})
        rebalancing_policy = RebalancingPolicy(
            trigger             = reb_d.get("trigger",             "calendar"),
            frequency_days      = int(reb_d.get("frequency_days",      30)),
            drift_threshold_pct = float(reb_d.get("drift_threshold_pct", 0.05)),
            time_of_day         = reb_d.get("time_of_day",          "09:30"),
            allow_fractional    = bool(reb_d.get("allow_fractional",    False)),
            min_trade_size      = float(reb_d.get("min_trade_size",     0.0)),
            rebalance_on_signal = bool(reb_d.get("rebalance_on_signal", False)),
            cooldown_hours      = float(reb_d.get("cooldown_hours",     24.0)),
        )

        config = PortfolioConfiguration(
            portfolio_id       = portfolio_id,
            profile_name       = profile_name,
            environment        = environment,
            objective          = objective,
            capital_limits     = capital_limits,
            allocation_policy  = allocation_policy,
            risk_policy        = risk_policy,
            rebalancing_policy = rebalancing_policy,
            extra              = data.get("extra", {}),
        )
        self._validate_or_raise(config)
        return config

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self, config: PortfolioConfiguration) -> list[ValidationResult]:
        """
        Run full validation; return all results (pass and fail).
        Does NOT raise — callers decide how to handle failures.
        """
        results: list[ValidationResult] = []
        reg = PARAMETER_REGISTRY

        # Validate known parameters
        field_map = {
            "initial_capital":          config.capital_limits.initial_capital,
            "min_capital":              config.capital_limits.min_capital,
            "max_capital":              config.capital_limits.max_capital,
            "min_cash_reserve_pct":     config.capital_limits.min_cash_reserve_pct,
            "allow_leverage":           config.capital_limits.allow_leverage,
            "max_leverage_ratio":       config.capital_limits.max_leverage_ratio,
            "max_single_position_pct":  config.allocation_policy.max_single_position_pct,
            "max_sector_pct":           config.allocation_policy.max_sector_pct,
            "min_positions":            config.allocation_policy.min_positions,
            "max_positions":            config.allocation_policy.max_positions,
            "max_drawdown_pct":         config.risk_policy.max_drawdown_pct,
            "max_daily_loss_pct":       config.risk_policy.max_daily_loss_pct,
            "rebalance_trigger":        config.rebalancing_policy.trigger,
            "rebalance_frequency_days": config.rebalancing_policy.frequency_days,
            "environment":              config.environment,
        }
        for name, value in field_map.items():
            try:
                defn = reg.get(name)
                results.extend(ParameterValidator.validate(defn, value))
            except KeyError:
                pass  # not in registry — skip

        return results

    def has_errors(self, results: list[ValidationResult]) -> bool:
        return any(r.outcome == ValidationOutcome.FAILED for r in results)

    # ------------------------------------------------------------------
    # Merging
    # ------------------------------------------------------------------

    def merge(
        self,
        base: PortfolioConfiguration,
        overrides: dict[str, Any],
    ) -> PortfolioConfiguration:
        """Apply a flat or nested overrides dict onto a base configuration."""
        merged = self._apply_overrides(base, overrides)
        self._validate_or_raise(merged)
        return merged

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _apply_overrides(
        self,
        base: PortfolioConfiguration,
        overrides: dict[str, Any],
    ) -> PortfolioConfiguration:
        """
        Apply a shallow overrides dict.  Supports nested keys via section
        prefix: e.g. {"risk_policy.max_drawdown_pct": 0.15}.
        """
        # Collect section-level overrides
        cap_ovr:   dict[str, Any] = {}
        alloc_ovr: dict[str, Any] = {}
        risk_ovr:  dict[str, Any] = {}
        reb_ovr:   dict[str, Any] = {}
        obj_ovr:   dict[str, Any] = {}
        top_ovr:   dict[str, Any] = {}

        for key, val in overrides.items():
            if key.startswith("capital_limits."):
                cap_ovr[key[len("capital_limits."):]] = val
            elif key.startswith("allocation_policy."):
                alloc_ovr[key[len("allocation_policy."):]] = val
            elif key.startswith("risk_policy."):
                risk_ovr[key[len("risk_policy."):]] = val
            elif key.startswith("rebalancing_policy."):
                reb_ovr[key[len("rebalancing_policy."):]] = val
            elif key.startswith("objective."):
                obj_ovr[key[len("objective."):]] = val
            else:
                top_ovr[key] = val

        # Rebuild sub-objects with overrides applied
        cap   = replace(base.capital_limits,    **cap_ovr)   if cap_ovr   else base.capital_limits
        alloc = replace(base.allocation_policy, **alloc_ovr) if alloc_ovr else base.allocation_policy
        risk  = replace(base.risk_policy,       **risk_ovr)  if risk_ovr  else base.risk_policy
        reb   = replace(base.rebalancing_policy,**reb_ovr)   if reb_ovr   else base.rebalancing_policy
        obj   = replace(base.objective,         **obj_ovr)   if obj_ovr   else base.objective

        return replace(
            base,
            capital_limits     = cap,
            allocation_policy  = alloc,
            risk_policy        = risk,
            rebalancing_policy = reb,
            objective          = obj,
            **{k: v for k, v in top_ovr.items()
               if k in ("portfolio_id", "profile_name", "environment")},
        )

    def _validate_or_raise(self, config: PortfolioConfiguration) -> None:
        config.validate()
        results = self.validate(config)
        failures = [r for r in results if r.outcome == ValidationOutcome.FAILED]
        if failures:
            msgs = "; ".join(r.message for r in failures)
            raise PortfolioConfigurationError(msgs)
