"""iios/investment/market/models/market_health.py"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _label(score: float, invert: bool = False) -> str:
    s = (100.0 - score) if invert else score
    if s >= 70:
        return "GOOD"
    if s >= 40:
        return "FAIR"
    return "POOR"


@dataclass
class MarketHealth:
    """
    Composite health assessment of a market.
    All scores 0–100. Higher is healthier.
    Volatility score: higher vol = lower health (inverted in label).
    """

    overall_score:    float = 50.0
    volatility_score: float = 50.0   # raw vol score; invert for health label
    liquidity_score:  float = 50.0
    breadth_score:    float = 50.0
    trend_score:      float = 50.0
    sentiment_score:  float = 50.0
    labels:           dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.labels:
            self.labels = {
                "overall":    _label(self.overall_score),
                "volatility": _label(self.volatility_score, invert=True),
                "liquidity":  _label(self.liquidity_score),
                "breadth":    _label(self.breadth_score),
                "trend":      _label(self.trend_score),
                "sentiment":  _label(self.sentiment_score),
            }

    @property
    def is_healthy(self) -> bool:
        return self.overall_score >= 60.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_score":    self.overall_score,
            "volatility_score": self.volatility_score,
            "liquidity_score":  self.liquidity_score,
            "breadth_score":    self.breadth_score,
            "trend_score":      self.trend_score,
            "sentiment_score":  self.sentiment_score,
            "labels":           self.labels,
            "is_healthy":       self.is_healthy,
        }
