"""
iios/intelligence/reasoning/reasoning_result.py
================================================
Output models produced by the Reasoning & Debate Engine.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from .reasoning_constants import (
    ConfidenceLevel,
    ReasoningStatus,
    ReasoningType,
    CONFIDENCE_THRESHOLD_HIGH,
)


@dataclass
class ReasoningResult:
    """
    Terminal output of a completed reasoning session.

    Attributes
    ----------
    session_id        : Source session identifier.
    reasoning_id      : Unique ID for this particular result.
    conclusion        : The reasoned conclusion (any serialisable value).
    confidence        : Aggregated confidence score in [0.0, 1.0].
    confidence_level  : Human-readable confidence tier.
    reasoning_type    : How the conclusion was reached.
    status            : Terminal session status.
    evidence_ids      : Evidence items that supported the conclusion.
    debate_ids        : Debate sessions that contributed.
    explanation_id    : ID of the associated DecisionExplanation.
    supporting_count  : Number of supporting arguments.
    opposing_count    : Number of opposing arguments.
    minority_opinions : Preserved dissenting views.
    duration_ms       : Wall-clock time consumed by the session.
    metadata          : Caller-supplied extra fields.
    created_at        : Unix timestamp.
    """

    session_id:        str                 = field(
        default_factory=lambda: str(uuid.uuid4())
    )
    reasoning_id:      str                 = field(
        default_factory=lambda: str(uuid.uuid4())
    )
    conclusion:        Any                 = None
    confidence:        float               = 0.0
    confidence_level:  ConfidenceLevel     = ConfidenceLevel.VERY_LOW
    reasoning_type:    ReasoningType       = ReasoningType.GENERIC
    status:            ReasoningStatus     = ReasoningStatus.COMPLETED
    evidence_ids:      list[str]           = field(default_factory=list)
    debate_ids:        list[str]           = field(default_factory=list)
    explanation_id:    str | None          = None
    supporting_count:  int                 = 0
    opposing_count:    int                 = 0
    minority_opinions: list[dict[str, Any]] = field(default_factory=list)
    duration_ms:       float               = 0.0
    metadata:          dict[str, Any]      = field(default_factory=dict)
    created_at:        float               = field(default_factory=time.time)

    # -- Properties ────────────────────────────────────────────────────────────

    @property
    def is_successful(self) -> bool:
        return self.status == ReasoningStatus.COMPLETED

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= CONFIDENCE_THRESHOLD_HIGH

    # -- Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id":        self.session_id,
            "reasoning_id":      self.reasoning_id,
            "conclusion":        self.conclusion,
            "confidence":        round(self.confidence, 4),
            "confidence_level":  self.confidence_level.value,
            "reasoning_type":    self.reasoning_type.value,
            "status":            self.status.value,
            "evidence_ids":      self.evidence_ids,
            "debate_ids":        self.debate_ids,
            "explanation_id":    self.explanation_id,
            "supporting_count":  self.supporting_count,
            "opposing_count":    self.opposing_count,
            "minority_opinions": self.minority_opinions,
            "duration_ms":       round(self.duration_ms, 2),
            "metadata":          self.metadata,
            "created_at":        self.created_at,
        }


@dataclass
class ReasoningOutput:
    """
    Lightweight output from a single reasoning step.
    Suitable as input/output for individual reasoning agents.
    """

    step_id:        str            = field(
        default_factory=lambda: str(uuid.uuid4())
    )
    reasoner_id:    str            = ""
    conclusion:     Any            = None
    confidence:     float          = 0.0
    reasoning_type: ReasoningType  = ReasoningType.GENERIC
    evidence_used:  list[str]      = field(default_factory=list)
    explanation:    str            = ""
    duration_ms:    float          = 0.0
    metadata:       dict[str, Any] = field(default_factory=dict)
    created_at:     float          = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id":        self.step_id,
            "reasoner_id":    self.reasoner_id,
            "conclusion":     self.conclusion,
            "confidence":     round(self.confidence, 4),
            "reasoning_type": self.reasoning_type.value,
            "evidence_used":  self.evidence_used,
            "explanation":    self.explanation,
            "duration_ms":    round(self.duration_ms, 2),
            "metadata":       self.metadata,
            "created_at":     self.created_at,
        }
