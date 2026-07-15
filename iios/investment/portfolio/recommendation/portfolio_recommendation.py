"""iios/investment/portfolio/recommendation/portfolio_recommendation.py

PortfolioRecommendation — the primary output of the Recommendation Engine.
RecommendationCandidate — internal working type.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.recommendation.recommendation_types import (
    LifecycleState, RecommendationAction, RecommendationGrade,
    RecommendationLevel, RecommendationPriority, RecommendationRisk,
    RecommendationStatus, action_to_category,
    recommendation_score_to_grade, recommendation_score_to_level, now_utc,
)


@dataclass(frozen=True)
class RecommendationCandidate:
    """
    Internal type produced by RecommendationLogic.
    Not exposed to callers — converted to PortfolioRecommendation before publication.
    """

    action:          RecommendationAction        = RecommendationAction.NO_ACTION
    priority:        RecommendationPriority      = RecommendationPriority.LOW
    confidence:      float                       = 0.5
    rationale:       str                         = ""
    evidence:        tuple                       = field(default_factory=tuple)  # str
    triggered_rule:  str                         = ""
    risk_level:      RecommendationRisk          = RecommendationRisk.LOW
    tags:            tuple                       = field(default_factory=tuple)  # str


@dataclass(frozen=True)
class PortfolioRecommendation:
    """
    Complete, auditable portfolio recommendation.

    This is the canonical output of PortfolioRecommendationEngine.evaluate().
    Does NOT contain trade execution logic.
    Every field is immutable and version-controlled.
    """

    recommendation_id:      str                  = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:           str                  = ""
    version:                int                  = 1
    created_at:             str                  = field(default_factory=now_utc)
    updated_at:             str                  = field(default_factory=now_utc)

    # Core recommendation
    action:                 RecommendationAction = RecommendationAction.NO_ACTION
    priority:               RecommendationPriority = RecommendationPriority.INFORMATIONAL
    confidence:             float                = 0.5
    risk_level:             RecommendationRisk   = RecommendationRisk.LOW

    # Lifecycle
    status:                 RecommendationStatus = RecommendationStatus.DRAFT
    lifecycle_state:        LifecycleState       = LifecycleState.CREATED

    # Expiration
    expires_at:             str                  = ""
    expiry_hours:           float                = 24.0

    # Rationale and evidence
    rationale:              str                  = ""
    supporting_evidence:    tuple                = field(default_factory=tuple)  # str
    triggered_rules:        tuple                = field(default_factory=tuple)  # str

    # Source traceability
    policy_id:              str                  = ""
    policy_name:            str                  = ""
    intelligence_id:        str                  = ""   # links to PortfolioIntelligence snapshot

    # Quality
    recommendation_score:   float                = 0.5
    grade:                  RecommendationGrade  = RecommendationGrade.C
    level:                  RecommendationLevel  = RecommendationLevel.AVERAGE

    # Flags
    is_actionable:          bool                 = True
    requires_approval:      bool                 = False
    is_time_sensitive:      bool                 = False

    # Classification
    category:               str                  = ""   # risk / allocation / diversification / quality / governance
    tags:                   tuple                = field(default_factory=tuple)  # str

    # Metadata
    metadata:               Optional[Dict[str, Any]] = None

    # ---- Computed properties ----

    @property
    def is_active(self) -> bool:
        return self.lifecycle_state in (
            LifecycleState.PUBLISHED,
            LifecycleState.ACTIVE,
            LifecycleState.MONITORING,
        )

    @property
    def is_terminal(self) -> bool:
        return self.lifecycle_state in (
            LifecycleState.EXPIRED,
            LifecycleState.WITHDRAWN,
            LifecycleState.ARCHIVED,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendation_id":    self.recommendation_id,
            "portfolio_id":         self.portfolio_id,
            "version":              self.version,
            "created_at":           self.created_at,
            "action":               self.action.value,
            "priority":             self.priority.value,
            "confidence":           round(self.confidence, 4),
            "risk_level":           self.risk_level.value,
            "status":               self.status.value,
            "lifecycle_state":      self.lifecycle_state.value,
            "expires_at":           self.expires_at,
            "rationale":            self.rationale,
            "policy_id":            self.policy_id,
            "recommendation_score": round(self.recommendation_score, 4),
            "grade":                self.grade.value,
            "is_actionable":        self.is_actionable,
            "requires_approval":    self.requires_approval,
            "category":             self.category,
            "tags":                 list(self.tags),
        }


def build_recommendation(
    candidate:        RecommendationCandidate,
    portfolio_id:     str,
    policy_id:        str,
    policy_name:      str,
    intelligence_id:  str,
    score:            float,
    expires_at:       str,
    expiry_hours:     float,
    requires_approval:bool = False,
    is_time_sensitive:bool = False,
) -> PortfolioRecommendation:
    """Construct a PortfolioRecommendation from a candidate."""
    return PortfolioRecommendation(
        portfolio_id         = portfolio_id,
        action               = candidate.action,
        priority             = candidate.priority,
        confidence           = round(candidate.confidence, 4),
        risk_level           = candidate.risk_level,
        status               = RecommendationStatus.DRAFT,
        lifecycle_state      = LifecycleState.CREATED,
        expires_at           = expires_at,
        expiry_hours         = expiry_hours,
        rationale            = candidate.rationale,
        supporting_evidence  = candidate.evidence,
        triggered_rules      = (candidate.triggered_rule,) if candidate.triggered_rule else (),
        policy_id            = policy_id,
        policy_name          = policy_name,
        intelligence_id      = intelligence_id,
        recommendation_score = round(score, 4),
        grade                = recommendation_score_to_grade(score),
        level                = recommendation_score_to_level(score),
        is_actionable        = candidate.action != RecommendationAction.NO_ACTION,
        requires_approval    = requires_approval,
        is_time_sensitive    = is_time_sensitive,
        category             = action_to_category(candidate.action),
        tags                 = candidate.tags,
    )
