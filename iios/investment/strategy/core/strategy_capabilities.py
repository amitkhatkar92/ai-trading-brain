"""iios/investment/strategy/core/strategy_capabilities.py
Strategy capability declarations — what an institutional strategy can do.
"""
from __future__ import annotations

from enum import Enum
from typing import FrozenSet


class StrategyCapability(str, Enum):
    """Coarse-grained capability flags for strategy discovery and filtering."""
    LONG_ONLY           = "long_only"
    SHORT_ALLOWED       = "short_allowed"
    HEDGING             = "hedging"
    PORTFOLIO           = "portfolio"
    SINGLE_ASSET        = "single_asset"
    MULTI_ASSET         = "multi_asset"
    SECTOR_ROTATION     = "sector_rotation"
    PAIRS_TRADING       = "pairs_trading"
    OPTIONS_WRITING     = "options_writing"
    OPTIONS_BUYING      = "options_buying"
    LEVERAGE            = "leverage"
    DERIVATIVES         = "derivatives"
    REAL_TIME           = "real_time"
    END_OF_DAY          = "end_of_day"
    BACKTESTABLE        = "backtestable"
    LIVE_TRADABLE       = "live_tradable"
    PAPER_TRADABLE      = "paper_tradable"
    REQUIRES_TICK       = "requires_tick"
    REQUIRES_CANDLE     = "requires_candle"
    REQUIRES_ORDERBOOK  = "requires_orderbook"
    AI_ENHANCED         = "ai_enhanced"
    RULE_BASED          = "rule_based"
    ML_SIGNAL           = "ml_signal"


EXECUTION_CAPABILITIES: FrozenSet[StrategyCapability] = frozenset({
    StrategyCapability.LIVE_TRADABLE,
    StrategyCapability.PAPER_TRADABLE,
})

DATA_CAPABILITIES: FrozenSet[StrategyCapability] = frozenset({
    StrategyCapability.REQUIRES_TICK,
    StrategyCapability.REQUIRES_CANDLE,
    StrategyCapability.REQUIRES_ORDERBOOK,
})
