"""iios/investment/strategy/migration/strategy_adapter.py
Strategy Adapter — wraps a legacy strategy and exposes IIOS-compatible interfaces.
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from iios.investment.strategy.migration.legacy_metadata import (
    LegacyStrategyMetadata,
    LegacyStrategySource,
    LegacyStrategyType,
)
from iios.investment.strategy.strategy_constants import (
    AssetClass,
    StrategyCategory,
    StrategyRiskLevel,
    StrategyStatus,
    StrategyTimeframe,
)
from iios.investment.strategy.core.strategy_definition import StrategyDefinition
from iios.investment.strategy.core.base_strategy import BaseStrategy


class AdaptationMode(str, Enum):
    """How the adapter bridges the legacy strategy to IIOS."""
    FULL_WRAP        = "full_wrap"         # complete wrapping; no legacy code changes
    PARAMETER_BRIDGE = "parameter_bridge"  # parameters are translated, no logic change
    BEHAVIOR_DELEGATE = "behavior_delegate" # adapter delegates to legacy at runtime
    CUSTOM           = "custom"            # custom adapter for non-standard strategies


_CATEGORY_MAP: Dict[str, StrategyCategory] = {
    "breakout":      StrategyCategory.BREAKOUT,
    "momentum":      StrategyCategory.MOMENTUM,
    "mean_reversion": StrategyCategory.MEAN_REVERSION,
    "retest":        StrategyCategory.RETEST,
    "options":       StrategyCategory.OPTIONS,
    "volatility":    StrategyCategory.VOLATILITY,
    "arbitrage":     StrategyCategory.MARKET_NEUTRAL,
    "hedging":       StrategyCategory.MULTI_FACTOR,
    "trend_following": StrategyCategory.TREND_FOLLOWING,
    "macro":         StrategyCategory.MACRO,
    "composite":     StrategyCategory.MULTI_FACTOR,
    "evolved":       StrategyCategory.CUSTOM,
}


def _map_category(category: str) -> StrategyCategory:
    return _CATEGORY_MAP.get(category.lower(), StrategyCategory.UNKNOWN)


def _map_risk_level(max_loss_pct: float) -> StrategyRiskLevel:
    if max_loss_pct <= 0.005: return StrategyRiskLevel.VERY_LOW
    if max_loss_pct <= 0.01:  return StrategyRiskLevel.LOW
    if max_loss_pct <= 0.02:  return StrategyRiskLevel.MODERATE
    if max_loss_pct <= 0.03:  return StrategyRiskLevel.HIGH
    return StrategyRiskLevel.VERY_HIGH


class LegacyStrategyAdapter(BaseStrategy):
    """
    Wraps a LegacyStrategyMetadata as a fully IIOS-compatible BaseStrategy.

    The original strategy logic is NEVER rewritten.
    All parameters and configurations are preserved exactly.
    This class only translates between legacy and IIOS conventions.
    """

    CATEGORY:    StrategyCategory  = StrategyCategory.CUSTOM
    ASSET_CLASS: AssetClass        = AssetClass.EQUITY
    TIMEFRAME:   StrategyTimeframe = StrategyTimeframe.INTRADAY

    def __init__(
        self,
        metadata:         LegacyStrategyMetadata,
        adaptation_mode:  AdaptationMode = AdaptationMode.PARAMETER_BRIDGE,
        strategy_id:      Optional[str]  = None,
    ) -> None:
        super().__init__(
            strategy_id=strategy_id or metadata.strategy_id,
            **metadata.raw_definition,  # preserve all original params
        )
        self._metadata   = metadata
        self._mode       = adaptation_mode
        self._definition = self._build_definition()
        self._status     = self._derive_status()
        self._created_at = datetime.now(timezone.utc)

    # ── BaseStrategy abstract implementation ──────────────────────────────────

    def get_definition(self) -> StrategyDefinition:
        return self._definition

    def get_params(self) -> Dict[str, Any]:
        """Return the legacy strategy parameters in IIOS format."""
        return self.get_risk_params()

    @property
    def name(self) -> str:
        return self._metadata.strategy_name

    @property
    def category(self) -> StrategyCategory:
        return _map_category(self._metadata.category)

    # ── Adapter-specific interface ────────────────────────────────────────────

    @property
    def metadata(self) -> LegacyStrategyMetadata:
        return self._metadata

    @property
    def adaptation_mode(self) -> AdaptationMode:
        return self._mode

    @property
    def is_legacy(self) -> bool:
        return True

    @property
    def has_entry_conditions(self) -> bool:
        return bool(self._metadata.entry_conditions)

    def evaluate_entry(self, features: Dict[str, float]) -> Optional[bool]:
        """Evaluate legacy entry conditions against feature values."""
        return self._metadata.evaluate_entry_conditions(features)

    def get_risk_params(self) -> Dict[str, float]:
        """Return the original legacy risk parameters."""
        return {
            "min_rr":           self._metadata.min_rr,
            "max_loss_pct":     self._metadata.max_loss_pct,
            "stop_loss_pct":    self._metadata.stop_loss_pct,
            "target_multiplier": self._metadata.target_multiplier,
        }

    def get_performance_snapshot(self) -> Dict[str, Any]:
        """Return any known performance metrics from the legacy definition."""
        return {
            "precision":       self._metadata.precision,
            "support":         self._metadata.support,
            "sharpe_ratio":    self._metadata.sharpe_ratio,
            "oos_win_rate":    self._metadata.oos_win_rate,
            "avg_return_r":    self._metadata.avg_return_r,
            "max_drawdown":    self._metadata.max_drawdown,
            "composite_score": self._metadata.composite_score,
            "expectancy_r":    self._metadata.expectancy_r,
            "live_trades":     self._metadata.live_trades,
            "live_wins":       self._metadata.live_wins,
        }

    def summary(self) -> Dict[str, Any]:
        return {
            "strategy_id":      self._strategy_id,
            "strategy_name":    self._metadata.strategy_name,
            "category":         self.category.value,
            "source":           self._metadata.source.value,
            "adaptation_mode":  self._mode.value,
            "is_approved":      self._metadata.is_approved,
            "status":           self._status.value,
            "risk_params":      self.get_risk_params(),
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    def _build_definition(self) -> StrategyDefinition:
        from iios.investment.strategy.strategy_constants import MarketRegime

        preferred: List[MarketRegime] = []
        _regime_map = {
            "bull_trend":    MarketRegime.BULL,
            "bull":          MarketRegime.BULL,
            "range_market":  MarketRegime.SIDEWAYS,
            "ranging":       MarketRegime.SIDEWAYS,
            "bear_market":   MarketRegime.BEAR,
            "bear":          MarketRegime.BEAR,
            "volatile":      MarketRegime.VOLATILE,
        }
        for r in self._metadata.preferred_regimes:
            regime = _regime_map.get(r.lower())
            if regime and regime not in preferred:
                preferred.append(regime)

        return StrategyDefinition(
            strategy_id=self._strategy_id,
            name=self._metadata.strategy_name,
            version="legacy-1.0",
            category=_map_category(self._metadata.category),
            asset_class=AssetClass.EQUITY,
            timeframe=StrategyTimeframe.INTRADAY,
            risk_level=_map_risk_level(self._metadata.max_loss_pct),
            initial_status=self._derive_status(),
            preferred_regimes=preferred,
            description=self._metadata.description or f"Migrated legacy strategy: {self._metadata.strategy_name}",
            tags=list(self._metadata.tags) + ["legacy", "migrated"],
            parameters={
                "min_rr":          self._metadata.min_rr,
                "max_loss_pct":    self._metadata.max_loss_pct,
                "stop_loss_pct":   self._metadata.stop_loss_pct,
                "target_multiplier": self._metadata.target_multiplier,
                "base_strategy":   self._metadata.base_strategy,
                "source":          self._metadata.source.value,
                "entry_conditions": [c.to_dict() for c in self._metadata.entry_conditions],
            },
            constraints={
                "max_loss_pct": self._metadata.max_loss_pct,
                "min_rr":       self._metadata.min_rr,
            },
        )

    def _derive_status(self) -> StrategyStatus:
        if self._metadata.is_approved:
            return StrategyStatus.PAPER_TRADING
        return StrategyStatus.TESTING
