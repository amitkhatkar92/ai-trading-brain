"""iios/investment/strategy/learning/learning_score.py
LearningScore — overall learning quality score for a strategy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from iios.investment.strategy.learning.learning_profile import StrategyLearningProfile
from iios.investment.strategy.learning.performance_learning import PerformanceLearningResult
from iios.investment.strategy.learning.adaptation_engine import AdaptationReport
from iios.investment.strategy.learning.knowledge_engine import KnowledgeReport
from iios.investment.strategy.learning.strategy_maturity import StrategyMaturity
from iios.investment.strategy.learning.learning_confidence import LearningConfidence
from iios.investment.strategy.learning.learning_statistics import clamp


def _grade(score: float) -> str:
    if score >= 80: return "A"
    if score >= 65: return "B"
    if score >= 50: return "C"
    if score >= 35: return "D"
    return "F"


@dataclass(frozen=True)
class LearningScore:
    """Composite learning score for a strategy."""
    strategy_id:              str
    scored_at:                datetime

    performance_learning_score: float  # from PerformanceLearner
    adaptation_score:          float   # from AdaptationEngine
    knowledge_score:           float   # from KnowledgeEngine
    consistency_score:         float   # from profile consistency
    improvement_potential:     float   # headroom from current score

    overall_learning_score:    float   # 0-100
    learning_grade:            str     # A/B/C/D/F

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":               self.strategy_id,
            "scored_at":                 self.scored_at.isoformat(),
            "performance_learning_score": round(self.performance_learning_score, 2),
            "adaptation_score":          round(self.adaptation_score, 2),
            "knowledge_score":           round(self.knowledge_score, 2),
            "consistency_score":         round(self.consistency_score, 2),
            "improvement_potential":     round(self.improvement_potential, 2),
            "overall_learning_score":    round(self.overall_learning_score, 2),
            "learning_grade":            self.learning_grade,
        }


class LearningScoreCalculator:
    """
    Calculates the overall learning score.
    Weights: performance 35%, adaptation 25%, knowledge 20%, consistency 20%.
    """

    WEIGHTS = {
        "performance": 0.35,
        "adaptation":  0.25,
        "knowledge":   0.20,
        "consistency": 0.20,
    }

    def score(
        self,
        profile:              StrategyLearningProfile,
        performance_result:   Optional[PerformanceLearningResult],
        adaptation_report:    Optional[AdaptationReport],
        knowledge_report:     Optional[KnowledgeReport],
        maturity:             Optional[StrategyMaturity],
        confidence:           Optional[LearningConfidence],
    ) -> LearningScore:
        sid = profile.strategy_id

        # Performance learning score
        if performance_result:
            perf_score = clamp(performance_result.score_consistency)
        else:
            perf_score = 0.0

        # Adaptation score
        adapt_score = clamp(adaptation_report.overall_adaptation) \
            if adaptation_report else 0.0

        # Knowledge score
        know_score = clamp(knowledge_report.knowledge_score) \
            if knowledge_report else 0.0

        # Consistency from profile
        from iios.investment.strategy.learning.learning_statistics import consistency_score as _cs
        raw_consistency = _cs(profile.recent_scores)
        cons_score = clamp(raw_consistency)

        # Composite
        overall = clamp(
            self.WEIGHTS["performance"] * perf_score
            + self.WEIGHTS["adaptation"] * adapt_score
            + self.WEIGHTS["knowledge"]  * know_score
            + self.WEIGHTS["consistency"] * cons_score
        )

        # Improvement potential: headroom from current smoothed score to 100
        improvement_potential = clamp(100.0 - profile.smoothed_score)

        # Adjust downward if confidence is low
        if confidence and confidence.overall_confidence < 40.0:
            overall = clamp(overall * (confidence.overall_confidence / 100.0))

        return LearningScore(
            strategy_id=sid,
            scored_at=datetime.now(timezone.utc),
            performance_learning_score=perf_score,
            adaptation_score=adapt_score,
            knowledge_score=know_score,
            consistency_score=cons_score,
            improvement_potential=improvement_potential,
            overall_learning_score=overall,
            learning_grade=_grade(overall),
        )
