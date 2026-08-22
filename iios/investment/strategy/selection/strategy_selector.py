"""iios/investment/strategy/selection/strategy_selector.py
Selects the best strategies for a given market context.
"""
from __future__ import annotations

import threading
from typing import Any

from iios.investment.strategy.strategy_constants import (
    StrategyStatus,
    RegimeCompatibility,
    MarketRegime,
)
from iios.investment.strategy.strategy_exceptions import (
    NoStrategiesAvailableError,
)
from iios.investment.strategy.core.strategy_profile import StrategyProfile
from iios.investment.strategy.evaluation.strategy_evaluator import StrategyEvaluator
from iios.investment.strategy.evaluation.strategy_ranker import StrategyRanker
from iios.investment.strategy.evaluation.strategy_score import StrategyScore
from iios.investment.strategy.performance.performance_record import PerformanceRecord


class StrategySelector:
    """
    Selects the most suitable strategies for the current market context.

    Selection pipeline:
    1. Filter profiles to evaluable statuses
    2. Optionally filter by regime compatibility
    3. Evaluate each strategy
    4. Rank and return top-N
    """

    SELECTABLE_STATUSES = frozenset({
        StrategyStatus.APPROVED,
        StrategyStatus.PRODUCTION,
        StrategyStatus.TESTING,       # allow during selection for paper-trading contexts
        StrategyStatus.PAPER_TRADING,
        StrategyStatus.VALIDATION,
    })

    def __init__(
        self,
        evaluator: StrategyEvaluator | None = None,
        ranker:    StrategyRanker    | None = None,
    ) -> None:
        self._lock      = threading.RLock()
        self._evaluator = evaluator or StrategyEvaluator()
        self._ranker    = ranker    or StrategyRanker()

    def select(
        self,
        profiles:        list[StrategyProfile],
        records_map:     dict[str, list[PerformanceRecord]] | None = None,
        market_context:  dict[str, Any]                    | None = None,
        n:               int                               = 5,
        min_score:       float                             = 40.0,
        require_regime_compat: bool                        = False,
    ) -> list[StrategyScore]:
        """
        Return top-N strategies best suited to the market context.

        Parameters
        ----------
        profiles              : All candidate StrategyProfiles from the registry
        records_map           : Optional pre-loaded records per strategy_id
        market_context        : Dict with at least ``regime`` key
        n                     : Number of strategies to return
        min_score             : Minimum overall_score to include
        require_regime_compat : When True only strategies that declare the
                                current regime as preferred are considered
        """
        if not profiles:
            raise NoStrategiesAvailableError("No strategy profiles provided")

        records_map    = records_map    or {}
        market_context = market_context or {}

        # 1. Filter to selectable statuses
        candidates = [
            p for p in profiles
            if p.lifecycle_status in self.SELECTABLE_STATUSES
        ]

        # 2. Optionally filter by regime compatibility
        if require_regime_compat and market_context:
            regime_str = market_context.get("regime", "unknown")
            try:
                regime = MarketRegime(regime_str)
            except ValueError:
                regime = MarketRegime.UNKNOWN

            if regime != MarketRegime.UNKNOWN:
                compat = [
                    p for p in candidates
                    if p.definition.is_compatible_with_regime(regime)
                ]
                # Fall back to all candidates if none declared compatible
                candidates = compat or candidates

        if not candidates:
            raise NoStrategiesAvailableError(
                "No strategies available after filtering"
            )

        # 3. Evaluate
        scores = self._evaluator.evaluate_batch(
            candidates, records_map, market_context
        )

        # 4. Rank, filter, return top-N
        filtered = self._ranker.filter_by_threshold(scores, min_score)
        top      = self._ranker.top_n(filtered or scores, n)
        return top

    def regime_compatibility(
        self,
        profile:        StrategyProfile,
        market_context: dict[str, Any],
    ) -> RegimeCompatibility:
        """
        Classify the regime compatibility of a single strategy.
        """
        if not market_context:
            return RegimeCompatibility.UNKNOWN

        regime_str = market_context.get("regime", "unknown")
        try:
            regime = MarketRegime(regime_str)
        except ValueError:
            return RegimeCompatibility.UNKNOWN

        defn = profile.definition
        if not defn.preferred_regimes:
            return RegimeCompatibility.NEUTRAL

        if regime in defn.preferred_regimes:
            return RegimeCompatibility.OPTIMAL

        # Partially compatible heuristic based on score
        score = self._evaluator._score_regime(profile, market_context)
        if score >= 70:
            return RegimeCompatibility.COMPATIBLE
        elif score >= 50:
            return RegimeCompatibility.NEUTRAL
        elif score >= 30:
            return RegimeCompatibility.SUBOPTIMAL
        else:
            return RegimeCompatibility.INCOMPATIBLE
