"""validation/out_of_sample_validator.py — Simple IS/OOS split validation."""
from __future__ import annotations

from typing import Any

from iios.integration.research.backtesting.backtest_constants import DEFAULT_OOS_SPLIT_RATIO
from iios.integration.research.backtesting.backtest_exceptions import BacktestValidationFrameworkError


class OOSSplit:
    """Result of an IS/OOS data split."""

    def __init__(
        self,
        is_timestamps:  list[float],
        oos_timestamps: list[float],
        split_ratio:    float,
    ) -> None:
        self.is_timestamps  = is_timestamps
        self.oos_timestamps = oos_timestamps
        self.split_ratio    = split_ratio

    @property
    def is_size(self) -> int:
        return len(self.is_timestamps)

    @property
    def oos_size(self) -> int:
        return len(self.oos_timestamps)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_size":      self.is_size,
            "oos_size":     self.oos_size,
            "split_ratio":  self.split_ratio,
            "is_start":     self.is_timestamps[0]  if self.is_timestamps  else None,
            "is_end":       self.is_timestamps[-1] if self.is_timestamps  else None,
            "oos_start":    self.oos_timestamps[0]  if self.oos_timestamps else None,
            "oos_end":      self.oos_timestamps[-1] if self.oos_timestamps else None,
        }


class OutOfSampleValidator:
    """
    Splits a timestamp series into in-sample and out-of-sample portions.

    Typically used to:
        1. Run a backtest on IS data (fitting / configuration phase)
        2. Run the same strategy unchanged on OOS data (validation phase)
        3. Compare IS vs OOS performance to detect overfitting
    """

    def split(
        self,
        timestamps:    list[float],
        oos_fraction:  float = DEFAULT_OOS_SPLIT_RATIO,
    ) -> OOSSplit:
        """
        Chronological split: first (1 - oos_fraction) = IS, remainder = OOS.
        """
        if not timestamps:
            raise BacktestValidationFrameworkError("timestamps list is empty")
        if not (0.0 < oos_fraction < 1.0):
            raise BacktestValidationFrameworkError(
                "oos_fraction must be between 0 and 1 (exclusive)"
            )
        n        = len(timestamps)
        is_count = max(1, int(n * (1.0 - oos_fraction)))
        return OOSSplit(
            is_timestamps  = timestamps[:is_count],
            oos_timestamps = timestamps[is_count:],
            split_ratio    = oos_fraction,
        )

    def compare_metrics(
        self,
        is_metrics:  dict[str, Any],
        oos_metrics: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Compare IS vs OOS for key metrics.

        Returns dict of metric → {"is": ..., "oos": ..., "degradation_pct": ...}.
        """
        KEYS = ("sharpe_ratio", "total_return_pct", "win_rate", "max_drawdown_pct")
        result: dict[str, Any] = {}
        for k in KEYS:
            is_val  = is_metrics.get(k)
            oos_val = oos_metrics.get(k)
            if is_val is not None and oos_val is not None and is_val != 0:
                degradation = (is_val - oos_val) / abs(is_val)
            else:
                degradation = None
            result[k] = {
                "is":              is_val,
                "oos":             oos_val,
                "degradation_pct": degradation,
            }
        return result
