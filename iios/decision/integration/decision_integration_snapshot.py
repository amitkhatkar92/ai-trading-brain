"""
decision_integration_snapshot.py — iios.decision.integration
=============================================================
Integration-level snapshot wrapping the M5 :class:`DecisionSnapshot` with
integration metadata (which components ran, timing, phases).

This is the published representation of a completed integration workflow.

C9 Decision Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from .constants import VERSION


@dataclass(frozen=True)
class DecisionIntegrationSnapshot:
    """
    Immutable integration-level snapshot.

    Wraps the M5 :class:`~iios.decision.snapshot.DecisionSnapshot` with
    integration-layer metadata: which components ran, per-phase timings,
    and an integration-level identifier.

    Fields
    ------
    integration_id :     Unique identifier for this integration run.
    request_id :         Originating integration request ID.
    decision_id :        Decision identifier.
    session_id :         M1 lifecycle session identifier.
    snapshot_id :        M5 DecisionSnapshot identifier (empty if absent).
    decision_status :    String status of the decision outcome.
    decision_score :     Final optimisation score (0.0 when N/A).
    decision_confidence: Confidence in the selection (0.0 when N/A).
    components_run :     Tuple of component type strings that participated.
    phase_times :        Dict mapping phase name → wall-clock seconds.
    total_time_s :       End-to-end wall-clock seconds.
    metadata :           Supplementary metadata dict.
    created_at :         UTC timestamp of snapshot creation.
    framework_version :  Framework version.
    """

    integration_id:      str
    request_id:          str
    decision_id:         str
    session_id:          str
    snapshot_id:         str                   = ""
    decision_status:     str                   = ""
    decision_score:      float                 = 0.0
    decision_confidence: float                 = 0.0
    components_run:      Tuple[str, ...]       = field(default_factory=tuple)
    phase_times:         Dict[str, float]      = field(default_factory=dict)
    total_time_s:        float                 = 0.0
    metadata:            Dict[str, Any]        = field(default_factory=dict)
    created_at:          datetime              = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    framework_version:   str                   = VERSION

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        request_id:         str,
        decision_id:        str,
        session_id:         str,
        *,
        integration_id:     Optional[str]           = None,
        snapshot_id:        str                     = "",
        decision_status:    str                     = "",
        decision_score:     float                   = 0.0,
        decision_confidence: float                  = 0.0,
        components_run:     Tuple[str, ...]         = (),
        phase_times:        Optional[Dict[str, float]] = None,
        total_time_s:       float                   = 0.0,
        metadata:           Optional[Dict[str, Any]] = None,
    ) -> "DecisionIntegrationSnapshot":
        return cls(
            integration_id      = integration_id or str(uuid.uuid4()),
            request_id          = request_id,
            decision_id         = decision_id,
            session_id          = session_id,
            snapshot_id         = snapshot_id,
            decision_status     = decision_status,
            decision_score      = decision_score,
            decision_confidence = decision_confidence,
            components_run      = tuple(components_run),
            phase_times         = dict(phase_times or {}),
            total_time_s        = total_time_s,
            metadata            = dict(metadata or {}),
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "integration_id":      self.integration_id,
            "request_id":          self.request_id,
            "decision_id":         self.decision_id,
            "session_id":          self.session_id,
            "snapshot_id":         self.snapshot_id,
            "decision_status":     self.decision_status,
            "decision_score":      self.decision_score,
            "decision_confidence": self.decision_confidence,
            "components_run":      list(self.components_run),
            "phase_times":         dict(self.phase_times),
            "total_time_s":        self.total_time_s,
            "metadata":            self.metadata,
            "created_at":          self.created_at.isoformat(),
            "framework_version":   self.framework_version,
        }

    def __repr__(self) -> str:
        return (
            f"DecisionIntegrationSnapshot("
            f"integration_id={self.integration_id!r}, "
            f"decision_id={self.decision_id!r}, "
            f"status={self.decision_status!r})"
        )
