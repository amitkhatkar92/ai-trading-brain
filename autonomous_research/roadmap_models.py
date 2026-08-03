"""
roadmap_models.py — Typed models for the ARS RoadmapManager.

ARS Phase 2B.

Pure data.  No business logic.  All fields serialisable for JSON round-trip.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .gap_models import GapCategory, GapSeverity


# ─── enumerations ─────────────────────────────────────────────────────────────

class StudyCategory(str, Enum):
    """Research portfolio categories.  Designed for future extension."""
    WINNER_DNA      = "WINNER_DNA"
    MARKET_REGIMES  = "MARKET_REGIMES"
    SECTOR_RESEARCH = "SECTOR_RESEARCH"
    VALIDATION      = "VALIDATION"
    RISK            = "RISK"
    EXPLORATION     = "EXPLORATION"


class RoadmapEntryStatus(str, Enum):
    PENDING  = "PENDING"
    DEFERRED = "DEFERRED"


# ─── knowledge gain estimate ──────────────────────────────────────────────────

@dataclass
class KnowledgeGainEstimate:
    """
    Estimated scientific knowledge gain from addressing a gap.

    Formula (all weights documented in breakdown):
        raw_gain = (
            scientific_importance            * 0.25
            + evidence_gap_size              * 0.20
            + expected_confidence_improvement * 0.20
            + coverage_increase              * 0.15
            + novelty                        * 0.10
            + reuse_potential                * 0.10
        )
        adjusted   = raw_gain * (1 + uncertainty_reduction * 0.15)
        final      = adjusted * (0.70 + historical_impact  * 0.30)
        total_gain = clamp(final, 0.0, 1.0)
    """
    gap_id:                           str
    scientific_importance:            float   # 0.0–1.0, from gap severity
    evidence_gap_size:                float   # 0.0–1.0, from gap category
    current_confidence:               float   # 0.0–1.0, from gap.confidence
    expected_confidence_improvement:  float   # 0.0–1.0, from gap category
    expected_new_findings:            int     # estimated number of new findings
    coverage_increase:                float   # 0.0–1.0, regime/sector expansion
    novelty:                          float   # 0.0–1.0, how new is this territory
    historical_impact:                float   # 0.0–1.0, proxy from gap.estimated_knowledge_gain
    reuse_potential:                  float   # 0.0–1.0, how reusable findings will be
    uncertainty_reduction:            float   # 0.0–1.0, expected uncertainty removed
    total_gain:                       float   # 0.0–1.0, final computed gain
    breakdown:                        Dict[str, float]  # all components documented

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gap_id":                           self.gap_id,
            "scientific_importance":            self.scientific_importance,
            "evidence_gap_size":                self.evidence_gap_size,
            "current_confidence":               self.current_confidence,
            "expected_confidence_improvement":  self.expected_confidence_improvement,
            "expected_new_findings":            self.expected_new_findings,
            "coverage_increase":                self.coverage_increase,
            "novelty":                          self.novelty,
            "historical_impact":                self.historical_impact,
            "reuse_potential":                  self.reuse_potential,
            "uncertainty_reduction":            self.uncertainty_reduction,
            "total_gain":                       self.total_gain,
            "breakdown":                        self.breakdown,
        }


# ─── research cost estimate ───────────────────────────────────────────────────

@dataclass
class ResearchCostEstimate:
    """
    Estimated cost of addressing a gap.

    Formula (all weights documented in breakdown):
        replay_factor = min(1.0, replay_duration_hours / 8.0)
        total_cost    = (
            implementation_effort * 0.40
            + risk                * 0.30
            + replay_factor       * 0.30
        )
    """
    gap_id:                         str
    historical_days_required:       int    # data lookback window
    replay_duration_estimate_hours: float  # expected compute time
    implementation_effort:          float  # 0.0–1.0 relative effort
    dependencies:                   List[str]   # IDs that should resolve first
    risk:                           float  # 0.0–1.0 execution risk
    total_cost:                     float  # 0.0–1.0 normalized cost
    breakdown:                      Dict[str, Any]  # formula documented

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gap_id":                         self.gap_id,
            "historical_days_required":       self.historical_days_required,
            "replay_duration_estimate_hours": self.replay_duration_estimate_hours,
            "implementation_effort":          self.implementation_effort,
            "dependencies":                   self.dependencies,
            "risk":                           self.risk,
            "total_cost":                     self.total_cost,
            "breakdown":                      self.breakdown,
        }


# ─── research debt ────────────────────────────────────────────────────────────

@dataclass
class ResearchDebt:
    """
    Accumulated research debt for a knowledge gap.

    Debt components:
        base_debt          — from gap severity (CRITICAL→1.0 … LOW→0.25)
        age_debt           — days since first observed / debt_half_life_days, capped 1.0
        contradiction_debt — extra 0.30 for CONTRADICTION_GAP (unresolved conflict)
        expiry_debt        — extra 0.20 for TEMPORAL_GAP (knowledge staleness)

    Total (all weights documented in breakdown):
        total_debt = clamp(
            base_debt          * 0.50
            + age_debt         * 0.30
            + contradiction_debt * 0.10
            + expiry_debt      * 0.10,
            0.0, 1.0
        )
    """
    gap_id:                 str
    category:               GapCategory
    severity:               GapSeverity
    base_debt:              float   # from severity
    age_debt:               float   # from time elapsed since first seen
    contradiction_debt:     float   # extra for CONTRADICTION_GAP
    expiry_debt:            float   # extra for TEMPORAL_GAP
    total_debt:             float   # 0.0–1.0 final computed debt
    accumulation_rationale: str     # human-readable explanation
    breakdown:              Dict[str, float]  # weights documented

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gap_id":                 self.gap_id,
            "category":               self.category.value,
            "severity":               self.severity.value,
            "base_debt":              self.base_debt,
            "age_debt":               self.age_debt,
            "contradiction_debt":     self.contradiction_debt,
            "expiry_debt":            self.expiry_debt,
            "total_debt":             self.total_debt,
            "accumulation_rationale": self.accumulation_rationale,
            "breakdown":              self.breakdown,
        }


# ─── roadmap entry ────────────────────────────────────────────────────────────

@dataclass
class RoadmapEntry:
    """
    A single prioritized entry in the research roadmap.

    Priority formula (weights from RoadmapManagerConfig, documented in breakdown):
        priority = (
            knowledge_gain  * w_knowledge_gain
            + research_debt * w_research_debt
            + sci_importance * w_scientific_importance
            + (1 - cost)    * w_cost_efficiency
            + urgency       * w_urgency
        ) / sum_weights
    """
    entry_id:                str               # RE-{sha256(gap_id)[:8]}
    gap:                     "KnowledgeGap"    # forward reference — same package
    knowledge_gain_estimate: KnowledgeGainEstimate
    cost_estimate:           ResearchCostEstimate
    debt:                    ResearchDebt
    priority_score:          float             # 0.0–1.0
    priority_breakdown:      Dict[str, Any]    # formula and weights documented
    study_category:          StudyCategory
    status:                  RoadmapEntryStatus
    rank:                    int               # 1-based; 1 = highest priority
    recommended_study_title: str
    recommended_approach:    str
    created_at:              datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id":                self.entry_id,
            "gap_id":                  self.gap.gap_id,
            "gap_title":               self.gap.title,
            "gap_category":            self.gap.category.value,
            "gap_severity":            self.gap.severity.value,
            "knowledge_gain_estimate": self.knowledge_gain_estimate.to_dict(),
            "cost_estimate":           self.cost_estimate.to_dict(),
            "debt":                    self.debt.to_dict(),
            "priority_score":          self.priority_score,
            "priority_breakdown":      self.priority_breakdown,
            "study_category":          self.study_category.value,
            "status":                  self.status.value,
            "rank":                    self.rank,
            "recommended_study_title": self.recommended_study_title,
            "recommended_approach":    self.recommended_approach,
            "created_at":              self.created_at.isoformat(),
        }


# ─── portfolio ────────────────────────────────────────────────────────────────

@dataclass
class ResearchPortfolio:
    """Balanced research allocation across study categories."""
    total_entries:          int
    allocation:             Dict[str, int]    # StudyCategory.value → count
    target_allocation:      Dict[str, float]  # StudyCategory.value → target fraction
    actual_fraction:        Dict[str, float]  # StudyCategory.value → actual fraction
    balance_score:          float             # 0.0–1.0: portfolio balance quality
    imbalanced_categories:  List[str]         # categories > threshold off-target
    recommendations:        List[str]         # rebalancing suggestions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_entries":         self.total_entries,
            "allocation":            self.allocation,
            "target_allocation":     self.target_allocation,
            "actual_fraction":       self.actual_fraction,
            "balance_score":         self.balance_score,
            "imbalanced_categories": self.imbalanced_categories,
            "recommendations":       self.recommendations,
        }


# ─── statistics ───────────────────────────────────────────────────────────────

@dataclass
class RoadmapStatistics:
    total_entries:          int
    pending_entries:        int
    avg_priority_score:     float
    avg_knowledge_gain:     float
    avg_cost:               float
    avg_debt:               float
    by_gap_category:        Dict[str, int]    # GapCategory.value → count
    by_severity:            Dict[str, int]    # GapSeverity.value → count
    by_study_category:      Dict[str, int]    # StudyCategory.value → count
    top_priority_entry_id:  Optional[str]
    total_research_debt:    float
    build_duration_ms:      float
    built_at:               datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_entries":         self.total_entries,
            "pending_entries":       self.pending_entries,
            "avg_priority_score":    self.avg_priority_score,
            "avg_knowledge_gain":    self.avg_knowledge_gain,
            "avg_cost":              self.avg_cost,
            "avg_debt":              self.avg_debt,
            "by_gap_category":       self.by_gap_category,
            "by_severity":           self.by_severity,
            "by_study_category":     self.by_study_category,
            "top_priority_entry_id": self.top_priority_entry_id,
            "total_research_debt":   self.total_research_debt,
            "build_duration_ms":     self.build_duration_ms,
            "built_at":              self.built_at.isoformat(),
        }


# ─── roadmap ──────────────────────────────────────────────────────────────────

@dataclass
class ResearchRoadmap:
    roadmap_id: str
    built_at:   datetime
    entries:    List[RoadmapEntry]    # sorted by rank (rank=1 is highest priority)
    portfolio:  ResearchPortfolio
    statistics: RoadmapStatistics
    warnings:   List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "roadmap_id": self.roadmap_id,
            "built_at":   self.built_at.isoformat(),
            "entries":    [e.to_dict() for e in self.entries],
            "portfolio":  self.portfolio.to_dict(),
            "statistics": self.statistics.to_dict(),
            "warnings":   self.warnings,
        }


# ─── configuration ────────────────────────────────────────────────────────────

@dataclass
class RoadmapManagerConfig:
    """
    All RoadmapManager configuration in one place.

    ┌──────────────────────────────────────────────────────────────────────┐
    │ Priority formula                                                     │
    │                                                                      │
    │   priority = (                                                       │
    │     knowledge_gain       * w_knowledge_gain                         │
    │     + research_debt      * w_research_debt                          │
    │     + sci_importance     * w_scientific_importance                  │
    │     + (1 - cost)         * w_cost_efficiency                        │
    │     + urgency            * w_urgency                                │
    │   ) / (sum of all weights)                                          │
    │                                                                      │
    │   All weights are normalized internally.                            │
    └──────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────────────────────────────────────────────────────┐
    │ Portfolio allocation                                                  │
    │   Keys must be StudyCategory.value strings.                         │
    │   Sum of values should be ≤ 1.0.                                   │
    └──────────────────────────────────────────────────────────────────────┘
    """
    # Priority score weights (normalized to sum before use)
    w_knowledge_gain:        float = 0.30
    w_research_debt:         float = 0.25
    w_scientific_importance: float = 0.25
    w_cost_efficiency:       float = 0.10
    w_urgency:               float = 0.10

    # Research debt: age_debt reaches 1.0 after this many days
    debt_half_life_days: int = 90

    # Portfolio allocation targets (StudyCategory.value → fraction)
    portfolio_allocation: Dict[str, float] = field(default_factory=lambda: {
        "WINNER_DNA":      0.20,
        "MARKET_REGIMES":  0.25,
        "SECTOR_RESEARCH": 0.15,
        "VALIDATION":      0.20,
        "RISK":            0.10,
        "EXPLORATION":     0.10,
    })

    # Categories more than this fraction off-target are flagged as imbalanced
    portfolio_imbalance_threshold: float = 0.10

    # Default count for top_priorities()
    default_top_n: int = 5


# ─── exceptions ───────────────────────────────────────────────────────────────

class RoadmapManagerError(Exception):
    """Base exception for RoadmapManager."""


class RoadmapBuildError(RoadmapManagerError):
    """Raised when the roadmap cannot be built."""
