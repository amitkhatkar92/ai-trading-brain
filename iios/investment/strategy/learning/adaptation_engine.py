"""iios/investment/strategy/learning/adaptation_engine.py
AdaptationEngine — orchestrates regime and parameter adaptation analysis.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.learning.learning_input import LearningObservation
from iios.investment.strategy.learning.parameter_analysis import (
    ParameterAnalyzer, ParameterStabilityResult,
)
from iios.investment.strategy.learning.regime_adaptation import (
    RegimeAdaptationAnalyzer, RegimeAdaptationResult,
)
from iios.investment.strategy.learning.adaptation_recommendations import (
    AdaptationRecommendation, generate_adaptation_recommendations,
)
from iios.investment.strategy.learning.learning_statistics import clamp


@dataclass(frozen=True)
class AdaptationReport:
    """Complete adaptation intelligence for a strategy."""
    strategy_id:       str
    assessed_at:       datetime

    regime_result:     Optional[RegimeAdaptationResult]
    param_result:      Optional[ParameterStabilityResult]
    recommendations:   List[AdaptationRecommendation]

    adaptability_score:    float    # 0-100 composite
    parameter_stability:   float    # 0-100
    overall_adaptation:    float    # weighted composite

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":          self.strategy_id,
            "assessed_at":          self.assessed_at.isoformat(),
            "adaptability_score":   round(self.adaptability_score, 2),
            "parameter_stability":  round(self.parameter_stability, 2),
            "overall_adaptation":   round(self.overall_adaptation, 2),
            "recommendation_count": len(self.recommendations),
            "regime_result":        self.regime_result.to_dict() if self.regime_result else None,
            "param_result":         self.param_result.to_dict() if self.param_result else None,
        }


class AdaptationEngine:
    """
    Orchestrates regime adaptation and parameter stability analysis.
    Produces an AdaptationReport with ranked recommendations.
    Does NOT modify any strategy.
    """

    def __init__(self) -> None:
        self._regime_analyzer = RegimeAdaptationAnalyzer()
        self._param_analyzer  = ParameterAnalyzer()

    def analyse(self, observations: List[LearningObservation]) -> Optional[AdaptationReport]:
        if len(observations) < 3:
            return None

        sid = observations[0].strategy_id

        regime_result = self._regime_analyzer.analyse(observations)
        param_result  = self._param_analyzer.analyse(observations)

        recs = generate_adaptation_recommendations(sid, regime_result, param_result)

        adaptability  = regime_result.adaptability_score if regime_result else 50.0
        param_stab    = param_result.overall_stability   if param_result  else 50.0

        overall = clamp(
            0.60 * adaptability
            + 0.40 * param_stab
        )

        return AdaptationReport(
            strategy_id=sid,
            assessed_at=datetime.now(timezone.utc),
            regime_result=regime_result,
            param_result=param_result,
            recommendations=recs,
            adaptability_score=adaptability,
            parameter_stability=param_stab,
            overall_adaptation=overall,
        )
