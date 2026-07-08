"""iios/decision_evaluation/tradeoff/tradeoff_engine.py"""
from __future__ import annotations

from ..scoring.score_calculator import AlternativeScore
from .tradeoff_analyzer import TradeoffAnalysis, TradeoffAnalyzer, TradeoffPair
from .utility_engine import UtilityEngine, UtilityFunction


class TradeoffEngine:
    """Orchestrates trade-off analysis and utility adjustments."""

    def __init__(
        self,
        analyzer:       TradeoffAnalyzer | None = None,
        utility_engine: UtilityEngine   | None = None,
    ) -> None:
        self._analyzer       = analyzer       or TradeoffAnalyzer()
        self._utility_engine = utility_engine or UtilityEngine()

    def analyze(
        self,
        alternatives: list[AlternativeScore],
        pairs:        list[TradeoffPair] | None = None,
    ) -> TradeoffAnalysis:
        return self._analyzer.analyze(alternatives, pairs or [])

    def apply_utility(
        self,
        alternatives: list[AlternativeScore],
        utility_fn:   UtilityFunction,
    ) -> list[AlternativeScore]:
        return self._utility_engine.apply_utility(alternatives, utility_fn)
