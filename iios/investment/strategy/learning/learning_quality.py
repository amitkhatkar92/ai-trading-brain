"""iios/investment/strategy/learning/learning_quality.py
LearningQuality — assesses the quality of the learning process itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from iios.investment.strategy.learning.learning_input import LearningObservation
from iios.investment.strategy.learning.learning_profile import StrategyLearningProfile
from iios.investment.strategy.learning.success_pattern import SuccessPattern
from iios.investment.strategy.learning.failure_pattern import FailurePattern
from iios.investment.strategy.learning.drift_detector import DriftSignal
from iios.investment.strategy.learning.recommendation_engine import Recommendation
from iios.investment.strategy.learning.learning_statistics import clamp


def _grade(score: float) -> str:
    if score >= 80: return "A"
    if score >= 65: return "B"
    if score >= 50: return "C"
    if score >= 35: return "D"
    return "F"


@dataclass(frozen=True)
class LearningQuality:
    """
    Assesses the quality of the learning process itself.
    High quality means: sufficient data, stable patterns, and well-evidenced recommendations.
    """
    strategy_id:            str
    input_completeness:     float   # 0-100; optional observation fields populated
    pattern_quality:        float   # 0-100; patterns have sufficient evidence
    drift_quality:          float   # 0-100; enough obs for reliable drift detection
    recommendation_quality: float   # 0-100; recommendations are well-evidenced
    overall_quality:        float   # 0-100
    grade:                  str     # A/B/C/D/F
    quality_issues:         List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":            self.strategy_id,
            "input_completeness":     round(self.input_completeness, 2),
            "pattern_quality":        round(self.pattern_quality, 2),
            "drift_quality":          round(self.drift_quality, 2),
            "recommendation_quality": round(self.recommendation_quality, 2),
            "overall_quality":        round(self.overall_quality, 2),
            "grade":                  self.grade,
            "quality_issues":         self.quality_issues,
        }

    @classmethod
    def assess(
        cls,
        profile:          StrategyLearningProfile,
        observations:     List[LearningObservation],
        success_patterns: List[SuccessPattern],
        failure_patterns: List[FailurePattern],
        drift_signals:    List[DriftSignal],
        recommendations:  List[Recommendation],
    ) -> "LearningQuality":
        issues: List[str] = []

        # 1. Input completeness — how many optional fields are present
        input_completeness = cls._input_completeness(observations, issues)

        # 2. Pattern quality — pattern count and evidence
        pattern_quality = cls._pattern_quality(
            success_patterns, failure_patterns, observations, issues
        )

        # 3. Drift quality — enough observations for drift to be meaningful
        drift_quality = cls._drift_quality(observations, drift_signals, issues)

        # 4. Recommendation quality — evidenced recommendations
        rec_quality = cls._recommendation_quality(recommendations, issues)

        overall = clamp(
            0.30 * input_completeness
            + 0.30 * pattern_quality
            + 0.20 * drift_quality
            + 0.20 * rec_quality
        )

        return cls(
            strategy_id=profile.strategy_id,
            input_completeness=input_completeness,
            pattern_quality=pattern_quality,
            drift_quality=drift_quality,
            recommendation_quality=rec_quality,
            overall_quality=overall,
            grade=_grade(overall),
            quality_issues=issues,
        )

    @staticmethod
    def _input_completeness(
        observations: List[LearningObservation], issues: List[str]
    ) -> float:
        if not observations:
            issues.append("No observations provided")
            return 0.0
        # Check optional fields: trade_count, winning_trades, losing_trades
        has_trade_count  = sum(1 for o in observations if o.trade_count is not None)
        has_win_trades   = sum(1 for o in observations if o.winning_trades is not None)
        n = len(observations)
        trade_completeness = (has_trade_count + has_win_trades) / (2 * n) * 100.0
        if trade_completeness < 50.0:
            issues.append("Trade outcome data missing for >50% of observations")
        return clamp(trade_completeness)

    @staticmethod
    def _pattern_quality(
        success: List[SuccessPattern],
        failure: List[FailurePattern],
        observations: List[LearningObservation],
        issues: List[str],
    ) -> float:
        n = len(observations)
        if n < 5:
            issues.append("Insufficient observations for pattern extraction (need ≥5)")
            return 0.0
        # Good pattern quality: at least 1 success and 1 failure pattern with confidence ≥ 0.60
        high_conf_success = sum(1 for p in success if p.confidence >= 0.60)
        high_conf_failure = sum(1 for p in failure if p.confidence >= 0.60)
        if high_conf_success == 0:
            issues.append("No high-confidence success patterns found")
        if high_conf_failure == 0 and n >= 20:
            issues.append("No high-confidence failure patterns found despite sufficient history")
        base = min(high_conf_success * 20.0 + high_conf_failure * 15.0, 80.0)
        return clamp(base + min(n * 0.5, 20.0))

    @staticmethod
    def _drift_quality(
        observations: List[LearningObservation],
        drift_signals: List[DriftSignal],
        issues: List[str],
    ) -> float:
        n = len(observations)
        if n < 10:
            issues.append("Fewer than 10 observations — drift detection unreliable")
            return clamp(n * 5.0)
        # Good drift quality: multiple drift dimensions assessed
        unique_types = len(set(s.drift_type for s in drift_signals))
        base = clamp(min(unique_types * 20.0, 80.0) + min(n * 0.2, 20.0))
        if not drift_signals:
            issues.append("No drift signals computed — check observation windows")
        return base

    @staticmethod
    def _recommendation_quality(
        recommendations: List[Recommendation], issues: List[str]
    ) -> float:
        if not recommendations:
            issues.append("No recommendations generated")
            return 30.0   # neutral — not penalised for having a good strategy
        # Quality improves with evidence depth
        avg_evidence = sum(len(r.evidence) for r in recommendations) / len(recommendations)
        reversible_pct = sum(1 for r in recommendations if r.is_reversible) / len(recommendations)
        base = clamp(
            min(avg_evidence * 20.0, 60.0)
            + reversible_pct * 40.0
        )
        if reversible_pct < 0.5:
            issues.append("More than 50% of recommendations are not marked reversible")
        return base
