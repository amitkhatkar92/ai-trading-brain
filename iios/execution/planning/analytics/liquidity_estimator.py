"""iios/execution/planning/analytics/liquidity_estimator.py
Estimates execution liquidity score and related metrics.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.execution.planning.planning_constants import LiquidityLevel


@dataclass
class LiquidityEstimatorConfig:
    # Participation-rate thresholds that define liquidity tiers
    high_threshold:    float = 0.05    # < 5% of daily vol → high liquidity
    medium_threshold:  float = 0.15    # 5–15% → medium
    low_threshold:     float = 0.30    # 15–30% → low; > 30% → very_low
    default_daily_vol: float = 1_000_000.0   # fallback when no volume provided
    metadata:          dict  = field(default_factory=dict)


@dataclass
class LiquidityEstimate:
    order_id:           str           = ""
    order_value:        float         = 0.0
    estimated_adv:      float         = 0.0    # estimated average daily volume
    participation_rate: float         = 0.0    # order_value / adv
    liquidity_score:    float         = 50.0   # 0–100; higher = more liquid
    liquidity_level:    LiquidityLevel = LiquidityLevel.UNKNOWN
    fill_probability:   float         = 0.5    # 0–1
    expected_fill_sec:  float         = 0.0    # estimated seconds to fill
    metadata:           dict          = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "order_id":           self.order_id,
            "order_value":        self.order_value,
            "estimated_adv":      self.estimated_adv,
            "participation_rate": self.participation_rate,
            "liquidity_score":    self.liquidity_score,
            "liquidity_level":    self.liquidity_level.value,
            "fill_probability":   self.fill_probability,
            "expected_fill_sec":  self.expected_fill_sec,
            "metadata":           self.metadata,
        }


class LiquidityEstimator:
    """
    Scores execution liquidity based on participation-rate relative to
    estimated average daily volume (ADV).

    When no market data is available, falls back to config defaults.
    """

    def __init__(self, config: LiquidityEstimatorConfig | None = None) -> None:
        self._cfg = config or LiquidityEstimatorConfig()

    def estimate(
        self,
        order_value:  float,
        adv:          float | None = None,
        order_id:     str          = "",
    ) -> LiquidityEstimate:
        effective_adv = adv if (adv and adv > 0) else self._cfg.default_daily_vol
        part_rate     = order_value / effective_adv if effective_adv > 0 else 1.0

        level  = self._classify(part_rate)
        score  = self._score(part_rate)
        fill_p = self._fill_probability(part_rate)

        # Rough fill-time: higher participation → longer fill (linear proxy)
        fill_sec = min(part_rate * 6_000, 21_600.0)  # cap at 6 hours

        return LiquidityEstimate(
            order_id           = order_id,
            order_value        = order_value,
            estimated_adv      = effective_adv,
            participation_rate = round(part_rate, 6),
            liquidity_score    = round(score, 2),
            liquidity_level    = level,
            fill_probability   = round(fill_p, 4),
            expected_fill_sec  = round(fill_sec, 1),
        )

    def _classify(self, part_rate: float) -> LiquidityLevel:
        if part_rate < self._cfg.high_threshold:
            return LiquidityLevel.HIGH
        elif part_rate < self._cfg.medium_threshold:
            return LiquidityLevel.MEDIUM
        elif part_rate < self._cfg.low_threshold:
            return LiquidityLevel.LOW
        else:
            return LiquidityLevel.VERY_LOW

    @staticmethod
    def _score(part_rate: float) -> float:
        """0 = very illiquid, 100 = very liquid."""
        return max(0.0, min(100.0, (1.0 - part_rate / 0.30) * 100.0))

    @staticmethod
    def _fill_probability(part_rate: float) -> float:
        if part_rate < 0.05:
            return 0.98
        elif part_rate < 0.15:
            return 0.90
        elif part_rate < 0.30:
            return 0.75
        else:
            return 0.55

    def to_dict(self) -> dict[str, Any]:
        return {
            "high_threshold":    self._cfg.high_threshold,
            "medium_threshold":  self._cfg.medium_threshold,
            "low_threshold":     self._cfg.low_threshold,
            "default_daily_vol": self._cfg.default_daily_vol,
        }
