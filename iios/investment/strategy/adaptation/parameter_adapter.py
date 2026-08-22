"""iios/investment/strategy/adaptation/parameter_adapter.py
Adjusts strategy parameters based on observed performance metrics.
"""
from __future__ import annotations

from typing import Any

from iios.investment.strategy.strategy_constants import (
    AdaptationType,
    MIN_WIN_RATE,
    MIN_SHARPE,
    MAX_DRAWDOWN,
)
from iios.investment.strategy.core.strategy_profile import StrategyProfile
from iios.investment.strategy.adaptation.adaptation_result import AdaptationResult
from iios.investment.strategy.performance.performance_tracker import StrategyStatistics


class ParameterAdapter:
    """
    Proposes parameter adjustments driven by observed performance.

    Heuristics:
    - Win rate below MIN_WIN_RATE → tighten entry thresholds
    - Max drawdown above MAX_DRAWDOWN → reduce position_size and tighten stop_loss
    - Sharpe below MIN_SHARPE → suggest lower risk exposure
    """

    def adapt(
        self,
        profile:   StrategyProfile,
        stats:     StrategyStatistics,
        context:   dict[str, Any] | None = None,
    ) -> AdaptationResult:
        original = dict(profile.active_params)
        adapted  = dict(original)
        changes: dict[str, Any] = {}
        reasons: list[str]      = []

        # 1. Win rate too low → tighten entry filter
        if stats.total_trades >= 10 and stats.win_rate < MIN_WIN_RATE:
            for param, val in original.items():
                if isinstance(val, (int, float)) and "threshold" in param.lower():
                    new_val = round(val * 1.10, 6)   # raise threshold 10%
                    adapted[param] = new_val
                    changes[param] = {"old": val, "new": new_val}
            reasons.append(f"win_rate={stats.win_rate:.2%} < threshold")

        # 2. Drawdown too high → reduce position size
        if stats.max_drawdown > MAX_DRAWDOWN:
            for param, val in original.items():
                if isinstance(val, (int, float)) and "position_size" in param.lower():
                    new_val = round(val * 0.75, 6)
                    adapted[param] = new_val
                    changes[param] = {"old": val, "new": new_val}
            reasons.append(f"max_drawdown={stats.max_drawdown:.2%} > threshold")

        # 3. Sharpe too low → tighten stop loss
        if stats.total_trades >= 10 and stats.sharpe_ratio < MIN_SHARPE:
            for param, val in original.items():
                if isinstance(val, (int, float)) and "stop_loss" in param.lower():
                    new_val = round(val * 0.85, 6)
                    adapted[param] = new_val
                    changes[param] = {"old": val, "new": new_val}
            reasons.append(f"sharpe={stats.sharpe_ratio:.3f} < threshold")

        reason     = "; ".join(reasons) if reasons else "No adjustment needed"
        confidence = 0.70 if changes and stats.total_trades >= 20 else 0.40

        return AdaptationResult(
            strategy_id      = profile.strategy_id,
            adaptation_type  = AdaptationType.PARAMETER,
            original_params  = original,
            adapted_params   = adapted,
            changes          = changes,
            reason           = reason,
            recommendation   = "apply" if changes else "no_change",
            confidence       = confidence,
            metadata         = {
                "win_rate":     stats.win_rate,
                "max_drawdown": stats.max_drawdown,
                "sharpe":       stats.sharpe_ratio,
                "n_trades":     stats.total_trades,
            },
        )
