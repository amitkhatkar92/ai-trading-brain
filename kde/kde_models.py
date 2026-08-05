"""
kde_models.py — Pure data models for KDE-001 Knowledge Discovery Engine.

All fields are JSON-serialisable. No business logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ── enumerations ──────────────────────────────────────────────────────────────

class DiscoveryStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    ACTIVE    = "ACTIVE"
    REVIEWED  = "REVIEWED"
    PROMOTED  = "PROMOTED"  # promoted to IRC by SD
    REJECTED  = "REJECTED"
    ARCHIVED  = "ARCHIVED"


class SDRecommendation(str, Enum):
    IGNORE  = "IGNORE"
    STUDY   = "STUDY"
    PROMOTE = "PROMOTE"
    REJECT  = "REJECT"
    ARCHIVE = "ARCHIVE"


class PotentialValue(str, Enum):
    LOW       = "LOW"
    MEDIUM    = "MEDIUM"
    HIGH      = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class RelationshipType(str, Enum):
    CORRELATED    = "CORRELATED"
    COMPLEMENTARY = "COMPLEMENTARY"
    CONTRADICTORY = "CONTRADICTORY"
    ENABLES       = "ENABLES"
    SUBSUMES      = "SUBSUMES"


class EvidenceType(str, Enum):
    DATA_POINTS = "DATA_POINTS"
    STATISTICAL = "STATISTICAL"
    PATTERN     = "PATTERN"
    HISTORICAL  = "HISTORICAL"
    COMPARATIVE = "COMPARATIVE"


class KDEError(Exception):
    """Base KDE error."""


# ── scoring weights (module-level, auditable) ─────────────────────────────────

DISCOVERY_WEIGHTS: Dict[str, float] = {
    "scientific_confidence": 0.35,
    "novelty":               0.25,
    "reproducibility":       0.20,
    "generality":            0.10,
    "business_impact":       0.10,
}


# ── discovery score ───────────────────────────────────────────────────────────

@dataclass
class DiscoveryScore:
    scientific_confidence: float
    novelty:               float
    reproducibility:       float
    generality:            float
    business_impact:       float
    overall:               float = field(init=False)

    def __post_init__(self) -> None:
        w = DISCOVERY_WEIGHTS
        self.overall = round(
            self.scientific_confidence * w["scientific_confidence"]
            + self.novelty             * w["novelty"]
            + self.reproducibility     * w["reproducibility"]
            + self.generality          * w["generality"]
            + self.business_impact     * w["business_impact"],
            4,
        )

    @classmethod
    def from_components(
        cls,
        scientific_confidence: float,
        novelty:               float,
        reproducibility:       float,
        generality:            float,
        business_impact:       float,
    ) -> "DiscoveryScore":
        return cls(
            scientific_confidence = max(0.0, min(1.0, scientific_confidence)),
            novelty               = max(0.0, min(1.0, novelty)),
            reproducibility       = max(0.0, min(1.0, reproducibility)),
            generality            = max(0.0, min(1.0, generality)),
            business_impact       = max(0.0, min(1.0, business_impact)),
        )

    def to_dict(self) -> Dict[str, float]:
        return {
            "scientific_confidence": self.scientific_confidence,
            "novelty":               self.novelty,
            "reproducibility":       self.reproducibility,
            "generality":            self.generality,
            "business_impact":       self.business_impact,
            "overall":               self.overall,
        }


# ── evidence ──────────────────────────────────────────────────────────────────

@dataclass
class DiscoveryEvidence:
    evidence_type:       str                   # EvidenceType value
    description:         str
    data_points:         int
    years_observed:      List[int]
    regimes_observed:    List[str]
    statistical_support: Dict[str, float]      # confidence, effect_size, p_value, etc.
    raw_values:          Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_type":       self.evidence_type,
            "description":         self.description,
            "data_points":         self.data_points,
            "years_observed":      self.years_observed,
            "regimes_observed":    self.regimes_observed,
            "statistical_support": self.statistical_support,
            "raw_values":          self.raw_values,
        }


# ── discovery candidate (raw scheme output) ───────────────────────────────────

@dataclass
class DiscoveryCandidate:
    scheme_id:         str
    question:          str
    answer:            str
    evidence:          List[DiscoveryEvidence]
    raw_score:         float                   # scheme-provided, 0-1
    years_observed:    List[int]
    regimes_observed:  List[str]
    suggested_followup: List[str]
    metadata:          Dict[str, Any]          # novelty_hint, impact_hint, feature_names, …

    @property
    def novelty_hint(self) -> float:
        return float(self.metadata.get("novelty_hint", 0.5))

    @property
    def impact_hint(self) -> float:
        return float(self.metadata.get("impact_hint", 0.3))

    @property
    def feature_names(self) -> List[str]:
        return list(self.metadata.get("feature_names", []))

    @property
    def dna_ids(self) -> List[str]:
        return list(self.metadata.get("dna_ids", []))


# ── promoted discovery ────────────────────────────────────────────────────────

@dataclass
class Discovery:
    discovery_id:      str               # "KDE-S001-20260805-0001"
    scheme_id:         str
    scheme_name:       str
    question:          str
    answer:            str
    evidence:          List[DiscoveryEvidence]
    score:             DiscoveryScore
    years_observed:    List[int]
    regimes_observed:  List[str]
    potential_value:   str               # PotentialValue value
    suggested_followup: List[str]
    status:            str               # DiscoveryStatus value
    sd_recommendation: Optional[str]     # SDRecommendation value or None
    feature_names:     List[str]
    dna_ids:           List[str]
    generated_at:      str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "discovery_id":      self.discovery_id,
            "scheme_id":         self.scheme_id,
            "scheme_name":       self.scheme_name,
            "question":          self.question,
            "answer":            self.answer,
            "evidence":          [e.to_dict() for e in self.evidence],
            "score":             self.score.to_dict(),
            "years_observed":    self.years_observed,
            "regimes_observed":  self.regimes_observed,
            "potential_value":   self.potential_value,
            "suggested_followup": self.suggested_followup,
            "status":            self.status,
            "sd_recommendation": self.sd_recommendation,
            "feature_names":     self.feature_names,
            "dna_ids":           self.dna_ids,
            "generated_at":      self.generated_at,
        }


# ── relationships between discoveries ────────────────────────────────────────

@dataclass
class DiscoveryRelationship:
    relationship_id:   str
    discovery_a:       str               # discovery_id
    discovery_b:       str
    relationship_type: str               # RelationshipType value
    strength:          float             # 0-1
    description:       str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relationship_id":   self.relationship_id,
            "discovery_a":       self.discovery_a,
            "discovery_b":       self.discovery_b,
            "relationship_type": self.relationship_type,
            "strength":          self.strength,
            "description":       self.description,
        }


# ── discovery cluster ─────────────────────────────────────────────────────────

@dataclass
class DiscoveryCluster:
    cluster_id:     str
    name:           str
    theme:          str
    discoveries:    List[str]            # discovery_ids
    cohesion_score: float
    description:    str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cluster_id":     self.cluster_id,
            "name":           self.name,
            "theme":          self.theme,
            "discoveries":    self.discoveries,
            "cohesion_score": self.cohesion_score,
            "description":    self.description,
        }


# ── run statistics ────────────────────────────────────────────────────────────

@dataclass
class DiscoveryStatistics:
    total_candidates:      int
    total_discoveries:     int
    discoveries_by_scheme: Dict[str, int]
    discoveries_by_regime: Dict[str, int]
    avg_score:             float
    avg_novelty:           float
    avg_confidence:        float
    high_value_count:      int           # potential_value in {HIGH, VERY_HIGH}
    relationship_count:    int
    cluster_count:         int
    generated_at:          str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_candidates":      self.total_candidates,
            "total_discoveries":     self.total_discoveries,
            "discoveries_by_scheme": self.discoveries_by_scheme,
            "discoveries_by_regime": self.discoveries_by_regime,
            "avg_score":             self.avg_score,
            "avg_novelty":           self.avg_novelty,
            "avg_confidence":        self.avg_confidence,
            "high_value_count":      self.high_value_count,
            "relationship_count":    self.relationship_count,
            "cluster_count":         self.cluster_count,
            "generated_at":          self.generated_at,
        }


# ── run result ────────────────────────────────────────────────────────────────

@dataclass
class KDERunResult:
    run_id:        str
    discoveries:   List[Discovery]
    relationships: List[DiscoveryRelationship]
    clusters:      List[DiscoveryCluster]
    statistics:    DiscoveryStatistics
    reports:       List[str]
    schemes_run:   List[str]
    generated_at:  str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id":        self.run_id,
            "discoveries":   [d.to_dict() for d in self.discoveries],
            "relationships": [r.to_dict() for r in self.relationships],
            "clusters":      [c.to_dict() for c in self.clusters],
            "statistics":    self.statistics.to_dict(),
            "reports":       self.reports,
            "schemes_run":   self.schemes_run,
            "generated_at":  self.generated_at,
        }


# ── engine status ─────────────────────────────────────────────────────────────

@dataclass
class KDEStatus:
    total_runs:         int
    last_run_id:        Optional[str]
    total_discoveries:  int
    schemes_registered: int
    schemes_enabled:    int
    last_run_at:        Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_runs":         self.total_runs,
            "last_run_id":        self.last_run_id,
            "total_discoveries":  self.total_discoveries,
            "schemes_registered": self.schemes_registered,
            "schemes_enabled":    self.schemes_enabled,
            "last_run_at":        self.last_run_at,
        }
