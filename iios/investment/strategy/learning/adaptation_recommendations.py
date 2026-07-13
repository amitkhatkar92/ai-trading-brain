"""iios/investment/strategy/learning/adaptation_recommendations.py
AdaptationRecommendation — recommendations derived from regime and parameter adaptation analysis.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.learning.regime_adaptation import RegimeAdaptationResult
from iios.investment.strategy.learning.parameter_analysis import ParameterStabilityResult


@dataclass(frozen=True)
class AdaptationRecommendation:
    """A single, auditable, reversible adaptation recommendation."""
    rec_id:      str
    strategy_id: str
    category:    str    # "regime" | "parameter" | "exposure"
    priority:    str    # "HIGH" | "MEDIUM" | "LOW"
    title:       str
    rationale:   str
    evidence:    List[str]
    is_reversible: bool = True
    created_at:  datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rec_id":       self.rec_id,
            "strategy_id":  self.strategy_id,
            "category":     self.category,
            "priority":     self.priority,
            "title":        self.title,
            "rationale":    self.rationale,
            "evidence":     self.evidence,
            "is_reversible": self.is_reversible,
            "created_at":   self.created_at.isoformat(),
        }


def generate_adaptation_recommendations(
    strategy_id: str,
    regime_result: Optional[RegimeAdaptationResult],
    param_result:  Optional[ParameterStabilityResult],
) -> List[AdaptationRecommendation]:
    """
    Generate adaptation recommendations from regime and parameter analyses.
    Returns an empty list if no actionable findings exist.
    """
    recs: List[AdaptationRecommendation] = []

    if regime_result:
        # High mismatch rate
        if regime_result.mismatch_rate > 0.30:
            recs.append(AdaptationRecommendation(
                rec_id=str(uuid.uuid4()),
                strategy_id=strategy_id,
                category="regime",
                priority="HIGH",
                title="Reduce regime-mismatch deployments",
                rationale=(
                    f"Strategy is deployed in unsupported regimes {regime_result.mismatch_rate:.0%} of the time, "
                    "creating avoidable performance drag."
                ),
                evidence=[
                    f"Mismatch rate: {regime_result.mismatch_rate:.1%}",
                    f"Worst performing regime: {regime_result.worst_regime}",
                ],
            ))

        # Regimes to avoid
        if regime_result.avoid_regimes:
            recs.append(AdaptationRecommendation(
                rec_id=str(uuid.uuid4()),
                strategy_id=strategy_id,
                category="regime",
                priority="MEDIUM",
                title=f"Avoid or limit exposure in: {', '.join(regime_result.avoid_regimes)}",
                rationale="Historical performance in these regimes is consistently below threshold.",
                evidence=[
                    f"{r}: {regime_result.regime_suitability.get(r, 0):.1f}/100 suitability"
                    for r in regime_result.avoid_regimes
                ],
            ))

        # Untested regimes (supported but not yet observed)
        if regime_result.regimes_not_seen:
            recs.append(AdaptationRecommendation(
                rec_id=str(uuid.uuid4()),
                strategy_id=strategy_id,
                category="regime",
                priority="LOW",
                title=f"Test in unseen regimes: {', '.join(regime_result.regimes_not_seen)}",
                rationale="These regimes are listed as supported but have not been observed yet.",
                evidence=[f"Unseen: {r}" for r in regime_result.regimes_not_seen],
            ))

        # Low adaptability
        if regime_result.adaptability_score < 40.0:
            recs.append(AdaptationRecommendation(
                rec_id=str(uuid.uuid4()),
                strategy_id=strategy_id,
                category="regime",
                priority="HIGH",
                title="Strategy shows limited regime adaptability",
                rationale=(
                    f"Adaptability score of {regime_result.adaptability_score:.1f}/100 suggests "
                    "the strategy is concentrated in a narrow set of market conditions."
                ),
                evidence=[
                    f"Regime breadth: {regime_result.regime_breadth:.1f}%",
                    f"Best regime: {regime_result.best_regime} ({regime_result.regime_suitability.get(regime_result.best_regime, 0):.1f}/100)",
                ],
            ))

    if param_result and not param_result.is_stable:
        recs.append(AdaptationRecommendation(
            rec_id=str(uuid.uuid4()),
            strategy_id=strategy_id,
            category="parameter",
            priority="HIGH",
            title="Unstable strategy parameters detected",
            rationale=(
                f"Overall parameter stability score of {param_result.overall_stability:.1f}/100 "
                "suggests the strategy's observable metrics are drifting inconsistently."
            ),
            evidence=param_result.instability_drivers,
        ))

    return recs
