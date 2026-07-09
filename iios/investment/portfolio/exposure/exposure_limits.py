"""iios/investment/portfolio/exposure/exposure_limits.py"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.investment.portfolio.portfolio_constants import (
    DEFAULT_MAX_ASSET_CLASS_PCT,
    DEFAULT_MAX_COUNTRY_PCT,
    DEFAULT_MAX_SECTOR_PCT,
    DEFAULT_MAX_SINGLE_WEIGHT,
    DEFAULT_MIN_CASH_PCT,
)


@dataclass
class ExposureLimits:
    """
    Configurable exposure limit set for a portfolio or system-wide policy.

    All values are fractions of NAV (e.g. 0.25 = 25%).
    """

    # Position-level
    max_single_position:  float           = DEFAULT_MAX_SINGLE_WEIGHT

    # Group-level
    max_sector_exposure:  float           = DEFAULT_MAX_SECTOR_PCT
    max_country_exposure: float           = DEFAULT_MAX_COUNTRY_PCT
    max_asset_class:      float           = DEFAULT_MAX_ASSET_CLASS_PCT

    # Portfolio-level
    max_gross_exposure:   float           = 1.0      # 100% of NAV
    max_net_exposure:     float           = 1.0
    min_cash_pct:         float           = DEFAULT_MIN_CASH_PCT
    max_cash_pct:         float           = 0.50     # 50% cash = flag

    # Custom per-entity overrides: entity_key → max_weight
    custom_limits:        dict[str, float] = field(default_factory=dict)

    def get_custom(self, key: str) -> float | None:
        return self.custom_limits.get(key)

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_single_position":  self.max_single_position,
            "max_sector_exposure":  self.max_sector_exposure,
            "max_country_exposure": self.max_country_exposure,
            "max_asset_class":      self.max_asset_class,
            "max_gross_exposure":   self.max_gross_exposure,
            "max_net_exposure":     self.max_net_exposure,
            "min_cash_pct":         self.min_cash_pct,
            "max_cash_pct":         self.max_cash_pct,
            "custom_limits":        self.custom_limits,
        }
