"""iios/decision_evaluation/evaluation_factory.py — Convenience factory helpers."""
from __future__ import annotations

from typing import Callable

from .evaluation_constants import (
    CriterionDirection,
    NormalizationMethod,
    RankingMethod,
    ScoringMethod,
)
from .evaluation_context import Alternative
from .criteria.criterion import (
    BooleanCriterion,
    QualitativeCriterion,
    QuantitativeCriterion,
)
from .evaluation_manager import EvaluationRequest
from .tradeoff.tradeoff_analyzer import TradeoffPair
from .tradeoff.utility_engine import LinearUtility, SigmoidUtility, PowerUtility


class EvaluationFactory:
    @staticmethod
    def make_alternative(name: str = "", **payload) -> Alternative:
        return Alternative(name=name, payload=dict(payload))

    @staticmethod
    def make_quantitative_criterion(
        criterion_id: str,
        name:         str,
        extractor:    Callable[[Alternative], float],
        direction:    CriterionDirection = CriterionDirection.MAXIMIZE,
        weight:       float = 1.0,
    ) -> QuantitativeCriterion:
        return QuantitativeCriterion(
            criterion_id = criterion_id,
            name         = name,
            extractor    = extractor,
            direction    = direction,
            weight       = weight,
        )

    @staticmethod
    def make_qualitative_criterion(
        criterion_id: str,
        name:         str,
        scorer:       Callable[[Alternative], float],
        weight:       float = 1.0,
    ) -> QualitativeCriterion:
        return QualitativeCriterion(
            criterion_id = criterion_id,
            name         = name,
            scorer       = scorer,
            weight       = weight,
        )

    @staticmethod
    def make_boolean_criterion(
        criterion_id: str,
        name:         str,
        predicate:    Callable[[Alternative], bool],
        weight:       float = 1.0,
    ) -> BooleanCriterion:
        return BooleanCriterion(
            criterion_id = criterion_id,
            name         = name,
            predicate    = predicate,
            weight       = weight,
        )

    @staticmethod
    def make_tradeoff_pair(
        crit_a: str,
        crit_b: str,
        label:  str = "",
    ) -> TradeoffPair:
        return TradeoffPair(criterion_a=crit_a, criterion_b=crit_b, label=label)

    @staticmethod
    def make_linear_utility(slope: float = 1.0, intercept: float = 0.0) -> LinearUtility:
        return LinearUtility(slope=slope, intercept=intercept)

    @staticmethod
    def make_sigmoid_utility(k: float = 10.0, midpoint: float = 0.5) -> SigmoidUtility:
        return SigmoidUtility(k=k, midpoint=midpoint)

    @staticmethod
    def make_power_utility(power: float = 0.5) -> PowerUtility:
        return PowerUtility(power=power)

    @staticmethod
    def make_request(
        alternatives: list[Alternative],
        criteria:     list,
        **kwargs,
    ) -> EvaluationRequest:
        return EvaluationRequest(
            alternatives = alternatives,
            criteria     = criteria,
            **kwargs,
        )
