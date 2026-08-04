"""
sd_models.py — Pure data models for the Scientific Director.

IIOS Research Infrastructure — Phase 3C.

All fields are JSON-serialisable.  No business logic.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ─── enumerations ───────────────────────────────────────────────────────────

class ReviewType(str, Enum):
    DAILY        = "DAILY"
    WEEKLY       = "WEEKLY"
    MONTHLY      = "MONTHLY"
    PLATFORM     = "PLATFORM"
    STUDY_REVIEW = "STUDY_REVIEW"
    AD_HOC       = "AD_HOC"


class DecisionType(str, Enum):
    CREATE_HYPOTHESIS          = "CREATE_HYPOTHESIS"
    UPDATE_ROADMAP             = "UPDATE_ROADMAP"
    APPROVE_STUDY_CLASS_A      = "APPROVE_STUDY_CLASS_A"
    APPROVE_STUDY_CLASS_B_PENDING = "APPROVE_STUDY_CLASS_B_PENDING"
    REJECT_STUDY               = "REJECT_STUDY"
    CLOSE_STUDY                = "CLOSE_STUDY"
    ESCALATE_HUMAN             = "ESCALATE_HUMAN"
    ARCHIVE_HYPOTHESIS         = "ARCHIVE_HYPOTHESIS"
    PROMOTE_HYPOTHESIS         = "PROMOTE_HYPOTHESIS"
    DEFER                      = "DEFER"
    OBSERVE                    = "OBSERVE"


class DecisionClass(str, Enum):
    CLASS_A = "CLASS_A"  # autonomous — no human approval required
    CLASS_B = "CLASS_B"  # supervised — human approval required before action


class SDHealth(str, Enum):
    HEALTHY  = "HEALTHY"   # all observations succeeded; SD fully operational
    DEGRADED = "DEGRADED"  # some components unreachable; partial observation only
    BLIND    = "BLIND"     # cannot observe any component
    NO_DATA  = "NO_DATA"   # no review executed yet


class SignificanceLevel(str, Enum):
    HIGH          = "HIGH"
    MEDIUM        = "MEDIUM"
    LOW           = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


class UrgencyLevel(str, Enum):
    HIGH   = "HIGH"
    MEDIUM = "MEDIUM"
    LOW    = "LOW"


# ─── ScientificObservation ──────────────────────────────────────────────────

@dataclass
class ScientificObservation:
    """A single structured observation made by the Scientific Director."""

    observation_id:  str
    component:       str              # "KnowledgeProvider" | "GapDetector" | etc.
    metric:          str              # e.g. "total_findings", "open_gaps"
    value:           Any              # raw observed value
    interpretation:  str              # SD's interpretation of the value
    significance:    SignificanceLevel
    timestamp:       str              # ISO-8601

    def to_dict(self) -> Dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "component":      self.component,
            "metric":         self.metric,
            "value":          self.value,
            "interpretation": self.interpretation,
            "significance":   self.significance.value,
            "timestamp":      self.timestamp,
        }


# ─── ScientificReasoning ────────────────────────────────────────────────────

@dataclass
class ScientificReasoning:
    """The SD's multi-factor reasoning for one decision."""

    knowledge_completeness:       float    # 0.0-1.0
    evidence_quality:             float    # 0.0-1.0
    research_value:               float    # 0.0-1.0
    expected_information_gain:    float    # 0.0-1.0
    scientific_risk:              str      # "LOW" | "MEDIUM" | "HIGH"
    research_cost:                str      # "LOW" | "MEDIUM" | "HIGH"
    strategic_alignment:          float    # 0.0-1.0
    rationale:                    str      # human-readable explanation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "knowledge_completeness":    self.knowledge_completeness,
            "evidence_quality":          self.evidence_quality,
            "research_value":            self.research_value,
            "expected_information_gain": self.expected_information_gain,
            "scientific_risk":           self.scientific_risk,
            "research_cost":             self.research_cost,
            "strategic_alignment":       self.strategic_alignment,
            "rationale":                 self.rationale,
        }


# ─── ScientificDecision ─────────────────────────────────────────────────────

@dataclass
class ScientificDecision:
    """A single fully-explained scientific decision made by the SD."""

    decision_id:             str
    decision_type:           DecisionType
    decision_class:          DecisionClass
    observations:            List[ScientificObservation]
    reasoning:               ScientificReasoning
    decision_text:           str              # what was decided
    delegation_target:       str              # where it was delegated (RC | MLC | HUMAN | NONE)
    expected_outcome:        str
    confidence:              float            # 0.0-1.0
    timestamp:               str
    requires_human_approval: bool
    approved_by_human:       Optional[bool]   # None=pending, True=approved, False=rejected

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id":             self.decision_id,
            "decision_type":           self.decision_type.value,
            "decision_class":          self.decision_class.value,
            "observations":            [o.to_dict() for o in self.observations],
            "reasoning":               self.reasoning.to_dict(),
            "decision_text":           self.decision_text,
            "delegation_target":       self.delegation_target,
            "expected_outcome":        self.expected_outcome,
            "confidence":              self.confidence,
            "timestamp":               self.timestamp,
            "requires_human_approval": self.requires_human_approval,
            "approved_by_human":       self.approved_by_human,
        }


# ─── ScientificRecommendation ───────────────────────────────────────────────

@dataclass
class ScientificRecommendation:
    """An advisory recommendation produced by the SD."""

    recommendation_id: str
    target:            str           # "ROADMAP" | "HYPOTHESIS" | "HUMAN_OPERATOR" | "STUDY"
    content:           str
    urgency:           UrgencyLevel
    decision_class:    DecisionClass
    rationale:         str           = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "target":            self.target,
            "content":           self.content,
            "urgency":           self.urgency.value,
            "decision_class":    self.decision_class.value,
            "rationale":         self.rationale,
        }


# ─── ScientificReview ───────────────────────────────────────────────────────

@dataclass
class ScientificReview:
    """Complete record of one scientific review cycle."""

    review_id:       str
    review_type:     ReviewType
    date:            str
    observations:    List[ScientificObservation]
    decisions:       List[ScientificDecision]
    recommendations: List[ScientificRecommendation]
    health:          SDHealth
    summary:         str
    duration_ms:     float
    timestamp:       str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "review_id":       self.review_id,
            "review_type":     self.review_type.value,
            "date":            self.date,
            "observations":    [o.to_dict() for o in self.observations],
            "decisions":       [d.to_dict() for d in self.decisions],
            "recommendations": [r.to_dict() for r in self.recommendations],
            "health":          self.health.value,
            "summary":         self.summary,
            "duration_ms":     self.duration_ms,
            "timestamp":       self.timestamp,
        }


# ─── ScientificRoadmap ──────────────────────────────────────────────────────

@dataclass
class ScientificRoadmap:
    """SD's view of the current research roadmap."""

    entries:                List[Any]      # List[RoadmapEntry] — typed as Any to avoid circular
    total_entries:          int
    critical_gaps:          int
    high_gaps:              int
    medium_gaps:            int
    low_gaps:               int
    pending_plans:          int
    next_priority_id:       Optional[str]
    next_priority_title:    Optional[str]
    next_priority_score:    float
    generated_at:           str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_entries":       self.total_entries,
            "critical_gaps":       self.critical_gaps,
            "high_gaps":           self.high_gaps,
            "medium_gaps":         self.medium_gaps,
            "low_gaps":            self.low_gaps,
            "pending_plans":       self.pending_plans,
            "next_priority_id":    self.next_priority_id,
            "next_priority_title": self.next_priority_title,
            "next_priority_score": self.next_priority_score,
            "generated_at":        self.generated_at,
        }


# ─── ScientificHealth ───────────────────────────────────────────────────────

@dataclass
class ScientificHealth:
    """Current operational health of the Scientific Director."""

    health:                      SDHealth
    last_review_id:              Optional[str]
    last_review_date:            Optional[str]
    last_review_type:            Optional[str]
    total_reviews:               int
    hypotheses_proposed:         int
    hypotheses_active:           int
    gaps_open:                   int
    gaps_critical:               int
    studies_pending:             int
    knowledge_completeness:      float
    rc_health:                   str
    mlc_health:                  str
    consecutive_review_failures: int
    detail:                      str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "health":                      self.health.value,
            "last_review_id":              self.last_review_id,
            "last_review_date":            self.last_review_date,
            "last_review_type":            self.last_review_type,
            "total_reviews":               self.total_reviews,
            "hypotheses_proposed":         self.hypotheses_proposed,
            "hypotheses_active":           self.hypotheses_active,
            "gaps_open":                   self.gaps_open,
            "gaps_critical":               self.gaps_critical,
            "studies_pending":             self.studies_pending,
            "knowledge_completeness":      self.knowledge_completeness,
            "rc_health":                   self.rc_health,
            "mlc_health":                  self.mlc_health,
            "consecutive_review_failures": self.consecutive_review_failures,
            "detail":                      self.detail,
        }


# ─── errors ─────────────────────────────────────────────────────────────────

class SDError(Exception):
    """Base error for the Scientific Director."""


class SDObservationError(SDError):
    """Raised when a critical observation fails."""

    def __init__(self, component: str, reason: str) -> None:
        super().__init__(f"[{component}] {reason}")
        self.component = component
        self.reason    = reason


# ─── utilities ──────────────────────────────────────────────────────────────

def make_review_id(date_str: Optional[str] = None) -> str:
    """Return ``sd-review-{date}-{uuid8}``."""
    d = date_str or datetime.now().strftime("%Y%m%d")
    return f"sd-review-{d}-{uuid.uuid4().hex[:8]}"


def make_decision_id() -> str:
    """Return ``sd-dec-{uuid8}``."""
    return f"sd-dec-{uuid.uuid4().hex[:8]}"


def make_observation_id() -> str:
    """Return ``sd-obs-{uuid8}``."""
    return f"sd-obs-{uuid.uuid4().hex[:8]}"


def make_recommendation_id() -> str:
    """Return ``sd-rec-{uuid8}``."""
    return f"sd-rec-{uuid.uuid4().hex[:8]}"


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="milliseconds")
