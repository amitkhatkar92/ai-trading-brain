"""
sfr_models.py — Pure data models for Scientific Findings Review and Data Quality Assessment.

IIOS Research Governance — Phase 4 (Permanent Scientific Evolution).

All fields JSON-serialisable.  No business logic.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────────────────

class FindingOutcome(str, Enum):
    VALIDATED        = "VALIDATED"          # lift >= threshold, statistically significant
    REJECTED         = "REJECTED"           # lift below threshold or anti-correlated
    PARTIAL          = "PARTIAL"            # lift marginal or some conditions fail
    CONTRADICTION    = "CONTRADICTION"      # contradicts prior validated knowledge
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA" # not enough records to test
    ANOMALY          = "ANOMALY"            # unexpected statistical pattern
    UNEXPECTED       = "UNEXPECTED"         # finding not in original hypothesis scope


class DQAClassification(str, Enum):
    EXCELLENT   = "EXCELLENT"   # score >= 85
    GOOD        = "GOOD"        # score >= 70
    ADEQUATE    = "ADEQUATE"    # score >= 55
    LIMITED     = "LIMITED"     # score >= 40
    INSUFFICIENT = "INSUFFICIENT"  # score < 40


class EvolStageStatus(str, Enum):
    COMPLETE  = "COMPLETE"
    DEGRADED  = "DEGRADED"
    SKIPPED   = "SKIPPED"
    ERROR     = "ERROR"


# ─────────────────────────────────────────────────────────────────────────────
# Finding-level models
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SFRFinding:
    """One categorised finding from a completed study."""
    finding_id:    str
    pattern_id:    str                # e.g. W01, L03
    outcome:       FindingOutcome
    evidence:      str                # brief evidence description
    confidence:    float              # 0-1
    lift:          Optional[float]    = None
    n_matched:     Optional[int]      = None
    is_anomaly:    bool               = False
    notes:         str                = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "pattern_id": self.pattern_id,
            "outcome":    self.outcome.value,
            "evidence":   self.evidence,
            "confidence": self.confidence,
            "lift":       self.lift,
            "n_matched":  self.n_matched,
            "is_anomaly": self.is_anomaly,
            "notes":      self.notes,
        }


@dataclass
class GeneratedHypothesis:
    """Hypothesis generated from scientific evidence during the review."""
    hypothesis_id:     str
    title:             str
    research_question: str
    origin_gap:        str     # gap_id that triggered this
    priority:          str     # CRITICAL | HIGH | MEDIUM | LOW
    expected_gain:     float   # 0-1 knowledge gain estimate
    eig_score:         float   # Expected Information Gain (0-1)
    study_type:        str     # recommended study type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hypothesis_id":     self.hypothesis_id,
            "title":             self.title,
            "research_question": self.research_question,
            "origin_gap":        self.origin_gap,
            "priority":          self.priority,
            "expected_gain":     self.expected_gain,
            "eig_score":         self.eig_score,
            "study_type":        self.study_type,
        }


@dataclass
class NextResearchProgram:
    """Selected next research program from prioritised roadmap."""
    program_id:      str
    title:           str
    study_type:      str
    priority_rank:   int
    priority_score:  float
    evidence_basis:  str
    expected_gain:   float
    eig_score:       float
    estimated_hours: float
    source_gap:      str
    source_hypothesis: Optional[str]
    rationale:       str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "program_id":         self.program_id,
            "title":              self.title,
            "study_type":         self.study_type,
            "priority_rank":      self.priority_rank,
            "priority_score":     self.priority_score,
            "evidence_basis":     self.evidence_basis,
            "expected_gain":      self.expected_gain,
            "eig_score":          self.eig_score,
            "estimated_hours":    self.estimated_hours,
            "source_gap":         self.source_gap,
            "source_hypothesis":  self.source_hypothesis,
            "rationale":          self.rationale,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Data Quality Assessment models
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DQADimension:
    """Single quality dimension measurement."""
    name:          str
    score:         float   # 0-10
    raw_value:     Any     # e.g. 6 (years), 12 (sectors)
    unit:          str     # e.g. "years", "sectors", "records"
    threshold:     float   # minimum acceptable
    status:        str     # "PASS" | "MARGINAL" | "FAIL"
    finding:       str
    recommendation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":           self.name,
            "score":          round(self.score, 2),
            "raw_value":      self.raw_value,
            "unit":           self.unit,
            "threshold":      self.threshold,
            "status":         self.status,
            "finding":        self.finding,
            "recommendation": self.recommendation,
        }


@dataclass
class DQAResult:
    """Complete 11-dimension Data Quality Assessment result."""
    assessed_at:     str
    dimensions:      List[DQADimension]
    overall_score:   float               # 0-100
    classification:  DQAClassification
    weaknesses:      List[str]
    recommendations: List[str]
    summary_line:    str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assessed_at":    self.assessed_at,
            "dimensions":     [d.to_dict() for d in self.dimensions],
            "overall_score":  round(self.overall_score, 2),
            "classification": self.classification.value,
            "weaknesses":     self.weaknesses,
            "recommendations": self.recommendations,
            "summary_line":   self.summary_line,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Top-level SFR result
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SFRResult:
    """Complete result of one Scientific Findings Review cycle."""
    sfr_id:               str
    study_id:             str
    run_date:             str
    findings:             List[SFRFinding]
    generated_hypotheses: List[GeneratedHypothesis]
    next_program:         Optional[NextResearchProgram]
    dqa_result:           DQAResult
    contradictions:       int
    anomalies:            int
    methodology_notes:    List[str]
    status:               EvolStageStatus
    summary_line:         str

    # Aggregate counts
    @property
    def n_validated(self) -> int:
        return sum(1 for f in self.findings if f.outcome == FindingOutcome.VALIDATED)

    @property
    def n_rejected(self) -> int:
        return sum(1 for f in self.findings if f.outcome == FindingOutcome.REJECTED)

    @property
    def n_partial(self) -> int:
        return sum(1 for f in self.findings if f.outcome == FindingOutcome.PARTIAL)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sfr_id":               self.sfr_id,
            "study_id":             self.study_id,
            "run_date":             self.run_date,
            "findings":             [f.to_dict() for f in self.findings],
            "generated_hypotheses": [h.to_dict() for h in self.generated_hypotheses],
            "next_program":         self.next_program.to_dict() if self.next_program else None,
            "dqa_result":           self.dqa_result.to_dict(),
            "contradictions":       self.contradictions,
            "anomalies":            self.anomalies,
            "methodology_notes":    self.methodology_notes,
            "status":               self.status.value,
            "summary_line":         self.summary_line,
            "n_validated":          self.n_validated,
            "n_rejected":           self.n_rejected,
            "n_partial":            self.n_partial,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────

def make_sfr_id() -> str:
    return f"sfr-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"

def make_finding_id(pattern_id: str, study_id: str) -> str:
    return f"sfrf-{study_id[:8]}-{pattern_id}"

def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")
