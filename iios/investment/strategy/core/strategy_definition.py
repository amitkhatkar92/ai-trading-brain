"""iios/investment/strategy/core/strategy_definition.py
Immutable strategy specification — the authoritative description of what a strategy is.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.investment.strategy.strategy_constants import (
    AssetClass,
    MarketRegime,
    StrategyCategory,
    StrategyRiskLevel,
    StrategyStatus,
    StrategyTimeframe,
    MIN_TRADES_FOR_EVAL,
)


@dataclass
class StrategyDefinition:
    """
    Immutable (post-registration) specification of a strategy.

    Describes what the strategy is, how it works, what data it needs,
    and what market conditions it targets.
    """

    strategy_id:          str                  = field(default_factory=lambda: str(uuid.uuid4()))
    name:                 str                  = ""
    version:              str                  = "1.0.0"
    category:             StrategyCategory     = StrategyCategory.UNKNOWN
    asset_class:          AssetClass           = AssetClass.UNKNOWN
    timeframe:            StrategyTimeframe    = StrategyTimeframe.UNKNOWN
    risk_level:           StrategyRiskLevel    = StrategyRiskLevel.UNKNOWN
    initial_status:       StrategyStatus       = StrategyStatus.DRAFT

    # Market conditions the strategy is designed for
    preferred_regimes:    list[MarketRegime]   = field(default_factory=list)

    # Expected holding period range (days)
    min_holding_days:     int                  = 1
    max_holding_days:     int                  = 30

    # Data requirements
    required_data:        list[str]            = field(default_factory=list)
    required_indicators:  list[str]            = field(default_factory=list)

    # Evaluation
    min_trades_required:  int                  = MIN_TRADES_FOR_EVAL

    # Descriptive
    description:          str                  = ""
    author:               str                  = ""
    tags:                 list[str]            = field(default_factory=list)

    # Strategy-specific parameters (free-form)
    parameters:           dict[str, Any]       = field(default_factory=dict)

    # Constraints (e.g. max_position_size, universe_filter)
    constraints:          dict[str, Any]       = field(default_factory=dict)

    created_at:           float                = field(default_factory=time.time)

    def is_compatible_with_regime(self, regime: MarketRegime | str) -> bool:
        """Returns True if the strategy declares compatibility with the given regime."""
        if not self.preferred_regimes:
            return True   # no preference = universal
        regime_val = regime.value if isinstance(regime, MarketRegime) else regime
        return any(r.value == regime_val for r in self.preferred_regimes)

    def holding_period_label(self) -> str:
        avg = (self.min_holding_days + self.max_holding_days) / 2
        if avg < 1:
            return "scalp"
        elif avg <= 5:
            return "short"
        elif avg <= 20:
            return "swing"
        elif avg <= 90:
            return "positional"
        else:
            return "long_term"

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id":         self.strategy_id,
            "name":                self.name,
            "version":             self.version,
            "category":            self.category.value,
            "asset_class":         self.asset_class.value,
            "timeframe":           self.timeframe.value,
            "risk_level":          self.risk_level.value,
            "initial_status":      self.initial_status.value,
            "preferred_regimes":   [r.value for r in self.preferred_regimes],
            "min_holding_days":    self.min_holding_days,
            "max_holding_days":    self.max_holding_days,
            "required_data":       self.required_data,
            "required_indicators": self.required_indicators,
            "min_trades_required": self.min_trades_required,
            "description":         self.description,
            "author":              self.author,
            "tags":                self.tags,
            "parameters":          self.parameters,
            "constraints":         self.constraints,
            "created_at":          self.created_at,
        }
