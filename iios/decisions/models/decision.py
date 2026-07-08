"""
iios/decisions/models/decision.py
==================================
Decision — the canonical output of the Decision Engine.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..decision_constants import DecisionPriority, DecisionStatus, DecisionType
from .decision_candidate import DecisionCandidate
from .decision_metadata import DecisionMetadata


@dataclass
class Decision:
    """
    The fully resolved output of one Decision Engine workflow run.

    Attributes
    ----------
    decision_id           : Unique identifier.
    request_id            : Parent DecisionRequest.
    decision_type         : The type of decision made.
    status                : Current lifecycle state.
    priority              : Inherited from the request.
    selected_candidate_id : ID of the winning DecisionCandidate.
    confidence            : Confidence of the final decision [0, 1].
    risk_score            : Risk of the selected option [0, 1].
    rationale             : Human-readable explanation of why this was chosen.
    candidates            : All evaluated candidates.
    policy_summary        : Aggregated policy outcome info.
    alternatives          : Runner-up candidates (not selected).
    warnings              : Non-blocking workflow warnings.
    errors                : Blocking errors (present only on FAILED decisions).
    metadata              : Provenance metadata.
    version               : Schema version.
    created_at            : Unix timestamp of creation.
    completed_at          : Unix timestamp when workflow finished.
    """

    decision_id:           str                       = field(default_factory=lambda: str(uuid.uuid4()))
    request_id:            str                       = ""
    decision_type:         DecisionType              = DecisionType.GENERIC
    status:                DecisionStatus            = DecisionStatus.PENDING
    priority:              DecisionPriority          = DecisionPriority.MEDIUM
    selected_candidate_id: str                       = ""
    confidence:            float                     = 0.0
    risk_score:            float                     = 0.5
    rationale:             str                       = ""
    candidates:            list[DecisionCandidate]   = field(default_factory=list)
    policy_summary:        dict[str, Any]            = field(default_factory=dict)
    alternatives:          list[DecisionCandidate]   = field(default_factory=list)
    warnings:              list[str]                 = field(default_factory=list)
    errors:                list[str]                 = field(default_factory=list)
    metadata:              DecisionMetadata          = field(default_factory=DecisionMetadata)
    version:               str                       = "1.0"
    created_at:            float                     = field(default_factory=time.time)
    completed_at:          float                     = 0.0

    # -- Derived helpers ───────────────────────────────────────────────────────

    @property
    def is_completed(self) -> bool:
        return self.status == DecisionStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        return self.status == DecisionStatus.FAILED

    @property
    def selected_candidate(self) -> DecisionCandidate | None:
        for c in self.candidates:
            if c.candidate_id == self.selected_candidate_id:
                return c
        return None

    def complete(self) -> None:
        self.status       = DecisionStatus.COMPLETED
        self.completed_at = time.time()

    def fail(self, reason: str) -> None:
        self.status = DecisionStatus.FAILED
        self.errors.append(reason)
        self.completed_at = time.time()

    def elapsed_ms(self) -> float:
        end = self.completed_at if self.completed_at else time.time()
        return (end - self.created_at) * 1_000.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id":           self.decision_id,
            "request_id":            self.request_id,
            "decision_type":         self.decision_type.value,
            "status":                self.status.value,
            "priority":              self.priority.value,
            "selected_candidate_id": self.selected_candidate_id,
            "confidence":            round(self.confidence, 4),
            "risk_score":            round(self.risk_score, 4),
            "rationale":             self.rationale,
            "candidates":            [c.to_dict() for c in self.candidates],
            "policy_summary":        dict(self.policy_summary),
            "alternatives":          [c.to_dict() for c in self.alternatives],
            "warnings":              list(self.warnings),
            "errors":                list(self.errors),
            "metadata":              self.metadata.to_dict(),
            "version":               self.version,
            "created_at":            self.created_at,
            "completed_at":          self.completed_at,
            "elapsed_ms":            round(self.elapsed_ms(), 2),
        }
