"""iios/investment/portfolio/core/portfolio_configuration.py

Configuration data structures for the Institutional Portfolio Framework.
All configuration objects are immutable frozen dataclasses.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, FrozenSet, Optional


class PortfolioConfigurationError(ValueError):
    """Raised when a portfolio configuration is invalid."""

    def __init__(self, message: str = "", *, field: str = "") -> None:
        self.field = field
        super().__init__(f"Configuration error{' (field: ' + field + ')' if field else ''}: {message}")


# ---------------------------------------------------------------------------
# Individual policy blocks
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InvestmentObjective:
    """Defines what the portfolio is trying to achieve."""

    primary_objective:    str    = "growth"      # growth | income | preservation | total_return | speculation
    target_return_pct:    float  = 0.0           # annualised target return (0 = unconstrained)
    target_yield_pct:     float  = 0.0           # dividend/income yield target
    benchmark:            str    = ""            # benchmark symbol / index
    tracking_error_max:   float  = 0.0           # max tracking error vs benchmark (0 = unconstrained)
    information_ratio_min:float  = 0.0           # minimum information ratio target
    use_absolute_return:  bool   = False         # True = absolute return mandate

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary_objective":     self.primary_objective,
            "target_return_pct":     self.target_return_pct,
            "target_yield_pct":      self.target_yield_pct,
            "benchmark":             self.benchmark,
            "tracking_error_max":    self.tracking_error_max,
            "information_ratio_min": self.information_ratio_min,
            "use_absolute_return":   self.use_absolute_return,
        }


@dataclass(frozen=True)
class CapitalLimits:
    """Capital boundary constraints."""

    min_capital:           float = 0.0
    max_capital:           float = 1e12
    initial_capital:       float = 0.0
    min_cash_reserve_pct:  float = 0.02   # 2% minimum cash buffer
    max_cash_pct:          float = 0.50   # maximum idle cash
    capital_currency:      str   = "INR"
    allow_leverage:        bool  = False
    max_leverage_ratio:    float = 1.0    # 1.0 = no leverage, 2.0 = 2×

    def validate(self) -> None:
        if self.min_capital < 0:
            raise PortfolioConfigurationError("min_capital must be >= 0", field="min_capital")
        if self.max_capital <= self.min_capital:
            raise PortfolioConfigurationError(
                "max_capital must exceed min_capital", field="max_capital"
            )
        if not (0.0 <= self.min_cash_reserve_pct <= 1.0):
            raise PortfolioConfigurationError(
                "min_cash_reserve_pct must be in [0, 1]", field="min_cash_reserve_pct"
            )
        if not self.allow_leverage and self.max_leverage_ratio > 1.0:
            raise PortfolioConfigurationError(
                "max_leverage_ratio > 1 requires allow_leverage=True",
                field="max_leverage_ratio",
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "min_capital":          self.min_capital,
            "max_capital":          self.max_capital,
            "initial_capital":      self.initial_capital,
            "min_cash_reserve_pct": self.min_cash_reserve_pct,
            "max_cash_pct":         self.max_cash_pct,
            "capital_currency":     self.capital_currency,
            "allow_leverage":       self.allow_leverage,
            "max_leverage_ratio":   self.max_leverage_ratio,
        }


@dataclass(frozen=True)
class AllocationPolicy:
    """Governs how capital is allocated across positions and sectors."""

    max_single_position_pct:  float          = 0.10   # max weight per position
    min_single_position_pct:  float          = 0.001  # min meaningful weight
    max_sector_pct:           float          = 0.30
    max_asset_class_pct:      float          = 0.80
    min_positions:            int            = 3
    max_positions:            int            = 100
    allowed_asset_classes:    FrozenSet[str] = field(default_factory=frozenset)
    restricted_symbols:       FrozenSet[str] = field(default_factory=frozenset)
    allow_short_positions:    bool           = False
    max_short_pct:            float          = 0.0    # max net short weight
    equal_weight:             bool           = False  # force equal-weight policy

    def validate(self) -> None:
        if not (0.0 < self.max_single_position_pct <= 1.0):
            raise PortfolioConfigurationError(
                "max_single_position_pct must be in (0, 1]",
                field="max_single_position_pct",
            )
        if self.min_positions < 1:
            raise PortfolioConfigurationError(
                "min_positions must be >= 1", field="min_positions"
            )
        if self.max_positions < self.min_positions:
            raise PortfolioConfigurationError(
                "max_positions must be >= min_positions", field="max_positions"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_single_position_pct": self.max_single_position_pct,
            "min_single_position_pct": self.min_single_position_pct,
            "max_sector_pct":          self.max_sector_pct,
            "max_asset_class_pct":     self.max_asset_class_pct,
            "min_positions":           self.min_positions,
            "max_positions":           self.max_positions,
            "allow_short_positions":   self.allow_short_positions,
            "max_short_pct":           self.max_short_pct,
            "equal_weight":            self.equal_weight,
        }


@dataclass(frozen=True)
class RiskPolicy:
    """Risk boundaries enforced by the framework."""

    max_drawdown_pct:         float = 0.20   # maximum acceptable drawdown
    max_daily_loss_pct:       float = 0.03
    max_weekly_loss_pct:      float = 0.08
    max_monthly_loss_pct:     float = 0.15
    max_volatility_annual_pct:float = 0.30   # annualised vol ceiling
    min_sharpe_ratio:         float = 0.0    # minimum Sharpe (0 = unconstrained)
    max_beta:                 float = 2.0
    max_var_95_pct:           float = 0.05   # 1-day 95% VaR as % of NAV
    stop_loss_pct:            float = 0.0    # 0 = no auto stop-loss
    risk_on_flag:             bool  = True   # True = risk-on mode (can deploy capital)

    def validate(self) -> None:
        if not (0.0 < self.max_drawdown_pct <= 1.0):
            raise PortfolioConfigurationError(
                "max_drawdown_pct must be in (0, 1]", field="max_drawdown_pct"
            )
        if self.max_daily_loss_pct <= 0.0:
            raise PortfolioConfigurationError(
                "max_daily_loss_pct must be > 0", field="max_daily_loss_pct"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_drawdown_pct":          self.max_drawdown_pct,
            "max_daily_loss_pct":        self.max_daily_loss_pct,
            "max_weekly_loss_pct":       self.max_weekly_loss_pct,
            "max_monthly_loss_pct":      self.max_monthly_loss_pct,
            "max_volatility_annual_pct": self.max_volatility_annual_pct,
            "min_sharpe_ratio":          self.min_sharpe_ratio,
            "max_beta":                  self.max_beta,
            "max_var_95_pct":            self.max_var_95_pct,
            "stop_loss_pct":             self.stop_loss_pct,
            "risk_on_flag":              self.risk_on_flag,
        }


@dataclass(frozen=True)
class RebalancingPolicy:
    """Defines when and how the portfolio should be rebalanced."""

    trigger:              str   = "calendar"   # calendar | drift | signal | manual
    frequency_days:       int   = 30           # for calendar trigger
    drift_threshold_pct:  float = 0.05         # for drift trigger (5% position drift)
    time_of_day:          str   = "09:30"      # HH:MM market-local time
    allow_fractional:     bool  = False
    min_trade_size:       float = 0.0          # minimum lot size in currency
    rebalance_on_signal:  bool  = False        # allow signal-driven rebalance
    cooldown_hours:       float = 24.0         # minimum hours between rebalances

    def to_dict(self) -> dict[str, Any]:
        return {
            "trigger":             self.trigger,
            "frequency_days":      self.frequency_days,
            "drift_threshold_pct": self.drift_threshold_pct,
            "time_of_day":         self.time_of_day,
            "allow_fractional":    self.allow_fractional,
            "min_trade_size":      self.min_trade_size,
            "rebalance_on_signal": self.rebalance_on_signal,
            "cooldown_hours":      self.cooldown_hours,
        }


# ---------------------------------------------------------------------------
# Composite configuration object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PortfolioConfiguration:
    """
    The full, validated configuration for one portfolio.
    Immutable. Changes require creating a new instance.
    """

    portfolio_id:         str                 = ""
    profile_name:         str                 = "custom"
    environment:          str                 = "production"   # production | paper | backtest
    objective:            InvestmentObjective = field(default_factory=InvestmentObjective)
    capital_limits:       CapitalLimits       = field(default_factory=CapitalLimits)
    allocation_policy:    AllocationPolicy    = field(default_factory=AllocationPolicy)
    risk_policy:          RiskPolicy          = field(default_factory=RiskPolicy)
    rebalancing_policy:   RebalancingPolicy   = field(default_factory=RebalancingPolicy)
    extra:                dict[str, Any]      = field(default_factory=dict)

    def validate(self) -> None:
        """Run cross-field validation. Raises PortfolioConfigurationError on failure."""
        self.capital_limits.validate()
        self.allocation_policy.validate()
        self.risk_policy.validate()
        if self.environment not in ("production", "paper", "backtest", "simulation"):
            raise PortfolioConfigurationError(
                f"Unknown environment: {self.environment!r}", field="environment"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_id":       self.portfolio_id,
            "profile_name":       self.profile_name,
            "environment":        self.environment,
            "objective":          self.objective.to_dict(),
            "capital_limits":     self.capital_limits.to_dict(),
            "allocation_policy":  self.allocation_policy.to_dict(),
            "risk_policy":        self.risk_policy.to_dict(),
            "rebalancing_policy": self.rebalancing_policy.to_dict(),
            "extra":              dict(self.extra),
        }
