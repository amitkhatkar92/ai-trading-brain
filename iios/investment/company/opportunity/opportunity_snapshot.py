"""iios/investment/company/opportunity/opportunity_snapshot.py
OpportunitySnapshot — primary output of the Company Opportunity Engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.company.opportunity.investment_thesis import InvestmentThesis
from iios.investment.company.opportunity.opportunity_profile import (
    AlertSeverity, ConfidenceLevel, ComponentScore, OpportunityAlert,
    OpportunityCategory, OpportunityLifecycle, OpportunityPriority,
    OpportunityScoreBreakdown, OpportunityStrength,
)
from iios.investment.company.opportunity.ranking_score import RankingResult


@dataclass
class OpportunitySnapshot:
    """
    Primary output of CompanyOpportunityEngine.evaluate().

    Contains the full evaluation result for a single company at a point in time.
    Consumed by the Decision Layer, Portfolio AI, and Strategy Intelligence.
    NOT a buy/sell/hold recommendation.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    ticker:          str
    opportunity_id:  str
    company_name:    Optional[str] = None
    sector:          Optional[str] = None
    industry:        Optional[str] = None
    exchange:        Optional[str] = None

    # ── Timing ────────────────────────────────────────────────────────────────
    generated_at:    datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    discovery_time:  Optional[datetime] = None

    # ── Classification ────────────────────────────────────────────────────────
    primary_category:    OpportunityCategory = OpportunityCategory.UNCLASSIFIED
    secondary_categories: List[OpportunityCategory] = field(default_factory=list)

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    lifecycle:  OpportunityLifecycle = OpportunityLifecycle.DISCOVERED
    priority:   OpportunityPriority  = OpportunityPriority.LOW

    # ── Scores ────────────────────────────────────────────────────────────────
    score_breakdown: Optional[OpportunityScoreBreakdown] = None
    overall_score:   float = 0.0
    strength:        OpportunityStrength = OpportunityStrength.UNKNOWN

    # ── Confidence ────────────────────────────────────────────────────────────
    confidence:        float = 0.0
    confidence_level:  ConfidenceLevel = ConfidenceLevel.VERY_LOW
    data_completeness: float = 0.0    # 0-1 fraction of available sources

    # ── Investment Thesis ─────────────────────────────────────────────────────
    thesis: Optional[InvestmentThesis] = None

    # ── Ranking ───────────────────────────────────────────────────────────────
    ranking: Optional[RankingResult] = None

    # ── Monitoring ────────────────────────────────────────────────────────────
    alerts: List[OpportunityAlert] = field(default_factory=list)

    # ── Metadata ──────────────────────────────────────────────────────────────
    data_sources:    List[str] = field(default_factory=list)
    evaluation_count: int = 0

    # ── Convenience properties ────────────────────────────────────────────────

    @property
    def opportunity_label(self) -> str:
        return self.strength.value

    @property
    def is_active(self) -> bool:
        return self.lifecycle not in (
            OpportunityLifecycle.EXPIRED, OpportunityLifecycle.ARCHIVED
        )

    @property
    def is_high_priority(self) -> bool:
        return self.priority in (OpportunityPriority.CRITICAL, OpportunityPriority.HIGH)

    @property
    def is_high_conviction(self) -> bool:
        return self.lifecycle in (
            OpportunityLifecycle.HIGH_CONVICTION, OpportunityLifecycle.CONFIRMED
        )

    @property
    def global_rank(self) -> Optional[int]:
        return self.ranking.global_rank if self.ranking else None

    @property
    def sector_rank(self) -> Optional[int]:
        return self.ranking.sector_rank if self.ranking else None

    @property
    def alert_messages(self) -> List[str]:
        return [a.message for a in self.alerts]

    @property
    def has_critical_alerts(self) -> bool:
        return any(a.severity == AlertSeverity.CRITICAL for a in self.alerts)

    @property
    def headline(self) -> str:
        return self.thesis.headline if self.thesis else f"{self.ticker} — under evaluation"

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker":            self.ticker,
            "opportunity_id":    self.opportunity_id,
            "company_name":      self.company_name,
            "sector":            self.sector,
            "industry":          self.industry,
            "exchange":          self.exchange,
            "generated_at":      self.generated_at.isoformat(),
            "discovery_time":    self.discovery_time.isoformat() if self.discovery_time else None,
            "primary_category":  self.primary_category.value,
            "secondary_categories": [c.value for c in self.secondary_categories],
            "lifecycle":         self.lifecycle.value,
            "priority":          self.priority.value,
            "overall_score":     round(self.overall_score, 2),
            "opportunity_label": self.opportunity_label,
            "confidence":        round(self.confidence, 3),
            "confidence_level":  self.confidence_level.value,
            "data_completeness": round(self.data_completeness, 3),
            "is_active":         self.is_active,
            "is_high_conviction": self.is_high_conviction,
            "is_high_priority":  self.is_high_priority,
            "global_rank":       self.global_rank,
            "sector_rank":       self.sector_rank,
            "headline":          self.headline,
            "score_breakdown":   self.score_breakdown.to_dict() if self.score_breakdown else None,
            "ranking":           self.ranking.to_dict() if self.ranking else None,
            "thesis":            self.thesis.to_dict() if self.thesis else None,
            "alerts":            [a.to_dict() for a in self.alerts],
            "data_sources":      self.data_sources,
            "evaluation_count":  self.evaluation_count,
        }
