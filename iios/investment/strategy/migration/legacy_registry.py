"""iios/investment/strategy/migration/legacy_registry.py
Known legacy strategy definitions — the ground truth for what must be migrated.
"""
from __future__ import annotations

import threading
from typing import Dict, Iterator, List, Optional

from iios.investment.strategy.migration.legacy_metadata import (
    LegacyStrategyMetadata,
    LegacyStrategySource,
    LegacyStrategyType,
    LegacyHealthStatus,
)

# ── Hardcoded catalogue of all known code-based legacy strategies ─────────────
# Sourced from strategy_lab/strategy_generator_ai.py :: STRATEGY_PARAMS
# and strategy_lab/meta_strategy_controller.py :: _REGIME_MAP
_KNOWN_CODE_STRATEGIES: Dict[str, Dict] = {
    "Breakout_Volume": {
        "min_rr": 2.5, "max_loss_pct": 0.02,
        "preferred_regimes": ["bull_trend", "range_market"],
        "category": "breakout",
        "description": "BULL_TREND + volume breakout — targets trend explosions",
        "tags": ["breakout", "volume", "trend"],
    },
    "Momentum_Retest": {
        "min_rr": 2.0, "max_loss_pct": 0.025,
        "preferred_regimes": ["bull_trend", "range_market"],
        "category": "momentum",
        "description": "BULL_TREND + RSI continuation — Nifty-50 intraday momentum",
        "tags": ["momentum", "rsi", "retest", "nifty"],
    },
    "Trend_Pullback": {
        "min_rr": 2.5, "max_loss_pct": 0.02,
        "preferred_regimes": ["bull_trend", "range_market"],
        "category": "trend_following",
        "description": "ATR-based pullback inside trend — primary bull-market setup",
        "tags": ["trend", "pullback", "atr"],
    },
    "Mean_Reversion": {
        "min_rr": 2.0, "max_loss_pct": 0.015,
        "preferred_regimes": ["range_market"],
        "category": "mean_reversion",
        "description": "RANGE_MARKET + RSI extremes — range bounce strategy",
        "tags": ["mean_reversion", "rsi", "range"],
    },
    "Bull_Call_Spread": {
        "min_rr": 2.0, "max_loss_pct": 0.01,
        "preferred_regimes": ["bull_trend"],
        "category": "options",
        "description": "BULL_TREND + options signal — defined-risk bull spread",
        "tags": ["options", "spread", "bull"],
    },
    "Iron_Condor_Range": {
        "min_rr": 1.5, "max_loss_pct": 0.01,
        "preferred_regimes": ["range_market", "bear_market"],
        "category": "options",
        "description": "RANGE_MARKET + low IV — premium income through neutral spread",
        "tags": ["options", "iron_condor", "range", "premium"],
    },
    "Hedging_Model": {
        "min_rr": 1.5, "max_loss_pct": 0.02,
        "preferred_regimes": ["bear_market", "volatile"],
        "category": "hedging",
        "description": "BEAR_MARKET / VOLATILE — downside protection model",
        "tags": ["hedge", "bear", "volatility"],
    },
    "Short_Straddle_IV_Spike": {
        "min_rr": 1.5, "max_loss_pct": 0.015,
        "preferred_regimes": ["volatile", "range_market"],
        "category": "options",
        "description": "Sell premium during IV spike — neutral volatility strategy",
        "tags": ["options", "straddle", "iv", "premium"],
    },
    "Long_Straddle_Pre_Event": {
        "min_rr": 2.5, "max_loss_pct": 0.02,
        "preferred_regimes": ["bull_trend", "volatile"],
        "category": "options",
        "description": "Buy volatility ahead of known events — fat-tail event strategy",
        "tags": ["options", "straddle", "event", "volatility"],
    },
    "Futures_Basis_Arb": {
        "min_rr": 1.2, "max_loss_pct": 0.005,
        "preferred_regimes": ["bull_trend", "range_market", "bear_market"],
        "category": "arbitrage",
        "description": "Futures basis arbitrage — tight spread, market-neutral",
        "tags": ["futures", "arbitrage", "basis"],
    },
    "ETF_NAV_Arb": {
        "min_rr": 1.2, "max_loss_pct": 0.003,
        "preferred_regimes": ["bull_trend", "range_market", "bear_market"],
        "category": "arbitrage",
        "description": "ETF NAV arbitrage — captures premium/discount to NAV",
        "tags": ["etf", "arbitrage", "nav"],
    },
    "Equity_Breakout": {
        "min_rr": 2.5, "max_loss_pct": 0.015,
        "preferred_regimes": ["volatile"],
        "category": "breakout",
        "description": "Equity breakout in volatile regime — strict risk controls",
        "tags": ["equity", "breakout", "volatile"],
    },
    "Equity_Retest": {
        "min_rr": 2.0, "max_loss_pct": 0.015,
        "preferred_regimes": ["volatile"],
        "category": "retest",
        "description": "Equity retest in volatile regime — limited participation",
        "tags": ["equity", "retest", "volatile"],
    },
}


class LegacyStrategyRegistry:
    """
    Thread-safe registry of known legacy strategy definitions.

    Starts with all code-based strategies hardcoded from STRATEGY_PARAMS.
    Additional strategies (JSON-based) are registered at discovery time.
    """

    def __init__(self) -> None:
        self._strategies: Dict[str, LegacyStrategyMetadata] = {}
        self._lock = threading.RLock()
        self._populate_defaults()

    def _populate_defaults(self) -> None:
        """Register all known code-based legacy strategies."""
        for name, params in _KNOWN_CODE_STRATEGIES.items():
            meta = LegacyStrategyMetadata(
                strategy_id=f"legacy_{name}",
                strategy_name=name,
                source=LegacyStrategySource.STRATEGY_GENERATOR,
                strategy_type=LegacyStrategyType.CODE_BASED,
                min_rr=params["min_rr"],
                max_loss_pct=params["max_loss_pct"],
                stop_loss_pct=params["max_loss_pct"],
                target_multiplier=params["min_rr"],
                category=params.get("category", "unknown"),
                preferred_regimes=params.get("preferred_regimes", []),
                compatible_regimes=params.get("preferred_regimes", []),
                description=params.get("description", ""),
                tags=params.get("tags", []),
                health_status=LegacyHealthStatus.ACTIVE,
                is_approved=True,
            )
            self._strategies[name] = meta

    def register(self, meta: LegacyStrategyMetadata) -> None:
        with self._lock:
            self._strategies[meta.strategy_name] = meta

    def get(self, name: str) -> Optional[LegacyStrategyMetadata]:
        with self._lock:
            return self._strategies.get(name)

    def get_by_id(self, strategy_id: str) -> Optional[LegacyStrategyMetadata]:
        with self._lock:
            return next(
                (m for m in self._strategies.values() if m.strategy_id == strategy_id),
                None,
            )

    def all(self) -> List[LegacyStrategyMetadata]:
        with self._lock:
            return list(self._strategies.values())

    def by_source(self, source: LegacyStrategySource) -> List[LegacyStrategyMetadata]:
        with self._lock:
            return [m for m in self._strategies.values() if m.source == source]

    def by_category(self, category: str) -> List[LegacyStrategyMetadata]:
        with self._lock:
            return [m for m in self._strategies.values() if m.category == category]

    def names(self) -> List[str]:
        with self._lock:
            return list(self._strategies.keys())

    def count(self) -> int:
        with self._lock:
            return len(self._strategies)

    def __iter__(self) -> Iterator[LegacyStrategyMetadata]:
        with self._lock:
            return iter(list(self._strategies.values()))
