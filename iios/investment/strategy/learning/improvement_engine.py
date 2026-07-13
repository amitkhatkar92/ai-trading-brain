"""iios/investment/strategy/learning/improvement_engine.py
ImprovementEngine — generates improvement suggestions from learning signals.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.learning.degradation_detector import DegradationReport, DegradationLevel
from iios.investment.strategy.learning.adaptation_engine import AdaptationReport
from iios.investment.strategy.learning.knowledge_engine import KnowledgeReport
from iios.investment.strategy.learning.learning_profile import StrategyLearningProfile
from iios.investment.strategy.learning.learning_statistics import clamp


@dataclass(frozen=True)
class ImprovementSuggestion:
    """A specific, actionable improvement suggestion. NOT an automatic action."""
    suggestion_id:   str
    strategy_id:     str
    category:        str    # "performance" | "risk" | "regime" | "parameter" | "lifecycle"
    title:           str
    description:     str
    rationale:       str
    evidence:        List[str]
    expected_impact: str    # qualitative: "high" | "medium" | "low"
    is_reversible:   bool = True
    created_at:      datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suggestion_id":  self.suggestion_id,
            "strategy_id":    self.strategy_id,
            "category":       self.category,
            "title":          self.title,
            "description":    self.description,
            "rationale":      self.rationale,
            "evidence":       self.evidence,
            "expected_impact": self.expected_impact,
            "is_reversible":  self.is_reversible,
            "created_at":     self.created_at.isoformat(),
        }


class ImprovementEngine:
    """
    Synthesises improvement suggestions from degradation, adaptation, and knowledge reports.
    All suggestions are recommendations only — never auto-applied.
    """

    def suggest(
        self,
        profile:            StrategyLearningProfile,
        degradation:        Optional[DegradationReport],
        adaptation:         Optional[AdaptationReport],
        knowledge:          Optional[KnowledgeReport],
    ) -> List[ImprovementSuggestion]:
        suggestions: List[ImprovementSuggestion] = []
        sid = profile.strategy_id

        suggestions += self._from_degradation(sid, degradation)
        suggestions += self._from_adaptation(sid, adaptation)
        suggestions += self._from_knowledge(sid, knowledge)
        suggestions += self._from_profile(sid, profile)

        # Deduplicate by title
        seen: set = set()
        unique: List[ImprovementSuggestion] = []
        for s in suggestions:
            if s.title not in seen:
                seen.add(s.title)
                unique.append(s)
        return unique

    def _from_degradation(
        self, sid: str, report: Optional[DegradationReport]
    ) -> List[ImprovementSuggestion]:
        if not report or not report.is_actionable:
            return []
        suggestions: List[ImprovementSuggestion] = []

        if report.level in (DegradationLevel.SEVERE, DegradationLevel.CRITICAL):
            suggestions.append(ImprovementSuggestion(
                suggestion_id=str(uuid.uuid4()),
                strategy_id=sid,
                category="lifecycle",
                title="Consider strategy suspension pending review",
                description=(
                    f"Strategy exhibits {report.level.value} degradation "
                    f"(score: {report.degradation_score:.1f}/100). "
                    "Suspension reduces capital at risk while root cause is identified."
                ),
                rationale="Severe/critical degradation poses unacceptable ongoing risk.",
                evidence=[
                    f"Degradation level: {report.level.value}",
                    *[s.description for s in report.drift_signals if s.is_significant],
                ],
                expected_impact="high",
                is_reversible=True,
            ))
        elif report.level == DegradationLevel.MODERATE:
            suggestions.append(ImprovementSuggestion(
                suggestion_id=str(uuid.uuid4()),
                strategy_id=sid,
                category="risk",
                title="Reduce position size during degradation period",
                description=(
                    "Moderate degradation detected. Scaling down position size preserves "
                    "capital while allowing continued observation."
                ),
                rationale="Partial participation reduces downside during uncertain periods.",
                evidence=[f"Degradation score: {report.degradation_score:.1f}"],
                expected_impact="medium",
                is_reversible=True,
            ))

        if report.performance_degradation > 20.0:
            suggestions.append(ImprovementSuggestion(
                suggestion_id=str(uuid.uuid4()),
                strategy_id=sid,
                category="performance",
                title="Investigate entry/exit signal degradation",
                description=(
                    "Performance metrics have degraded significantly from baseline. "
                    "Review signal generation logic and recent market condition changes."
                ),
                rationale=f"Performance degradation: {report.performance_degradation:.1f}/100",
                evidence=[f"Performance degradation score: {report.performance_degradation:.1f}"],
                expected_impact="high",
            ))

        return suggestions

    def _from_adaptation(
        self, sid: str, report: Optional[AdaptationReport]
    ) -> List[ImprovementSuggestion]:
        if not report:
            return []
        suggestions: List[ImprovementSuggestion] = []

        if report.regime_result and report.regime_result.avoid_regimes:
            suggestions.append(ImprovementSuggestion(
                suggestion_id=str(uuid.uuid4()),
                strategy_id=sid,
                category="regime",
                title=f"Restrict deployment in: {', '.join(report.regime_result.avoid_regimes)}",
                description=(
                    "Historical performance in these regimes is consistently below threshold. "
                    "Restricting deployment preserves capital."
                ),
                rationale="Regime suitability analysis shows poor performance pattern.",
                evidence=[
                    f"Regime suitability: {r}={report.regime_result.regime_suitability.get(r, 0):.1f}"
                    for r in report.regime_result.avoid_regimes
                ],
                expected_impact="medium",
            ))

        if report.param_result and not report.param_result.is_stable:
            suggestions.append(ImprovementSuggestion(
                suggestion_id=str(uuid.uuid4()),
                strategy_id=sid,
                category="parameter",
                title="Schedule parameter review",
                description=(
                    "Parameter instability detected across multiple metrics. "
                    "A structured parameter review (backtesting team action) is recommended."
                ),
                rationale=f"Stability score: {report.param_result.overall_stability:.1f}/100",
                evidence=report.param_result.instability_drivers,
                expected_impact="medium",
            ))

        return suggestions

    def _from_knowledge(
        self, sid: str, report: Optional[KnowledgeReport]
    ) -> List[ImprovementSuggestion]:
        if not report or not report.has_actionable:
            return []
        suggestions: List[ImprovementSuggestion] = []

        for entry in report.failure_entries:
            if entry.severity == "severe":
                suggestions.append(ImprovementSuggestion(
                    suggestion_id=str(uuid.uuid4()),
                    strategy_id=sid,
                    category="performance",
                    title=f"Address severe failure: {entry.pattern_name}",
                    description=entry.remedy,
                    rationale=entry.description,
                    evidence=entry.evidence,
                    expected_impact="high",
                ))

        return suggestions

    def _from_profile(
        self, sid: str, profile: StrategyLearningProfile
    ) -> List[ImprovementSuggestion]:
        suggestions: List[ImprovementSuggestion] = []
        if profile.maturity_level == "nascent":
            suggestions.append(ImprovementSuggestion(
                suggestion_id=str(uuid.uuid4()),
                strategy_id=sid,
                category="lifecycle",
                title="Continue observation — insufficient data for conclusions",
                description=(
                    "Strategy has fewer than 10 observations. "
                    "At least 10-50 observations are needed before actionable learning can occur."
                ),
                rationale="Nascent strategies require time to accumulate learning signal.",
                evidence=[f"Observation count: {profile.observation_count}"],
                expected_impact="low",
                is_reversible=True,
            ))
        return suggestions
