"""iios/investment/strategy/adaptation/strategy_optimizer.py
Suggests version-bumped parameter improvements for a strategy.
"""
from __future__ import annotations

from typing import Any

from iios.investment.strategy.strategy_constants import AdaptationType
from iios.investment.strategy.core.strategy_profile import StrategyProfile
from iios.investment.strategy.adaptation.adaptation_result import AdaptationResult
from iios.investment.strategy.evaluation.strategy_score import StrategyScore


class StrategyOptimizer:
    """
    Proposes holistic parameter improvements based on the evaluation score.

    Unlike ParameterAdapter (which reacts to bad metrics), the Optimizer
    aims to push a working strategy toward its performance ceiling.
    """

    def optimize(
        self,
        profile:     StrategyProfile,
        score:       StrategyScore,
        constraints: dict[str, Any] | None = None,
    ) -> AdaptationResult:
        constraints = constraints or {}
        original    = dict(profile.active_params)
        adapted     = dict(original)
        changes: dict[str, Any] = {}
        suggestions: list[str]  = []

        # Only optimise strategies with reasonable data
        if not score.confidence_score >= 30:
            return AdaptationResult(
                strategy_id    = profile.strategy_id,
                adaptation_type = AdaptationType.CUSTOM,
                original_params = original,
                adapted_params  = adapted,
                reason         = "Insufficient data for optimisation",
                recommendation = "collect_more_data",
                confidence     = 0.10,
            )

        # Reward high-performing strategies: slightly expand position sizing
        if score.overall_score >= 75 and score.max_drawdown <= 0.10:
            for param, val in original.items():
                if isinstance(val, (int, float)) and "position_size" in param.lower():
                    max_size = float(constraints.get("max_position_size", val * 1.5))
                    new_val  = round(min(val * 1.10, max_size), 6)
                    if new_val != val:
                        adapted[param] = new_val
                        changes[param] = {"old": val, "new": new_val}
            suggestions.append("Position sizing expanded (excellent performance)")

        # For moderate performers: try relaxing entry filters slightly
        if 55 <= score.overall_score < 75 and score.win_rate >= 0.48:
            for param, val in original.items():
                if isinstance(val, (int, float)) and "threshold" in param.lower():
                    new_val = round(val * 0.95, 6)   # relax 5%
                    adapted[param] = new_val
                    changes[param] = {"old": val, "new": new_val}
            suggestions.append("Entry threshold relaxed (moderate performance)")

        reason = "; ".join(suggestions) if suggestions else "No optimisation applied"
        new_version = (
            self._bump_patch(profile.current_version) if changes else profile.current_version
        )

        return AdaptationResult(
            strategy_id      = profile.strategy_id,
            adaptation_type  = AdaptationType.CUSTOM,
            original_params  = original,
            adapted_params   = adapted,
            changes          = changes,
            reason           = reason,
            recommendation   = "apply_and_bump_version" if changes else "no_change",
            confidence       = min(0.90, score.confidence_score / 100.0),
            metadata         = {
                "overall_score": score.overall_score,
                "new_version":   new_version,
                "suggestions":   suggestions,
            },
        )

    @staticmethod
    def _bump_patch(version: str) -> str:
        parts = version.split(".")
        if len(parts) == 3:
            try:
                parts[2] = str(int(parts[2]) + 1)
                return ".".join(parts)
            except ValueError:
                pass
        return version
