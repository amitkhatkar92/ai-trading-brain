"""iios/investment/strategy/learning/best_practices.py
BestPractice extraction from success patterns and positive observations.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

from iios.investment.strategy.learning.learning_input import LearningObservation
from iios.investment.strategy.learning.success_pattern import SuccessPattern
from iios.investment.strategy.learning.lesson_registry import Lesson, LessonCategory


@dataclass(frozen=True)
class BestPractice:
    """An extracted best practice from successful strategy periods."""
    practice_id:   str
    strategy_id:   str
    title:         str
    guideline:     str
    rationale:     str
    evidence:      List[str]
    confidence:    float
    created_at:    datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_lesson(self) -> Lesson:
        return Lesson(
            lesson_id=str(uuid.uuid4()),
            strategy_id=self.strategy_id,
            category=LessonCategory.SUCCESS,
            title=self.title,
            description=self.guideline,
            evidence=self.evidence,
            confidence=self.confidence,
            support_count=len(self.evidence),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "practice_id": self.practice_id,
            "strategy_id": self.strategy_id,
            "title":       self.title,
            "guideline":   self.guideline,
            "rationale":   self.rationale,
            "evidence":    self.evidence,
            "confidence":  round(self.confidence, 3),
        }


class BestPracticeExtractor:
    """Converts success patterns into structured best-practice guidelines."""

    def extract(
        self,
        strategy_id:      str,
        patterns:         List[SuccessPattern],
        observations:     List[LearningObservation],
    ) -> List[BestPractice]:
        practices: List[BestPractice] = []

        for pattern in patterns:
            if pattern.confidence < 0.60:
                continue

            if "regime_alignment" in pattern.name:
                regime = pattern.characteristic_regimes[0] if pattern.characteristic_regimes else "aligned"
                practices.append(BestPractice(
                    practice_id=str(uuid.uuid4()),
                    strategy_id=strategy_id,
                    title=f"Deploy in {regime} regime conditions",
                    guideline=(
                        f"Prioritise deployment when the market is in a {regime} regime. "
                        f"Historical success rate in this regime: {pattern.success_rate:.0%}."
                    ),
                    rationale=pattern.description,
                    evidence=[f"Support: {pattern.observation_count} observations",
                              f"Confidence: {pattern.confidence:.0%}"],
                    confidence=pattern.confidence,
                ))
            elif "drawdown" in pattern.name:
                practices.append(BestPractice(
                    practice_id=str(uuid.uuid4()),
                    strategy_id=strategy_id,
                    title="Maintain drawdown discipline",
                    guideline=(
                        "Strategy performs best when max drawdown is kept below 15% "
                        "combined with win rates above 55%. "
                        "Use tighter stops during elevated drawdown periods."
                    ),
                    rationale=pattern.description,
                    evidence=[f"Support: {pattern.observation_count} observations",
                              f"Success rate: {pattern.success_rate:.0%}"],
                    confidence=pattern.confidence,
                ))
            elif "sharpe" in pattern.name:
                practices.append(BestPractice(
                    practice_id=str(uuid.uuid4()),
                    strategy_id=strategy_id,
                    title="Operate only when risk-adjusted return is strong",
                    guideline=(
                        "Periods with Sharpe ratio ≥ 1.5 are strongly associated with high "
                        "evaluation scores. Monitor Sharpe as an early quality indicator."
                    ),
                    rationale=pattern.description,
                    evidence=[f"Support: {pattern.observation_count} observations"],
                    confidence=pattern.confidence,
                ))
            else:
                # Generic tag-based practice
                tag = pattern.characteristic_tags[0] if pattern.characteristic_tags else "identified"
                practices.append(BestPractice(
                    practice_id=str(uuid.uuid4()),
                    strategy_id=strategy_id,
                    title=f"Leverage {tag} conditions",
                    guideline=(
                        f"Strategy tag '{tag}' is consistently associated with above-threshold "
                        f"performance (success rate: {pattern.success_rate:.0%})."
                    ),
                    rationale=pattern.description,
                    evidence=[f"Support: {pattern.observation_count} observations",
                              f"Confidence: {pattern.confidence:.0%}"],
                    confidence=pattern.confidence,
                ))

        return practices
