"""iios/investment/portfolio/core/investment_style.py

Investment style taxonomy for the Institutional Portfolio Framework.
Styles govern how a portfolio approaches security selection, sizing,
and rotation — not the allocation algorithm itself.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet, Optional


class InvestmentStyle(str, Enum):
    """Primary investment style classification."""

    VALUE          = "value"
    GROWTH         = "growth"
    BLEND          = "blend"
    MOMENTUM       = "momentum"
    QUALITY        = "quality"
    INCOME         = "income"
    INDEX          = "index"
    QUANTITATIVE   = "quantitative"
    MACRO          = "macro"
    ARBITRAGE      = "arbitrage"
    VOLATILITY     = "volatility"
    MULTI_STRATEGY = "multi_strategy"
    TACTICAL       = "tactical"
    THEMATIC       = "thematic"
    UNKNOWN        = "unknown"

    @property
    def is_active(self) -> bool:
        """True for styles that require active management."""
        passive = {InvestmentStyle.INDEX}
        return self not in passive

    @property
    def typical_turnover_annual_pct(self) -> float:
        """Rough annual turnover percentage for indicative use."""
        _map = {
            "value": 25.0, "growth": 40.0, "blend": 30.0,
            "momentum": 150.0, "quality": 30.0, "income": 20.0,
            "index": 5.0, "quantitative": 200.0, "macro": 80.0,
            "arbitrage": 400.0, "volatility": 300.0,
            "multi_strategy": 100.0, "tactical": 120.0, "thematic": 35.0,
            "unknown": 50.0,
        }
        return _map.get(self.value, 50.0)


class InvestmentHorizon(str, Enum):
    """Time-horizon of the investment approach."""

    INTRADAY      = "intraday"     # < 1 day
    SHORT_TERM    = "short_term"   # 1 day – 3 months
    MEDIUM_TERM   = "medium_term"  # 3 months – 1 year
    LONG_TERM     = "long_term"    # 1 year – 5 years
    VERY_LONG     = "very_long"    # > 5 years
    PERPETUAL     = "perpetual"    # Evergreen / no fixed end

    @property
    def min_holding_days(self) -> int:
        _map = {
            "intraday": 0, "short_term": 1, "medium_term": 90,
            "long_term": 365, "very_long": 1825, "perpetual": 0,
        }
        return _map.get(self.value, 0)

    @property
    def max_holding_days(self) -> Optional[int]:
        _map: dict[str, Optional[int]] = {
            "intraday": 1, "short_term": 90, "medium_term": 365,
            "long_term": 1825, "very_long": None, "perpetual": None,
        }
        return _map.get(self.value)


class ConcentrationBias(str, Enum):
    """Concentration preference of the portfolio style."""

    CONCENTRATED  = "concentrated"   # < 15 positions
    FOCUSED       = "focused"        # 15 – 30 positions
    DIVERSIFIED   = "diversified"    # 30 – 60 positions
    BROAD         = "broad"          # 60 – 150 positions
    INDEX_LIKE    = "index_like"     # 150+ positions


@dataclass(frozen=True)
class StyleConstraints:
    """Non-binding guidance constraints derived from an investment style."""

    style:               InvestmentStyle
    horizon:             InvestmentHorizon
    concentration:       ConcentrationBias
    max_single_weight:   float              = 0.10
    min_single_weight:   float              = 0.001
    max_sector_weight:   float              = 0.30
    min_positions:       int                = 5
    max_positions:       int                = 100
    leverage_allowed:    bool               = False
    short_allowed:       bool               = False
    derivatives_allowed: bool               = False

    def to_dict(self) -> dict:
        return {
            "style":               self.style.value,
            "horizon":             self.horizon.value,
            "concentration":       self.concentration.value,
            "max_single_weight":   self.max_single_weight,
            "min_single_weight":   self.min_single_weight,
            "max_sector_weight":   self.max_sector_weight,
            "min_positions":       self.min_positions,
            "max_positions":       self.max_positions,
            "leverage_allowed":    self.leverage_allowed,
            "short_allowed":       self.short_allowed,
            "derivatives_allowed": self.derivatives_allowed,
        }


@dataclass(frozen=True)
class InvestmentStyleProfile:
    """Complete style profile attached to a portfolio."""

    primary_style:    InvestmentStyle
    secondary_styles: FrozenSet[InvestmentStyle] = field(default_factory=frozenset)
    horizon:          InvestmentHorizon           = InvestmentHorizon.MEDIUM_TERM
    constraints:      StyleConstraints            = field(
        default_factory=lambda: StyleConstraints(
            style         = InvestmentStyle.BLEND,
            horizon       = InvestmentHorizon.MEDIUM_TERM,
            concentration = ConcentrationBias.DIVERSIFIED,
        )
    )
    description:      str = ""

    def to_dict(self) -> dict:
        return {
            "primary_style":    self.primary_style.value,
            "secondary_styles": [s.value for s in sorted(self.secondary_styles,
                                                          key=lambda x: x.value)],
            "horizon":          self.horizon.value,
            "constraints":      self.constraints.to_dict(),
            "description":      self.description,
        }


# ---------------------------------------------------------------------------
# Style registry — singleton
# ---------------------------------------------------------------------------

_DEFAULT_PROFILES: dict[InvestmentStyle, InvestmentStyleProfile] = {
    InvestmentStyle.VALUE: InvestmentStyleProfile(
        primary_style = InvestmentStyle.VALUE,
        horizon       = InvestmentHorizon.LONG_TERM,
        constraints   = StyleConstraints(
            style               = InvestmentStyle.VALUE,
            horizon             = InvestmentHorizon.LONG_TERM,
            concentration       = ConcentrationBias.FOCUSED,
            max_single_weight   = 0.15,
            max_sector_weight   = 0.35,
            min_positions       = 10,
            max_positions       = 40,
        ),
        description = "Classic value investing — buy below intrinsic value, hold long term.",
    ),
    InvestmentStyle.GROWTH: InvestmentStyleProfile(
        primary_style = InvestmentStyle.GROWTH,
        horizon       = InvestmentHorizon.LONG_TERM,
        constraints   = StyleConstraints(
            style             = InvestmentStyle.GROWTH,
            horizon           = InvestmentHorizon.LONG_TERM,
            concentration     = ConcentrationBias.FOCUSED,
            max_single_weight = 0.20,
            max_sector_weight = 0.40,
            min_positions     = 8,
            max_positions     = 30,
        ),
        description = "High-growth company focus with elevated concentration tolerance.",
    ),
    InvestmentStyle.MOMENTUM: InvestmentStyleProfile(
        primary_style = InvestmentStyle.MOMENTUM,
        horizon       = InvestmentHorizon.SHORT_TERM,
        constraints   = StyleConstraints(
            style               = InvestmentStyle.MOMENTUM,
            horizon             = InvestmentHorizon.SHORT_TERM,
            concentration       = ConcentrationBias.DIVERSIFIED,
            max_single_weight   = 0.10,
            max_sector_weight   = 0.30,
            min_positions       = 15,
            max_positions       = 60,
            derivatives_allowed = True,
        ),
        description = "Systematic trend-following with high turnover.",
    ),
    InvestmentStyle.INDEX: InvestmentStyleProfile(
        primary_style = InvestmentStyle.INDEX,
        horizon       = InvestmentHorizon.PERPETUAL,
        constraints   = StyleConstraints(
            style             = InvestmentStyle.INDEX,
            horizon           = InvestmentHorizon.PERPETUAL,
            concentration     = ConcentrationBias.BROAD,
            max_single_weight = 0.05,
            max_sector_weight = 0.25,
            min_positions     = 30,
            max_positions     = 500,
        ),
        description = "Passive index replication.",
    ),
}


class StyleRegistry:
    """Thread-safe registry for investment style profiles."""

    def __init__(self) -> None:
        self._lock    = threading.RLock()
        self._profiles: dict[InvestmentStyle, InvestmentStyleProfile] = dict(_DEFAULT_PROFILES)

    def register(self, profile: InvestmentStyleProfile, *, overwrite: bool = False) -> None:
        with self._lock:
            if profile.primary_style in self._profiles and not overwrite:
                raise ValueError(
                    f"Style profile already registered: {profile.primary_style.value!r}"
                )
            self._profiles[profile.primary_style] = profile

    def get(self, style: InvestmentStyle) -> Optional[InvestmentStyleProfile]:
        with self._lock:
            return self._profiles.get(style)

    def all_styles(self) -> list[InvestmentStyle]:
        with self._lock:
            return list(self._profiles.keys())

    def constraints_for(self, style: InvestmentStyle) -> Optional[StyleConstraints]:
        profile = self.get(style)
        return profile.constraints if profile else None


STYLE_REGISTRY = StyleRegistry()
