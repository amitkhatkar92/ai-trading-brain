"""core/backtest_configuration.py — Immutable run-time parameters for a backtest."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.backtesting.backtest_constants import (
    DEFAULT_COMMISSION_FIXED,
    DEFAULT_COMMISSION_PCT,
    DEFAULT_INITIAL_CAPITAL,
    DEFAULT_MIN_BARS_REQUIRED,
    DEFAULT_RISK_FREE_RATE,
    DEFAULT_SLIPPAGE_PCT,
    ExecutionModel,
)


@dataclass
class BacktestConfiguration:
    """
    All parameters that govern how a single backtest is executed.

    Pass an instance to BacktestManager.submit() together with the strategy
    and bars data.  Once submitted the configuration must not be mutated.
    """

    # ── Data ─────────────────────────────────────────────────────────────────
    symbols:          list[str]          = field(default_factory=list)
    start_timestamp:  float              = 0.0    # unix timestamp; 0 = no filter
    end_timestamp:    float              = 0.0    # unix timestamp; 0 = no filter
    interval:         str                = "1d"

    # ── Capital ───────────────────────────────────────────────────────────────
    initial_capital:  float              = DEFAULT_INITIAL_CAPITAL

    # ── Costs ─────────────────────────────────────────────────────────────────
    commission_pct:   float              = DEFAULT_COMMISSION_PCT
    commission_fixed: float              = DEFAULT_COMMISSION_FIXED
    slippage_pct:     float              = DEFAULT_SLIPPAGE_PCT

    # ── Execution ─────────────────────────────────────────────────────────────
    execution_model:  ExecutionModel     = ExecutionModel.NEXT_OPEN
    min_bars:         int                = DEFAULT_MIN_BARS_REQUIRED

    # ── Benchmark ─────────────────────────────────────────────────────────────
    benchmark_symbol: Optional[str]      = None

    # ── Analytics ─────────────────────────────────────────────────────────────
    risk_free_rate:   float              = DEFAULT_RISK_FREE_RATE  # annualised

    # ── Corporate actions ─────────────────────────────────────────────────────
    adjust_dividends: bool               = True
    adjust_splits:    bool               = True

    # ── Misc ──────────────────────────────────────────────────────────────────
    tags:             list[str]          = field(default_factory=list)
    extra:            dict[str, Any]     = field(default_factory=dict)
    created_at:       float              = field(default_factory=time.time)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def validate(self) -> list[str]:
        """Return list of validation error messages (empty = valid)."""
        errors: list[str] = []
        if self.initial_capital <= 0:
            errors.append("initial_capital must be positive")
        if self.commission_pct < 0:
            errors.append("commission_pct must be >= 0")
        if self.slippage_pct < 0:
            errors.append("slippage_pct must be >= 0")
        if self.min_bars < 1:
            errors.append("min_bars must be >= 1")
        if self.start_timestamp < 0:
            errors.append("start_timestamp must be >= 0")
        if self.end_timestamp < 0:
            errors.append("end_timestamp must be >= 0")
        if (self.start_timestamp > 0 and self.end_timestamp > 0
                and self.start_timestamp >= self.end_timestamp):
            errors.append("start_timestamp must be < end_timestamp")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbols":          list(self.symbols),
            "start_timestamp":  self.start_timestamp,
            "end_timestamp":    self.end_timestamp,
            "interval":         self.interval,
            "initial_capital":  self.initial_capital,
            "commission_pct":   self.commission_pct,
            "commission_fixed": self.commission_fixed,
            "slippage_pct":     self.slippage_pct,
            "execution_model":  self.execution_model.value,
            "min_bars":         self.min_bars,
            "benchmark_symbol": self.benchmark_symbol,
            "risk_free_rate":   self.risk_free_rate,
            "adjust_dividends": self.adjust_dividends,
            "adjust_splits":    self.adjust_splits,
            "tags":             list(self.tags),
            "extra":            dict(self.extra),
            "created_at":       self.created_at,
        }
