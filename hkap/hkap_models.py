"""
hkap_models.py — Pure data models for HKAP-001 Historical Knowledge Acquisition Program.

All fields are JSON-serialisable.  No business logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ── enumerations ───────────────────────────────────────────────────────────────

class YearStudyStatus(str, Enum):
    PENDING  = "PENDING"
    RUNNING  = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED   = "FAILED"
    SKIPPED  = "SKIPPED"


class DNALifecycleLabel(str, Enum):
    STABLE        = "STABLE"         # present ≥75% of observed years
    STRENGTHENING = "STRENGTHENING"  # rising confidence trend
    WEAKENING     = "WEAKENING"      # declining confidence trend
    EMERGING      = "EMERGING"       # appeared in last 1-2 years only
    DISAPPEARING  = "DISAPPEARING"   # absent for last 2+ years
    SPORADIC      = "SPORADIC"       # intermittent, no clear trend


class RegimeDependency(str, Enum):
    REGIME_SPECIFIC     = "REGIME_SPECIFIC"      # only in certain regimes
    REGIME_INDEPENDENT  = "REGIME_INDEPENDENT"   # present across all regimes
    MULTI_REGIME        = "MULTI_REGIME"         # present in 2–3 of 4 regimes


# ── errors ────────────────────────────────────────────────────────────────────

class HKAPError(Exception):
    """Base HKAP error."""


class FutureDataLeakError(HKAPError):
    """Raised when a year attempts to access future-year data."""

    def __init__(self, requesting_year: int, future_year: int) -> None:
        self.requesting_year = requesting_year
        self.future_year     = future_year
        super().__init__(
            f"Year {requesting_year} attempted to access year {future_year} — "
            "future data leak prevented."
        )


class YearNotCompleteError(HKAPError):
    """Raised when a year's pipeline is accessed before completion."""

    def __init__(self, year: int) -> None:
        self.year = year
        super().__init__(f"Year {year} is not yet complete.")


# ── market profile ─────────────────────────────────────────────────────────────

@dataclass
class YearMarketProfile:
    year:                       int
    regime_distribution:        Dict[str, float]   # regime → fraction of trading days
    dominant_regime:            str
    volatility_level:           str                # LOW / MEDIUM / HIGH / EXTREME
    sector_leaders:             List[str]          # top 3 sectors by annual return
    sector_rotations:           List[str]          # key rotation events
    breadth_score:              float              # avg % advancing stocks (0-1)
    momentum_strength:          float              # 0-1
    mean_reversion_strength:    float              # 0-1
    institutional_activity:     float              # 0-1 inferred from volume patterns
    market_personality:         str                # e.g. TRENDING_BULL
    behaviour_clusters:         List[str]          # descriptive cluster labels
    key_observations:           List[str]          # 3-5 notable market facts
    index_return_ytd:           float              # NIFTY50 calendar-year return
    peak_drawdown:              float              # max drawdown from YTD peak
    trading_days:               int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "year":                    self.year,
            "regime_distribution":     self.regime_distribution,
            "dominant_regime":         self.dominant_regime,
            "volatility_level":        self.volatility_level,
            "sector_leaders":          self.sector_leaders,
            "sector_rotations":        self.sector_rotations,
            "breadth_score":           self.breadth_score,
            "momentum_strength":       self.momentum_strength,
            "mean_reversion_strength": self.mean_reversion_strength,
            "institutional_activity":  self.institutional_activity,
            "market_personality":      self.market_personality,
            "behaviour_clusters":      self.behaviour_clusters,
            "key_observations":        self.key_observations,
            "index_return_ytd":        self.index_return_ytd,
            "peak_drawdown":           self.peak_drawdown,
            "trading_days":            self.trading_days,
        }


# ── DNA snapshot ──────────────────────────────────────────────────────────────

@dataclass
class YearDNASnapshot:
    year:                   int
    winner_dna:             List[str]          # DNA IDs (feature_name + direction)
    loser_dna:              List[str]
    neutral_dna:            List[str]
    regime_specific_dna:    Dict[str, List[str]]  # regime → [dna_ids]
    regime_independent_dna: List[str]
    total_discovered:       int
    high_confidence_count:  int                # confidence ≥ edge_threshold
    median_confidence:      float
    confidence_by_id:       Dict[str, float]   # dna_id → confidence
    source_db:              str                # path to year's IDR

    def to_dict(self) -> Dict[str, Any]:
        return {
            "year":                    self.year,
            "winner_dna":              self.winner_dna,
            "loser_dna":               self.loser_dna,
            "neutral_dna":             self.neutral_dna,
            "regime_specific_dna":     self.regime_specific_dna,
            "regime_independent_dna":  self.regime_independent_dna,
            "total_discovered":        self.total_discovered,
            "high_confidence_count":   self.high_confidence_count,
            "median_confidence":       self.median_confidence,
            "confidence_by_id":        self.confidence_by_id,
            "source_db":               self.source_db,
        }


# ── edge snapshot ─────────────────────────────────────────────────────────────

@dataclass
class YearEdgeSnapshot:
    year:                int
    active_edges:        List[str]   # DNA IDs with confidence ≥ edge_threshold
    promoted_this_year:  List[str]   # new high-confidence vs prior year
    demoted_this_year:   List[str]   # dropped below threshold vs prior year
    retired_this_year:   List[str]   # completely absent vs prior year
    survival_rate:       float       # % of prior-year edges still active
    new_edge_rate:       float       # % of active edges that are new this year
    total_prior_edges:   int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "year":               self.year,
            "active_edges":       self.active_edges,
            "promoted_this_year": self.promoted_this_year,
            "demoted_this_year":  self.demoted_this_year,
            "retired_this_year":  self.retired_this_year,
            "survival_rate":      self.survival_rate,
            "new_edge_rate":      self.new_edge_rate,
            "total_prior_edges":  self.total_prior_edges,
        }


# ── SD year review ────────────────────────────────────────────────────────────

@dataclass
class YearSDReview:
    year:                int
    review_id:           str
    health:              str
    observations:        List[str]
    reasoning:           str
    lessons_learned:     List[str]
    remaining_questions: List[str]
    recommended_study:   str
    confidence:          float
    generated_at:        str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "year":                self.year,
            "review_id":           self.review_id,
            "health":              self.health,
            "observations":        self.observations,
            "reasoning":           self.reasoning,
            "lessons_learned":     self.lessons_learned,
            "remaining_questions": self.remaining_questions,
            "recommended_study":   self.recommended_study,
            "confidence":          self.confidence,
            "generated_at":        self.generated_at,
        }


# ── year knowledge package ────────────────────────────────────────────────────

@dataclass
class YearKnowledgePackage:
    year:                   int
    status:                 str                    # YearStudyStatus value
    market_profile:         Optional[YearMarketProfile]
    dna_snapshot:           Optional[YearDNASnapshot]
    edge_snapshot:          Optional[YearEdgeSnapshot]
    sd_review:              Optional[YearSDReview]
    prior_years_context:    List[int]
    trading_days_analyzed:  int
    universe_size:          int
    completed_at:           str
    reports:                List[str]
    stage_statuses:         Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "year":                  self.year,
            "status":                self.status,
            "market_profile":        self.market_profile.to_dict() if self.market_profile else None,
            "dna_snapshot":          self.dna_snapshot.to_dict() if self.dna_snapshot else None,
            "edge_snapshot":         self.edge_snapshot.to_dict() if self.edge_snapshot else None,
            "sd_review":             self.sd_review.to_dict() if self.sd_review else None,
            "prior_years_context":   self.prior_years_context,
            "trading_days_analyzed": self.trading_days_analyzed,
            "universe_size":         self.universe_size,
            "completed_at":          self.completed_at,
            "reports":               self.reports,
            "stage_statuses":        self.stage_statuses,
        }


# ── cross-year records ────────────────────────────────────────────────────────

@dataclass
class CrossYearDNARecord:
    dna_id:            str
    feature_name:      str
    direction:         str
    years_present:     List[int]
    years_absent:      List[int]
    confidence_by_year: Dict[int, float]   # year → confidence
    regimes_observed:  List[str]           # regimes where this DNA appeared
    lifecycle_label:   str                 # DNALifecycleLabel value
    regime_dependency: str                 # RegimeDependency value
    survival_score:    float               # fraction of covered years present
    confidence_trend:  str                 # RISING / FALLING / STABLE / VOLATILE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dna_id":             self.dna_id,
            "feature_name":       self.feature_name,
            "direction":          self.direction,
            "years_present":      self.years_present,
            "years_absent":       self.years_absent,
            "confidence_by_year": {str(k): v for k, v in self.confidence_by_year.items()},
            "regimes_observed":   self.regimes_observed,
            "lifecycle_label":    self.lifecycle_label,
            "regime_dependency":  self.regime_dependency,
            "survival_score":     self.survival_score,
            "confidence_trend":   self.confidence_trend,
        }


@dataclass
class CrossYearEdgeRecord:
    edge_id:              str
    feature_name:         str
    years_active:         List[int]
    years_inactive:       List[int]
    lifecycle_label:      str
    peak_confidence_year: int
    peak_confidence:      float
    trend:                str    # STRENGTHENING / WEAKENING / STABLE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edge_id":              self.edge_id,
            "feature_name":         self.feature_name,
            "years_active":         self.years_active,
            "years_inactive":       self.years_inactive,
            "lifecycle_label":      self.lifecycle_label,
            "peak_confidence_year": self.peak_confidence_year,
            "peak_confidence":      self.peak_confidence,
            "trend":                self.trend,
        }


# ── program-level status and summary ─────────────────────────────────────────

@dataclass
class HKAPStatus:
    years_planned:         List[int]
    years_completed:       List[int]
    years_failed:          List[int]
    years_pending:         List[int]
    current_year:          Optional[int]
    is_synthesis_done:     bool
    total_dna_accumulated: int
    last_updated:          str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "years_planned":          self.years_planned,
            "years_completed":        self.years_completed,
            "years_failed":           self.years_failed,
            "years_pending":          self.years_pending,
            "current_year":           self.current_year,
            "is_synthesis_done":      self.is_synthesis_done,
            "total_dna_accumulated":  self.total_dna_accumulated,
            "last_updated":           self.last_updated,
        }


@dataclass
class HKAPSummary:
    years_planned:          List[int]
    years_completed:        List[int]
    years_failed:           List[int]
    total_dna_discovered:   int
    stable_dna_count:       int
    emerging_dna_count:     int
    disappearing_dna_count: int
    stable_edges_count:     int
    regime_specific_count:  int
    regime_independent_count: int
    synthesis_reports:      List[str]
    generated_at:           str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "years_planned":           self.years_planned,
            "years_completed":         self.years_completed,
            "years_failed":            self.years_failed,
            "total_dna_discovered":    self.total_dna_discovered,
            "stable_dna_count":        self.stable_dna_count,
            "emerging_dna_count":      self.emerging_dna_count,
            "disappearing_dna_count":  self.disappearing_dna_count,
            "stable_edges_count":      self.stable_edges_count,
            "regime_specific_count":   self.regime_specific_count,
            "regime_independent_count": self.regime_independent_count,
            "synthesis_reports":       self.synthesis_reports,
            "generated_at":            self.generated_at,
        }
