"""iios/execution/monitoring/metrics/metrics_calculator.py
==================================================
MetricsCalculator — pure, stateless calculation engine.

Provides all numerical operations needed by the Metrics Framework.
No I/O, no state, no side-effects.

C6 Execution Intelligence — Phase 6, Module 3
"""
from __future__ import annotations

import math
import statistics
from typing import List, Optional, Sequence


class MetricsCalculator:
    """
    Pure, stateless calculation engine.

    All methods are classmethods — no instantiation required.
    All methods accept sequences of float and return float.
    """

    # ── Basic aggregations ────────────────────────────────────────────────────

    @classmethod
    def calculate_sum(cls, values: Sequence[float]) -> float:
        if not values:
            return 0.0
        return float(sum(values))

    @classmethod
    def calculate_count(cls, values: Sequence[float]) -> float:
        return float(len(values))

    @classmethod
    def calculate_average(cls, values: Sequence[float]) -> float:
        if not values:
            return 0.0
        return sum(values) / len(values)

    @classmethod
    def calculate_median(cls, values: Sequence[float]) -> float:
        if not values:
            return 0.0
        return statistics.median(values)

    @classmethod
    def calculate_min(cls, values: Sequence[float]) -> float:
        if not values:
            return 0.0
        return float(min(values))

    @classmethod
    def calculate_max(cls, values: Sequence[float]) -> float:
        if not values:
            return 0.0
        return float(max(values))

    @classmethod
    def calculate_std_dev(cls, values: Sequence[float]) -> float:
        if len(values) < 2:
            return 0.0
        return statistics.pstdev(values)

    # ── Percentile ────────────────────────────────────────────────────────────

    @classmethod
    def calculate_percentile(
        cls, values: Sequence[float], percentile: float
    ) -> float:
        """
        Compute ``percentile`` of ``values`` using linear interpolation.

        ``percentile`` is in the range [0, 100].
        Returns 0.0 for empty input.
        """
        if not values:
            return 0.0
        if not (0.0 <= percentile <= 100.0):
            raise ValueError(
                f"percentile must be in [0, 100], got {percentile}."
            )
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        if n == 1:
            return float(sorted_vals[0])
        # Linear interpolation
        index = (percentile / 100.0) * (n - 1)
        lower = int(index)
        upper = lower + 1
        if upper >= n:
            return float(sorted_vals[-1])
        frac = index - lower
        return sorted_vals[lower] + frac * (sorted_vals[upper] - sorted_vals[lower])

    @classmethod
    def calculate_p95(cls, values: Sequence[float]) -> float:
        return cls.calculate_percentile(values, 95.0)

    @classmethod
    def calculate_p99(cls, values: Sequence[float]) -> float:
        return cls.calculate_percentile(values, 99.0)

    # ── Rate calculations ─────────────────────────────────────────────────────

    @classmethod
    def calculate_rate(cls, numerator: float, denominator: float) -> float:
        """
        Compute numerator / denominator.  Returns 0.0 when denominator is 0.
        Clamps result to [0.0, 1.0] for standard rate metrics.
        """
        if denominator == 0:
            return 0.0
        rate = numerator / denominator
        return max(0.0, min(1.0, rate))

    @classmethod
    def calculate_throughput(
        cls, count: float, window_seconds: float
    ) -> float:
        """
        Compute events per second.  Returns 0.0 when window is zero or negative.
        """
        if window_seconds <= 0:
            return 0.0
        return count / window_seconds

    # ── Trend / rolling ───────────────────────────────────────────────────────

    @classmethod
    def calculate_rolling_average(
        cls, values: Sequence[float], window: int
    ) -> List[float]:
        """
        Compute rolling (moving) average over ``window`` samples.

        Returns a list of the same length as ``values``.  Leading items
        where ``window`` has not yet been filled use the partial average.
        """
        if not values:
            return []
        result: List[float] = []
        for i, _ in enumerate(values):
            start  = max(0, i - window + 1)
            chunk  = values[start : i + 1]
            result.append(sum(chunk) / len(chunk))
        return result

    @classmethod
    def calculate_change_rate(
        cls,
        current: float,
        previous: float,
    ) -> float:
        """
        Compute percentage change from ``previous`` to ``current``.
        Returns 0.0 when previous is 0.
        """
        if previous == 0:
            return 0.0
        return (current - previous) / abs(previous)

    # ── Composite metrics ─────────────────────────────────────────────────────

    @classmethod
    def compute_success_rate(
        cls, successes: int, total: int
    ) -> float:
        return cls.calculate_rate(float(successes), float(total))

    @classmethod
    def compute_failure_rate(
        cls, failures: int, total: int
    ) -> float:
        return cls.calculate_rate(float(failures), float(total))

    @classmethod
    def compute_retry_rate(
        cls, retries: int, total: int
    ) -> float:
        return cls.calculate_rate(float(retries), float(total))

    @classmethod
    def compute_timeout_rate(
        cls, timeouts: int, total: int
    ) -> float:
        return cls.calculate_rate(float(timeouts), float(total))

    @classmethod
    def compute_cancellation_rate(
        cls, cancellations: int, total: int
    ) -> float:
        return cls.calculate_rate(float(cancellations), float(total))
