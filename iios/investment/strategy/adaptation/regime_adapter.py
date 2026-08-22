"""iios/investment/strategy/adaptation/regime_adapter.py
Adjusts strategy parameters based on the detected market regime.
"""
from __future__ import annotations

from typing import Any

from iios.investment.strategy.strategy_constants import AdaptationType, MarketRegime
from iios.investment.strategy.core.strategy_profile import StrategyProfile
from iios.investment.strategy.adaptation.adaptation_result import AdaptationResult

# Regime-specific parameter scaling rules:
# Maps regime → {param_suffix → scale_factor}
_REGIME_RULES: dict[str, dict[str, float]] = {
    MarketRegime.VOLATILE.value:        {"stop_loss": 0.70, "position_size": 0.80},
    MarketRegime.HIGH_VOLATILITY.value: {"stop_loss": 0.60, "position_size": 0.70},
    MarketRegime.BEAR.value:            {"stop_loss": 0.80, "position_size": 0.75},
    MarketRegime.BULL.value:            {"stop_loss": 1.10, "position_size": 1.10},
    MarketRegime.LOW_VOLATILITY.value:  {"stop_loss": 1.20, "position_size": 1.00},
    MarketRegime.SIDEWAYS.value:        {"stop_loss": 0.90, "position_size": 0.90},
    MarketRegime.TRENDING.value:        {"stop_loss": 1.00, "position_size": 1.05},
}


class RegimeAdapter:
    """
    Proposes parameter adjustments driven by the current market regime.

    Only numeric parameters whose names contain regime-sensitive suffixes
    (``stop_loss``, ``position_size``) are modified.  The result is NOT
    automatically applied — the AdaptationEngine decides whether to commit.
    """

    def adapt(
        self,
        profile:        StrategyProfile,
        market_context: dict[str, Any],
    ) -> AdaptationResult:
        regime_str = market_context.get("regime", "unknown")
        rules      = _REGIME_RULES.get(regime_str, {})

        original = dict(profile.active_params)
        adapted  = dict(original)
        changes: dict[str, Any] = {}

        for param, val in original.items():
            if not isinstance(val, (int, float)):
                continue
            for suffix, factor in rules.items():
                if suffix in param.lower():
                    new_val = round(val * factor, 6)
                    if new_val != val:
                        adapted[param] = new_val
                        changes[param] = {"old": val, "new": new_val, "factor": factor}

        compatible = profile.definition.is_compatible_with_regime(
            MarketRegime(regime_str) if regime_str in MarketRegime._value2member_map_ else MarketRegime.UNKNOWN
        )
        confidence = 0.80 if compatible else 0.50

        reason = (
            f"Regime '{regime_str}' adaptation"
            + (" (strategy compatible)" if compatible else " (strategy not preferred for this regime)")
        )

        return AdaptationResult(
            strategy_id      = profile.strategy_id,
            adaptation_type  = AdaptationType.REGIME,
            original_params  = original,
            adapted_params   = adapted,
            changes          = changes,
            reason           = reason,
            recommendation   = "apply" if changes else "no_change",
            confidence       = confidence,
            metadata         = {"regime": regime_str, "rules_applied": list(rules.keys())},
        )
