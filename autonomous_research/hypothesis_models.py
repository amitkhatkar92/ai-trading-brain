"""
hypothesis_models.py — Typed models for the Scientific Hypothesis Registry.

ARS Phase 1.2.

All models are dataclasses.  Serialisation helpers included for JSON round-trip.
No business logic lives here — pure data.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ─── enumerations ─────────────────────────────────────────────────────────────

class HypothesisStatus(str, Enum):
    PROPOSED     = "PROPOSED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED     = "APPROVED"
    PLANNED      = "PLANNED"
    RUNNING      = "RUNNING"
    VALIDATED    = "VALIDATED"
    CONFIRMED    = "CONFIRMED"
    REJECTED     = "REJECTED"
    ARCHIVED     = "ARCHIVED"


class HypothesisPriority(str, Enum):
    CRITICAL    = "CRITICAL"
    HIGH        = "HIGH"
    MEDIUM      = "MEDIUM"
    LOW         = "LOW"
    EXPLORATORY = "EXPLORATORY"


class HypothesisClassification(str, Enum):
    PERFORMANCE_GAP = "PERFORMANCE_GAP"
    COVERAGE_GAP    = "COVERAGE_GAP"
    TEMPORAL_GAP    = "TEMPORAL_GAP"
    DEGRADATION     = "DEGRADATION"
    CONTRADICTION   = "CONTRADICTION"
    EXPLORATORY     = "EXPLORATORY"
    MANUAL          = "MANUAL"


class EvidenceType(str, Enum):
    STUDY         = "STUDY"
    FINDING       = "FINDING"
    EDGE          = "EDGE"
    METRIC        = "METRIC"
    CERTIFICATION = "CERTIFICATION"
    STRATEGY      = "STRATEGY"
    EXTERNAL      = "EXTERNAL"


# ─── valid lifecycle transitions ──────────────────────────────────────────────

VALID_TRANSITIONS: Dict[HypothesisStatus, set] = {
    HypothesisStatus.PROPOSED:     {HypothesisStatus.UNDER_REVIEW,
                                    HypothesisStatus.ARCHIVED},
    HypothesisStatus.UNDER_REVIEW: {HypothesisStatus.APPROVED,
                                    HypothesisStatus.REJECTED,
                                    HypothesisStatus.PROPOSED},   # send back for revision
    HypothesisStatus.APPROVED:     {HypothesisStatus.PLANNED,
                                    HypothesisStatus.ARCHIVED},
    HypothesisStatus.PLANNED:      {HypothesisStatus.RUNNING,
                                    HypothesisStatus.ARCHIVED},
    HypothesisStatus.RUNNING:      {HypothesisStatus.VALIDATED,
                                    HypothesisStatus.REJECTED},
    HypothesisStatus.VALIDATED:    {HypothesisStatus.CONFIRMED,
                                    HypothesisStatus.REJECTED},
    HypothesisStatus.CONFIRMED:    {HypothesisStatus.ARCHIVED},
    HypothesisStatus.REJECTED:     {HypothesisStatus.ARCHIVED,
                                    HypothesisStatus.PROPOSED},   # revival path
    HypothesisStatus.ARCHIVED:     set(),                          # terminal
}

# Statuses considered "open" (eligible for further work)
OPEN_STATUSES = {
    HypothesisStatus.PROPOSED,
    HypothesisStatus.UNDER_REVIEW,
    HypothesisStatus.APPROVED,
    HypothesisStatus.PLANNED,
    HypothesisStatus.RUNNING,
    HypothesisStatus.VALIDATED,
}


# ─── sub-models ───────────────────────────────────────────────────────────────

@dataclass
class EvidenceReference:
    evidence_id:   str
    evidence_type: EvidenceType
    description:   str
    added_at:      datetime
    added_by:      str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id":   self.evidence_id,
            "evidence_type": self.evidence_type.value,
            "description":   self.description,
            "added_at":      self.added_at.isoformat(),
            "added_by":      self.added_by,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EvidenceReference":
        return cls(
            evidence_id=d["evidence_id"],
            evidence_type=EvidenceType(d["evidence_type"]),
            description=d.get("description", ""),
            added_at=_parse_dt(d["added_at"]),
            added_by=d.get("added_by", "system"),
        )


@dataclass
class DecisionEvent:
    event_id:        str
    timestamp:       datetime
    actor:           str
    action:          str
    reason:          str
    previous_status: HypothesisStatus
    new_status:      HypothesisStatus
    metadata:        Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":        self.event_id,
            "timestamp":       self.timestamp.isoformat(),
            "actor":           self.actor,
            "action":          self.action,
            "reason":          self.reason,
            "previous_status": self.previous_status.value,
            "new_status":      self.new_status.value,
            "metadata":        self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DecisionEvent":
        return cls(
            event_id=d.get("event_id", str(uuid.uuid4())[:8]),
            timestamp=_parse_dt(d["timestamp"]),
            actor=d.get("actor", "system"),
            action=d.get("action", ""),
            reason=d.get("reason", ""),
            previous_status=HypothesisStatus(d["previous_status"]),
            new_status=HypothesisStatus(d["new_status"]),
            metadata=d.get("metadata") or {},
        )


@dataclass
class ValidationResult:
    validated_at: datetime
    validated_by: str
    verdict:      str              # PASS | FAIL | INCONCLUSIVE
    findings:     List[str]
    study_ids:    List[str]
    metrics:      Dict[str, Any]
    notes:        str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validated_at": self.validated_at.isoformat(),
            "validated_by": self.validated_by,
            "verdict":      self.verdict,
            "findings":     self.findings,
            "study_ids":    self.study_ids,
            "metrics":      self.metrics,
            "notes":        self.notes,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ValidationResult":
        return cls(
            validated_at=_parse_dt(d["validated_at"]),
            validated_by=d.get("validated_by", "system"),
            verdict=d.get("verdict", "INCONCLUSIVE"),
            findings=d.get("findings") or [],
            study_ids=d.get("study_ids") or [],
            metrics=d.get("metrics") or {},
            notes=d.get("notes", ""),
        )


# ─── main hypothesis model ────────────────────────────────────────────────────

@dataclass
class ScientificHypothesis:
    hypothesis_id:           str
    title:                   str
    research_question:       str
    description:             str
    origin:                  str
    origin_study:            Optional[str]
    created_at:              datetime
    created_by:              str
    priority:                HypothesisPriority
    confidence:              float                   # 0.0–1.0: prior belief
    status:                  HypothesisStatus
    classification:          HypothesisClassification
    supporting_evidence:     List[EvidenceReference]
    knowledge_gap:           str
    expected_knowledge_gain: str
    required_data:           Dict[str, Any]
    dependencies:            List[str]               # hypothesis_ids
    validation_method:       str
    validation_result:       Optional[ValidationResult]
    decision_history:        List[DecisionEvent]
    last_reviewed:           Optional[datetime]
    notes:                   List[str]               # append-only

    # ─── serialisation ───────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hypothesis_id":           self.hypothesis_id,
            "title":                   self.title,
            "research_question":       self.research_question,
            "description":             self.description,
            "origin":                  self.origin,
            "origin_study":            self.origin_study,
            "created_at":              self.created_at.isoformat(),
            "created_by":              self.created_by,
            "priority":                self.priority.value,
            "confidence":              self.confidence,
            "status":                  self.status.value,
            "classification":          self.classification.value,
            "supporting_evidence":     [e.to_dict() for e in self.supporting_evidence],
            "knowledge_gap":           self.knowledge_gap,
            "expected_knowledge_gain": self.expected_knowledge_gain,
            "required_data":           self.required_data,
            "dependencies":            self.dependencies,
            "validation_method":       self.validation_method,
            "validation_result":       self.validation_result.to_dict() if self.validation_result else None,
            "decision_history":        [d.to_dict() for d in self.decision_history],
            "last_reviewed":           self.last_reviewed.isoformat() if self.last_reviewed else None,
            "notes":                   self.notes,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ScientificHypothesis":
        return cls(
            hypothesis_id=d["hypothesis_id"],
            title=d["title"],
            research_question=d.get("research_question", ""),
            description=d.get("description", ""),
            origin=d.get("origin", ""),
            origin_study=d.get("origin_study"),
            created_at=_parse_dt(d["created_at"]),
            created_by=d.get("created_by", "system"),
            priority=HypothesisPriority(d.get("priority", "MEDIUM")),
            confidence=float(d.get("confidence", 0.5)),
            status=HypothesisStatus(d["status"]),
            classification=HypothesisClassification(d.get("classification", "MANUAL")),
            supporting_evidence=[
                EvidenceReference.from_dict(e)
                for e in (d.get("supporting_evidence") or [])
            ],
            knowledge_gap=d.get("knowledge_gap", ""),
            expected_knowledge_gain=d.get("expected_knowledge_gain", ""),
            required_data=d.get("required_data") or {},
            dependencies=d.get("dependencies") or [],
            validation_method=d.get("validation_method", ""),
            validation_result=(
                ValidationResult.from_dict(d["validation_result"])
                if d.get("validation_result")
                else None
            ),
            decision_history=[
                DecisionEvent.from_dict(e)
                for e in (d.get("decision_history") or [])
            ],
            last_reviewed=_parse_dt(d["last_reviewed"]) if d.get("last_reviewed") else None,
            notes=d.get("notes") or [],
        )


# ─── exceptions ───────────────────────────────────────────────────────────────

class RegistryError(Exception):
    """Base class for all registry errors."""


class HypothesisNotFoundError(RegistryError):
    """Hypothesis ID does not exist in the registry."""


class DuplicateHypothesisError(RegistryError):
    """A hypothesis with this ID already exists."""


class InvalidTransitionError(RegistryError):
    """The requested lifecycle transition is not permitted."""
    def __init__(self, from_status: HypothesisStatus, to_status: HypothesisStatus):
        super().__init__(
            f"Transition {from_status.value} → {to_status.value} is not a valid "
            f"lifecycle transition.  Allowed from {from_status.value}: "
            f"{[s.value for s in VALID_TRANSITIONS[from_status]]}"
        )
        self.from_status = from_status
        self.to_status = to_status


class InvalidEvidenceError(RegistryError):
    """Evidence reference cannot be verified in KnowledgeProvider."""


class RegistryValidationError(RegistryError):
    """Required fields missing or invalid values."""


# ─── helper ───────────────────────────────────────────────────────────────────

def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(str(value)[:26], fmt)
        except (ValueError, TypeError):
            continue
    try:
        return datetime.fromisoformat(str(value)[:19])
    except (ValueError, TypeError):
        return datetime.now()
