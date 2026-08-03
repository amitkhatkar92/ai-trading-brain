"""
gap_models.py — Typed models for the ARS GapDetector.

ARS Phase 2A.

Pure data.  No business logic.  All fields serialisable for JSON round-trip.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ─── enumerations ─────────────────────────────────────────────────────────────

class GapCategory(str, Enum):
    """Ten research-gap categories.  Designed for future extension."""
    DATA_GAP          = "DATA_GAP"
    EVIDENCE_GAP      = "EVIDENCE_GAP"
    REGIME_GAP        = "REGIME_GAP"
    SECTOR_GAP        = "SECTOR_GAP"
    TEMPORAL_GAP      = "TEMPORAL_GAP"
    VALIDATION_GAP    = "VALIDATION_GAP"
    CONTRADICTION_GAP = "CONTRADICTION_GAP"
    CONFIDENCE_GAP    = "CONFIDENCE_GAP"
    KNOWLEDGE_GAP     = "KNOWLEDGE_GAP"
    COVERAGE_GAP      = "COVERAGE_GAP"


class GapSeverity(str, Enum):
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


class GapStatus(str, Enum):
    OPEN         = "OPEN"           # newly detected, not yet acknowledged
    ACKNOWLEDGED = "ACKNOWLEDGED"   # noted, still unresolved
    CLOSED       = "CLOSED"         # resolved or superseded


# ─── gap model ────────────────────────────────────────────────────────────────

@dataclass
class KnowledgeGap:
    """
    A single identified research gap.

    Every gap is:
      • Traceable    — supporting_evidence + related_studies/findings/hypotheses
      • Reproducible — gap_id is a deterministic hash of (category, rule_id, source_key)
      • Documented   — severity_rationale and rule_parameters explain the derivation
    """
    gap_id:                   str
    category:                 GapCategory
    title:                    str
    description:              str
    severity:                 GapSeverity
    severity_rationale:       str          # exact reason this severity was chosen
    confidence:               float        # 0.0–1.0: certainty this is a real gap
    status:                   GapStatus
    supporting_evidence:      List[str]    # IDs / descriptors of triggering evidence
    related_studies:          List[str]    # study_ids relevant to this gap
    related_hypotheses:       List[str]    # hypothesis_ids relevant to this gap
    related_findings:         List[str]    # finding_ids relevant to this gap
    recommended_action:       str
    estimated_knowledge_gain: float        # 0.0–1.0
    rule_id:                  str          # which detection rule produced this gap
    rule_parameters:          Dict[str, Any]   # config values active when rule fired
    created_at:               datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gap_id":                   self.gap_id,
            "category":                 self.category.value,
            "title":                    self.title,
            "description":              self.description,
            "severity":                 self.severity.value,
            "severity_rationale":       self.severity_rationale,
            "confidence":               self.confidence,
            "status":                   self.status.value,
            "supporting_evidence":      self.supporting_evidence,
            "related_studies":          self.related_studies,
            "related_hypotheses":       self.related_hypotheses,
            "related_findings":         self.related_findings,
            "recommended_action":       self.recommended_action,
            "estimated_knowledge_gain": self.estimated_knowledge_gain,
            "rule_id":                  self.rule_id,
            "rule_parameters":          self.rule_parameters,
            "created_at":               self.created_at.isoformat(),
        }


# ─── configuration ────────────────────────────────────────────────────────────

@dataclass
class GapDetectorConfig:
    """
    All detection thresholds in one place.  Every threshold is independently
    configurable.  Defaults are conservative baselines for IIOS.

    ┌───────────────┬───────────────────────────────────────────────────────┐
    │ Rule          │ Severity calculation                                  │
    ├───────────────┼───────────────────────────────────────────────────────┤
    │ R-GD-01 DATA  │ n < threshold÷3 → CRITICAL                           │
    │               │ n < threshold÷2 → HIGH                               │
    │               │ n < threshold   → MEDIUM                             │
    ├───────────────┼───────────────────────────────────────────────────────┤
    │ R-GD-02 EVID  │ count == 0 → HIGH                                    │
    │               │ count < min → MEDIUM                                 │
    ├───────────────┼───────────────────────────────────────────────────────┤
    │ R-GD-03 REGI  │ zero findings + observed in history → HIGH           │
    │               │ zero findings + not observed → MEDIUM (conf 0.7)     │
    │               │ < min but > 0 → MEDIUM                               │
    ├───────────────┼───────────────────────────────────────────────────────┤
    │ R-GD-04 SECT  │ no sector data at all → one HIGH gap                 │
    │               │ sector count < min → MEDIUM per sector               │
    ├───────────────┼───────────────────────────────────────────────────────┤
    │ R-GD-05 TEMP  │ no dated studies → CRITICAL                          │
    │               │ age > 3×threshold → CRITICAL                         │
    │               │ age > 2×threshold → HIGH                             │
    │               │ age > threshold   → MEDIUM                           │
    ├───────────────┼───────────────────────────────────────────────────────┤
    │ R-GD-06 VALI  │ oldest_age is None → HIGH                            │
    │               │ oldest_age > 2×threshold → HIGH                      │
    │               │ else → MEDIUM                                        │
    ├───────────────┼───────────────────────────────────────────────────────┤
    │ R-GD-07 CONT  │ contra.severity > high_threshold → HIGH              │
    │               │ contra.severity > med_threshold  → MEDIUM            │
    │               │ else → LOW                                           │
    ├───────────────┼───────────────────────────────────────────────────────┤
    │ R-GD-08 CONF  │ confidence < critical_threshold → CRITICAL           │
    │               │ confidence < high_threshold     → HIGH               │
    │               │ confidence < min_confidence     → MEDIUM             │
    ├───────────────┼───────────────────────────────────────────────────────┤
    │ R-GD-09 KNOW  │ severity mirrors hypothesis priority                 │
    │               │ CRITICAL→CRITICAL, HIGH→HIGH, MEDIUM→MEDIUM,         │
    │               │ LOW/EXPLORATORY→LOW                                  │
    ├───────────────┼───────────────────────────────────────────────────────┤
    │ R-GD-10 COVE  │ always HIGH (zero findings for a classification)     │
    └───────────────┴───────────────────────────────────────────────────────┘
    """
    # R-GD-01 DATA_GAP
    min_study_observations:         int   = 100
    # R-GD-02 EVIDENCE_GAP
    min_corroborating_studies:       int   = 2
    # R-GD-03 REGIME_GAP
    known_regimes:                   tuple = ("TREND", "RANGE", "VOLATILE", "BEAR")
    min_findings_per_regime:         int   = 1
    # R-GD-04 SECTOR_GAP
    min_sector_observations:         int   = 20
    # R-GD-05 TEMPORAL_GAP
    max_study_age_days:              int   = 90
    # R-GD-06 VALIDATION_GAP
    max_edge_unvalidated_days:       int   = 30
    # R-GD-07 CONTRADICTION_GAP
    contradiction_high_threshold:    float = 0.70
    contradiction_medium_threshold:  float = 0.40
    # R-GD-08 CONFIDENCE_GAP
    min_synthesis_confidence:        float = 0.60
    confidence_critical_threshold:   float = 0.30
    confidence_high_threshold:       float = 0.45
    # R-GD-09 KNOWLEDGE_GAP
    max_hypothesis_open_days:        int   = 90


# ─── statistics ───────────────────────────────────────────────────────────────

@dataclass
class GapStatistics:
    total_gaps:            int
    open_gaps:             int
    by_category:           Dict[str, int]
    by_severity:           Dict[str, int]
    critical_count:        int
    high_count:            int
    detection_duration_ms: float
    detected_at:           datetime
    rules_fired:           Dict[str, int]   # rule_id → number of gaps produced

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_gaps":            self.total_gaps,
            "open_gaps":             self.open_gaps,
            "by_category":           self.by_category,
            "by_severity":           self.by_severity,
            "critical_count":        self.critical_count,
            "high_count":            self.high_count,
            "detection_duration_ms": self.detection_duration_ms,
            "detected_at":           self.detected_at.isoformat(),
            "rules_fired":           self.rules_fired,
        }


# ─── detection report ─────────────────────────────────────────────────────────

@dataclass
class GapDetectionReport:
    report_id:   str
    detected_at: datetime
    gaps:        List[KnowledgeGap]
    statistics:  GapStatistics
    warnings:    List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":   self.report_id,
            "detected_at": self.detected_at.isoformat(),
            "gaps":        [g.to_dict() for g in self.gaps],
            "statistics":  self.statistics.to_dict(),
            "warnings":    self.warnings,
        }


# ─── exceptions ───────────────────────────────────────────────────────────────

class GapDetectorError(Exception):
    """Base exception for GapDetector."""


class DetectionError(GapDetectorError):
    """Raised when a detection rule encounters an unexpected failure."""
