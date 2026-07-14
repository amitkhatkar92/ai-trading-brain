"""iios/investment/strategy/integration/conflict_classifier.py
Classifies raw conflicts from rule failures into structured Conflict objects.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.integration.integration_constants import (
    ConflictSeverity,
    ConflictType,
    IntelligenceSource,
    ResolutionStrategy,
)
from iios.investment.strategy.integration.consistency_rules import RuleCheckResult


@dataclass
class Conflict:
    """A classified, actionable conflict between two intelligence sources."""
    conflict_id:         str
    strategy_id:         str
    conflict_type:       ConflictType
    severity:            ConflictSeverity
    source_a:            IntelligenceSource
    source_b:            IntelligenceSource
    description:         str
    rule_id:             str
    resolution_strategy: ResolutionStrategy
    is_resolved:         bool               = False
    resolution_notes:    str                = ""
    detected_at:         datetime           = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at:         Optional[datetime] = None

    def resolve(self, notes: str = "") -> None:
        self.is_resolved    = True
        self.resolved_at    = datetime.now(timezone.utc)
        self.resolution_notes = notes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_id":         self.conflict_id,
            "strategy_id":         self.strategy_id,
            "conflict_type":       self.conflict_type.value,
            "severity":            self.severity.value,
            "source_a":            self.source_a.value,
            "source_b":            self.source_b.value,
            "description":         self.description,
            "rule_id":             self.rule_id,
            "resolution_strategy": self.resolution_strategy.value,
            "is_resolved":         self.is_resolved,
            "resolution_notes":    self.resolution_notes,
            "detected_at":         self.detected_at.isoformat(),
            "resolved_at":         self.resolved_at.isoformat() if self.resolved_at else None,
        }


# Default resolution strategies per conflict type
_DEFAULT_RESOLUTION: Dict[ConflictType, ResolutionStrategy] = {
    ConflictType.EVALUATION_VS_RISK:       ResolutionStrategy.RISK_FIRST,
    ConflictType.OPPORTUNITY_VS_PORTFOLIO: ResolutionStrategy.CONSERVATIVE,
    ConflictType.LEARNING_VS_EVALUATION:   ResolutionStrategy.MOST_RECENT,
    ConflictType.DEBATE_VS_RISK:           ResolutionStrategy.RISK_FIRST,
    ConflictType.MIGRATION_VS_EVALUATION:  ResolutionStrategy.MOST_RECENT,
    ConflictType.PORTFOLIO_VS_OPPORTUNITY: ResolutionStrategy.CONSERVATIVE,
    ConflictType.LIFECYCLE_VS_EVALUATION:  ResolutionStrategy.MOST_RECENT,
    ConflictType.CROSS_ENGINE:             ResolutionStrategy.HIGHER_CONFIDENCE,
}


class ConflictClassifier:
    """Classifies failed RuleCheckResults into Conflict objects."""

    def classify(
        self,
        strategy_id: str,
        failures:    List[RuleCheckResult],
    ) -> List[Conflict]:
        conflicts = []
        for r in failures:
            if r.passed or r.conflict_type is None:
                continue
            res_strategy = _DEFAULT_RESOLUTION.get(
                r.conflict_type, ResolutionStrategy.HIGHER_CONFIDENCE
            )
            conflicts.append(Conflict(
                conflict_id=str(uuid.uuid4()),
                strategy_id=strategy_id,
                conflict_type=r.conflict_type,
                severity=r.severity or ConflictSeverity.LOW,
                source_a=r.source_a or IntelligenceSource.STRATEGY_FRAMEWORK,
                source_b=r.source_b or IntelligenceSource.STRATEGY_FRAMEWORK,
                description=r.description,
                rule_id=r.rule_id,
                resolution_strategy=res_strategy,
            ))
        return conflicts
