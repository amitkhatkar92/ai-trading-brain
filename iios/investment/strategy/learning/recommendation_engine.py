"""iios/investment/strategy/learning/recommendation_engine.py
RecommendationEngine — generates, scores, and stores recommendations.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from iios.investment.strategy.learning.degradation_detector import DegradationReport, DegradationLevel
from iios.investment.strategy.learning.adaptation_engine import AdaptationReport
from iios.investment.strategy.learning.knowledge_engine import KnowledgeReport
from iios.investment.strategy.learning.learning_profile import StrategyLearningProfile
from iios.investment.strategy.learning.improvement_engine import ImprovementEngine, ImprovementSuggestion
from iios.investment.strategy.learning.adaptation_recommendations import AdaptationRecommendation
from iios.investment.strategy.learning.recommendation_score import score_recommendation, RecommendationScore
from iios.investment.strategy.learning.recommendation_history import (
    RecommendationHistory, RecommendationRecord,
)
from iios.investment.strategy.learning.learning_statistics import clamp


class RecommendationType(str, Enum):
    MAINTAIN          = "maintain"
    FURTHER_TESTING   = "further_testing"
    PARAMETER_REVIEW  = "parameter_review"
    REGIME_FOCUS      = "regime_focus"
    RISK_ADJUSTMENT   = "risk_adjustment"
    FURTHER_REVIEW    = "further_review"
    RETIREMENT        = "retirement"
    WATCH             = "watch"


@dataclass(frozen=True)
class Recommendation:
    """
    Final recommendation object: explainable, auditable, reversible.
    Recommendations must never be auto-applied.
    """
    recommendation_id: str
    strategy_id:       str
    rec_type:          RecommendationType
    priority:          str    # "HIGH" | "MEDIUM" | "LOW"
    title:             str
    rationale:         str
    evidence:          List[str]
    expected_impact:   str
    priority_score:    float
    is_reversible:     bool = True
    created_at:        datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "strategy_id":       self.strategy_id,
            "rec_type":          self.rec_type.value,
            "priority":          self.priority,
            "title":             self.title,
            "rationale":         self.rationale,
            "evidence":          self.evidence,
            "expected_impact":   self.expected_impact,
            "priority_score":    round(self.priority_score, 2),
            "is_reversible":     self.is_reversible,
            "created_at":        self.created_at.isoformat(),
        }


class RecommendationEngine:
    """
    Synthesises all learning signals into final Recommendation objects.
    Scores and deduplicates recommendations, stores audit trail.
    """

    def __init__(
        self,
        history: Optional[RecommendationHistory] = None,
        cooldown_obs: int = 5,
    ) -> None:
        self._history    = history or RecommendationHistory()
        self._improvement = ImprovementEngine()
        self._cooldown   = cooldown_obs

    def generate(
        self,
        profile:     StrategyLearningProfile,
        degradation: Optional[DegradationReport]  = None,
        adaptation:  Optional[AdaptationReport]   = None,
        knowledge:   Optional[KnowledgeReport]    = None,
    ) -> List[Recommendation]:
        recs: List[Recommendation] = []
        sid  = profile.strategy_id

        # 1. Base recommendation from maturity / overall state
        recs += self._base_recs(profile, degradation)

        # 2. From improvement engine
        suggestions = self._improvement.suggest(profile, degradation, adaptation, knowledge)
        recs += self._from_suggestions(sid, suggestions, degradation)

        # 3. From adaptation recommendations
        if adaptation:
            for ar in adaptation.recommendations:
                recs.append(self._from_adaptation_rec(ar))

        # Deduplicate and sort by priority
        recs = self._deduplicate(recs)
        recs.sort(key=lambda r: r.priority_score, reverse=True)

        # Store in history
        records = [self._to_record(r) for r in recs]
        self._history.add_all(records)

        return recs

    # ── base recommendations ──────────────────────────────────────────────────

    def _base_recs(
        self,
        profile:     StrategyLearningProfile,
        degradation: Optional[DegradationReport],
    ) -> List[Recommendation]:
        recs: List[Recommendation] = []
        sid  = profile.strategy_id

        if profile.maturity_level == "nascent":
            recs.append(Recommendation(
                recommendation_id=str(uuid.uuid4()),
                strategy_id=sid,
                rec_type=RecommendationType.FURTHER_TESTING,
                priority="LOW",
                title="Continue testing — strategy is nascent",
                rationale="Insufficient observation history to form reliable conclusions.",
                evidence=[f"Observations: {profile.observation_count}"],
                expected_impact="low",
                priority_score=20.0,
            ))

        if degradation and degradation.level == DegradationLevel.CRITICAL:
            recs.append(Recommendation(
                recommendation_id=str(uuid.uuid4()),
                strategy_id=sid,
                rec_type=RecommendationType.RETIREMENT,
                priority="HIGH",
                title="Strategy retirement recommended",
                rationale=(
                    f"Critical degradation ({degradation.degradation_score:.1f}/100) "
                    "with no observed recovery trajectory."
                ),
                evidence=[
                    f"Degradation level: {degradation.level.value}",
                    f"Recovery possible: {degradation.recovery_possible}",
                ],
                expected_impact="high",
                priority_score=90.0,
            ))
        elif degradation and degradation.level in (DegradationLevel.MODERATE, DegradationLevel.SEVERE):
            recs.append(Recommendation(
                recommendation_id=str(uuid.uuid4()),
                strategy_id=sid,
                rec_type=RecommendationType.FURTHER_REVIEW,
                priority="HIGH",
                title="Initiate performance review",
                rationale=f"{degradation.level.value.capitalize()} degradation detected.",
                evidence=[f"Degradation score: {degradation.degradation_score:.1f}"],
                expected_impact="high",
                priority_score=75.0,
            ))

        if (degradation is None or degradation.level == DegradationLevel.NONE) and \
                profile.maturity_level in ("established", "mature", "veteran"):
            recs.append(Recommendation(
                recommendation_id=str(uuid.uuid4()),
                strategy_id=sid,
                rec_type=RecommendationType.MAINTAIN,
                priority="LOW",
                title="Maintain current deployment",
                rationale="No degradation detected in a mature strategy.",
                evidence=[
                    f"Maturity: {profile.maturity_level}",
                    f"Observations: {profile.observation_count}",
                ],
                expected_impact="low",
                priority_score=10.0,
            ))

        return recs

    def _from_suggestions(
        self,
        sid:         str,
        suggestions: List[ImprovementSuggestion],
        degradation: Optional[DegradationReport],
    ) -> List[Recommendation]:
        recs: List[Recommendation] = []
        for s in suggestions:
            urgency = 80.0 if s.expected_impact == "high" else (50.0 if s.expected_impact == "medium" else 25.0)
            impact  = 80.0 if s.expected_impact == "high" else (50.0 if s.expected_impact == "medium" else 25.0)
            sc = score_recommendation(urgency=urgency, impact=impact, confidence=65.0)
            recs.append(Recommendation(
                recommendation_id=str(uuid.uuid4()),
                strategy_id=sid,
                rec_type=self._category_to_type(s.category),
                priority=sc.priority_label,
                title=s.title,
                rationale=s.rationale,
                evidence=s.evidence,
                expected_impact=s.expected_impact,
                priority_score=sc.priority_score,
                is_reversible=s.is_reversible,
            ))
        return recs

    def _from_adaptation_rec(self, ar: AdaptationRecommendation) -> Recommendation:
        urgency = 70.0 if ar.priority == "HIGH" else (45.0 if ar.priority == "MEDIUM" else 20.0)
        sc = score_recommendation(urgency=urgency, impact=urgency, confidence=60.0)
        return Recommendation(
            recommendation_id=str(uuid.uuid4()),
            strategy_id=ar.strategy_id,
            rec_type=RecommendationType.REGIME_FOCUS if ar.category == "regime"
                     else RecommendationType.PARAMETER_REVIEW,
            priority=ar.priority,
            title=ar.title,
            rationale=ar.rationale,
            evidence=ar.evidence,
            expected_impact="medium",
            priority_score=sc.priority_score,
            is_reversible=ar.is_reversible,
        )

    @staticmethod
    def _category_to_type(category: str) -> RecommendationType:
        return {
            "risk":      RecommendationType.RISK_ADJUSTMENT,
            "regime":    RecommendationType.REGIME_FOCUS,
            "parameter": RecommendationType.PARAMETER_REVIEW,
            "lifecycle": RecommendationType.FURTHER_REVIEW,
            "performance": RecommendationType.FURTHER_REVIEW,
        }.get(category, RecommendationType.WATCH)

    @staticmethod
    def _deduplicate(recs: List[Recommendation]) -> List[Recommendation]:
        seen: set = set()
        unique: List[Recommendation] = []
        for r in recs:
            if r.title not in seen:
                seen.add(r.title)
                unique.append(r)
        return unique

    @staticmethod
    def _to_record(r: Recommendation) -> RecommendationRecord:
        return RecommendationRecord(
            record_id=r.recommendation_id,
            strategy_id=r.strategy_id,
            rec_type=r.rec_type.value,
            priority=r.priority,
            title=r.title,
            rationale=r.rationale,
            evidence=r.evidence,
            priority_score=r.priority_score,
            is_reversible=r.is_reversible,
            created_at=r.created_at,
        )

    def history(self, strategy_id: str, n: int = 20) -> List[RecommendationRecord]:
        return self._history.get_recent(strategy_id, n)
