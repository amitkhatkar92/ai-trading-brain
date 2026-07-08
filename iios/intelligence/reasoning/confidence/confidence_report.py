"""
iios/intelligence/reasoning/confidence/confidence_report.py
===========================================================
ConfidenceReport — the published output of a confidence calculation.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..reasoning_constants import ConfidenceLevel, CONFIDENCE_THRESHOLD_MODERATE
from .confidence_model import ConfidenceModel


@dataclass
class ConfidenceReport:
    """
    Immutable report produced by the ConfidenceEngine for one session.

    Attributes
    ----------
    report_id        : Unique identifier.
    session_id       : Reasoning session this report belongs to.
    model            : The underlying multi-dimensional model.
    confidence_level : Human-readable tier (very_low … certain).
    is_reliable      : True when score meets or exceeds MODERATE threshold.
    warnings         : List of flagged quality issues.
    recommendations  : Suggested improvements to raise confidence.
    created_at       : Unix timestamp.
    """

    report_id:        str               = field(
        default_factory=lambda: str(uuid.uuid4())
    )
    session_id:       str               = ""
    model:            ConfidenceModel   = field(default_factory=ConfidenceModel)
    confidence_level: ConfidenceLevel   = ConfidenceLevel.VERY_LOW
    is_reliable:      bool              = False
    warnings:         list[str]         = field(default_factory=list)
    recommendations:  list[str]         = field(default_factory=list)
    created_at:       float             = field(default_factory=time.time)

    # -- Properties ────────────────────────────────────────────────────────────

    @property
    def score(self) -> float:
        return self.model.final_score

    # -- Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id":        self.report_id,
            "session_id":       self.session_id,
            "score":            round(self.score, 4),
            "confidence_level": self.confidence_level.value,
            "is_reliable":      self.is_reliable,
            "warnings":         self.warnings,
            "recommendations":  self.recommendations,
            "model":            self.model.to_dict(),
            "created_at":       self.created_at,
        }
