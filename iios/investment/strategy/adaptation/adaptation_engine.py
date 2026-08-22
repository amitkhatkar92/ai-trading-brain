"""iios/investment/strategy/adaptation/adaptation_engine.py
Orchestrates all adaptation components for a single strategy.
"""
from __future__ import annotations

import threading
from typing import Any

from iios.investment.strategy.core.strategy_profile import StrategyProfile
from iios.investment.strategy.adaptation.adaptation_result import AdaptationResult
from iios.investment.strategy.adaptation.regime_adapter import RegimeAdapter
from iios.investment.strategy.adaptation.parameter_adapter import ParameterAdapter
from iios.investment.strategy.adaptation.strategy_optimizer import StrategyOptimizer
from iios.investment.strategy.evaluation.strategy_score import StrategyScore
from iios.investment.strategy.performance.performance_tracker import StrategyStatistics


class AdaptationEngine:
    """
    Coordinates regime, parameter, and optimisation adapters.

    Returns the highest-confidence AdaptationResult from all adapters.
    Callers decide whether to apply the result.
    """

    def __init__(
        self,
        regime_adapter:    RegimeAdapter    | None = None,
        parameter_adapter: ParameterAdapter | None = None,
        optimizer:         StrategyOptimizer | None = None,
    ) -> None:
        self._lock      = threading.RLock()
        self._regime    = regime_adapter    or RegimeAdapter()
        self._parameter = parameter_adapter or ParameterAdapter()
        self._optimizer = optimizer         or StrategyOptimizer()

    def adapt(
        self,
        profile:        StrategyProfile,
        market_context: dict[str, Any]      = {},    # noqa: B006
        stats:          StrategyStatistics | None = None,
        score:          StrategyScore      | None = None,
    ) -> AdaptationResult:
        """
        Run all adapters and return the result with the highest confidence.
        If no adapter proposes changes, return a no-change result.
        """
        results: list[AdaptationResult] = []

        # 1. Regime adaptation
        if market_context:
            results.append(self._regime.adapt(profile, market_context))

        # 2. Parameter adaptation (requires performance stats)
        if stats is not None:
            results.append(self._parameter.adapt(profile, stats, market_context))

        # 3. Optimisation (requires evaluation score)
        if score is not None:
            results.append(self._optimizer.optimize(profile, score))

        # Select the result with highest confidence that has changes
        with_changes = [r for r in results if r.has_changes]
        if with_changes:
            best = max(with_changes, key=lambda r: r.confidence)
            return best

        # Fall back to first result or a no-change stub
        if results:
            return results[0]

        return AdaptationResult(
            strategy_id     = profile.strategy_id,
            original_params = dict(profile.active_params),
            adapted_params  = dict(profile.active_params),
            reason          = "No adaptation inputs provided",
            recommendation  = "no_change",
            confidence      = 0.0,
        )

    def adapt_regime(
        self,
        profile:        StrategyProfile,
        market_context: dict[str, Any],
    ) -> AdaptationResult:
        return self._regime.adapt(profile, market_context)

    def adapt_parameters(
        self,
        profile: StrategyProfile,
        stats:   StrategyStatistics,
    ) -> AdaptationResult:
        return self._parameter.adapt(profile, stats)

    def optimize(
        self,
        profile: StrategyProfile,
        score:   StrategyScore,
    ) -> AdaptationResult:
        return self._optimizer.optimize(profile, score)
