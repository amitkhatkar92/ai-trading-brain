"""iios/investment/strategy/migration/compatibility_layer.py
Translates between legacy strategy conventions and IIOS interfaces.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from iios.investment.strategy.migration.legacy_metadata import (
    LegacyStrategyMetadata,
    LegacyStrategySource,
    LegacyStrategyType,
)
from iios.investment.strategy.strategy_constants import (
    AssetClass,
    StrategyCategory,
    StrategyRiskLevel,
    StrategyTimeframe,
    MarketRegime,
)


# ── Parameter name translation map ────────────────────────────────────────────
# legacy_name → iios_name
_PARAM_TRANSLATION: Dict[str, str] = {
    "min_rr":               "minimum_risk_reward_ratio",
    "max_loss_pct":         "maximum_loss_percent",
    "stop_loss_pct":        "stop_loss_percent",
    "target_multiplier":    "profit_target_multiplier",
    "use_rsi_filter":       "rsi_filter_enabled",
    "volume_ratio":         "volume_confirmation_ratio",
    "base_strategy":        "parent_strategy_name",
}

# ── Regime translation maps ────────────────────────────────────────────────────
_LEGACY_TO_IIOS_REGIME: Dict[str, MarketRegime] = {
    "bull_trend":    MarketRegime.BULL,
    "bull":          MarketRegime.BULL,
    "range_market":  MarketRegime.SIDEWAYS,
    "ranging":       MarketRegime.SIDEWAYS,
    "bear_market":   MarketRegime.BEAR,
    "bear":          MarketRegime.BEAR,
    "volatile":      MarketRegime.VOLATILE,
    "high_vol":      MarketRegime.VOLATILE,
}

_IIOS_TO_LEGACY_REGIME: Dict[str, str] = {v.value: k for k, v in _LEGACY_TO_IIOS_REGIME.items()}

# ── Asset class inference ─────────────────────────────────────────────────────
_CATEGORY_ASSET_MAP: Dict[str, AssetClass] = {
    "options":       AssetClass.OPTIONS,
    "arbitrage":     AssetClass.FUTURES,
    "futures":       AssetClass.FUTURES,
    "hedging":       AssetClass.MIXED,
    "breakout":      AssetClass.EQUITY,
    "momentum":      AssetClass.EQUITY,
    "mean_reversion": AssetClass.EQUITY,
    "retest":        AssetClass.EQUITY,
    "trend_following": AssetClass.EQUITY,
}


class CompatibilityLayer:
    """
    Stateless translation service between legacy and IIOS conventions.
    Used by adapters to normalise parameters, types, and interface calls.
    """

    @staticmethod
    def translate_params(legacy_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Translate legacy parameter names to IIOS canonical names.
        Returns both original and translated parameters (non-destructive).
        """
        translated = {}
        for k, v in legacy_params.items():
            iios_key = _PARAM_TRANSLATION.get(k, k)
            translated[iios_key] = v
        return translated

    @staticmethod
    def translate_regime_to_iios(legacy_regime: str) -> Optional[MarketRegime]:
        return _LEGACY_TO_IIOS_REGIME.get(legacy_regime.lower())

    @staticmethod
    def translate_regime_to_legacy(iios_regime: str) -> Optional[str]:
        return _IIOS_TO_LEGACY_REGIME.get(iios_regime.lower())

    @staticmethod
    def translate_regimes_to_iios(legacy_regimes: List[str]) -> List[MarketRegime]:
        result = []
        for r in legacy_regimes:
            mapped = CompatibilityLayer.translate_regime_to_iios(r)
            if mapped and mapped not in result:
                result.append(mapped)
        return result

    @staticmethod
    def infer_asset_class(category: str, strategy_name: str = "") -> AssetClass:
        """Infer asset class from category and name."""
        cat_lower  = category.lower()
        name_lower = strategy_name.lower()
        if "option" in name_lower or "straddle" in name_lower or "spread" in name_lower:
            return AssetClass.OPTIONS
        if "futures" in name_lower or "arb" in name_lower:
            return AssetClass.FUTURES
        return _CATEGORY_ASSET_MAP.get(cat_lower, AssetClass.EQUITY)

    @staticmethod
    def infer_timeframe(strategy_name: str) -> StrategyTimeframe:
        """Infer timeframe from strategy name conventions."""
        name = strategy_name.lower()
        if "intraday" in name:
            return StrategyTimeframe.INTRADAY
        if "swing" in name:
            return StrategyTimeframe.SWING
        if "arb" in name or "arbitrage" in name:
            return StrategyTimeframe.SCALP
        return StrategyTimeframe.INTRADAY   # default for most legacy strategies

    @staticmethod
    def infer_category(strategy_name: str, raw_category: str) -> StrategyCategory:
        """Infer category from name and raw category string."""
        from iios.investment.strategy.strategy_constants import StrategyCategory as SC

        # Trust explicit category if useful
        explicit = raw_category.lower()
        if explicit in ("breakout", "momentum", "mean_reversion", "options",
                        "volatility", "arbitrage"):
            return {
                "breakout":      SC.BREAKOUT,
                "momentum":      SC.MOMENTUM,
                "mean_reversion": SC.MEAN_REVERSION,
                "options":       SC.OPTIONS,
                "volatility":    SC.VOLATILITY,
                "arbitrage":     SC.MARKET_NEUTRAL,
            }[explicit]

        # Fall back to name analysis
        name = strategy_name.lower()
        if "breakout" in name:     return SC.BREAKOUT
        if "momentum" in name:     return SC.MOMENTUM
        if "reversion" in name:    return SC.MEAN_REVERSION
        if "retest" in name:       return SC.RETEST
        if "straddle" in name or "condor" in name or "spread" in name:
            return SC.OPTIONS
        if "hedge" in name or "hedging" in name: return SC.MULTI_FACTOR
        if "arb" in name:          return SC.MARKET_NEUTRAL
        if "pullback" in name:     return SC.TREND_FOLLOWING
        return SC.CUSTOM

    @staticmethod
    def check_interface_gaps(metadata: LegacyStrategyMetadata) -> List[str]:
        """
        Identify interface gaps between legacy strategy and IIOS requirements.
        Returns a list of gap descriptions (empty = fully compatible).
        """
        gaps: List[str] = []

        # Required parameters
        if metadata.min_rr <= 0:
            gaps.append("min_rr is zero or negative")
        if metadata.max_loss_pct <= 0:
            gaps.append("max_loss_pct is zero or negative")

        # Regime coverage
        if not metadata.preferred_regimes and not metadata.compatible_regimes:
            gaps.append("No preferred regimes declared — strategy will match all regimes")

        # Performance data
        if metadata.source in (LegacyStrategySource.DISCOVERED_EDGES,
                                LegacyStrategySource.EVOLVED_STRATEGIES):
            if metadata.precision is None:
                gaps.append("Precision (hit rate) not available — evaluation confidence limited")
            if metadata.sharpe_ratio is None:
                gaps.append("Sharpe ratio not available — risk-adjusted return cannot be assessed")

        # Entry conditions for JSON strategies
        if metadata.strategy_type in (LegacyStrategyType.JSON_BASED,
                                       LegacyStrategyType.PATTERN_ONLY):
            if not metadata.entry_conditions:
                gaps.append("JSON-type strategy has no entry conditions — signal logic cannot be verified")

        return gaps

    @staticmethod
    def build_iios_params(metadata: LegacyStrategyMetadata) -> Dict[str, Any]:
        """Build IIOS-canonical parameters dict from legacy metadata."""
        params = CompatibilityLayer.translate_params({
            "min_rr":            metadata.min_rr,
            "max_loss_pct":      metadata.max_loss_pct,
            "stop_loss_pct":     metadata.stop_loss_pct,
            "target_multiplier": metadata.target_multiplier,
            "base_strategy":     metadata.base_strategy,
        })
        # Add entry conditions inline for transparency
        if metadata.entry_conditions:
            params["entry_conditions"] = [c.to_dict() for c in metadata.entry_conditions]
        # Add performance data if available
        perf = {
            k: v for k, v in {
                "precision":    metadata.precision,
                "support":      metadata.support,
                "sharpe_ratio": metadata.sharpe_ratio,
                "oos_win_rate": metadata.oos_win_rate,
                "max_drawdown": metadata.max_drawdown,
            }.items() if v is not None
        }
        if perf:
            params["legacy_performance"] = perf
        params["legacy_source"] = metadata.source.value
        params["legacy_strategy_type"] = metadata.strategy_type.value
        return params
