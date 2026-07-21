"""
decision_integration_response.py — iios.decision.integration
=============================================================
Immutable public response returned by :class:`DecisionIntegrationEngine`.

C9 Decision Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import IntegrationStatus, VERSION


@dataclass(frozen=True)
class DecisionIntegrationResponse:
    """
    Immutable response returned by :meth:`DecisionIntegrationEngine.submit`.

    Fields
    ------
    response_id :          Unique identifier for this response.
    request_id :           Originating :class:`DecisionIntegrationRequest` ID.
    decision_id :          Decision identifier.
    session_id :           Decision lifecycle session identifier.
    status :               Outcome status.
    snapshot_id :          ID of the published :class:`DecisionSnapshot`
                           (empty string when no snapshot was produced).
    selected_decision :    The selected candidate dict (None on non-approval).
    decision_status :      String status of the decision (e.g. "approved").
    decision_score :       Confidence-adjusted final score (0.0 when N/A).
    decision_confidence :  Confidence in the selection (0.0 when N/A).
    decision_explanation : Human-readable summary of the decision.
    component_results :    Per-component outcome dict (lifecycle/engine/…).
    error_message :        Non-empty only on FAILED / TIMEOUT status.
    error_code :           Machine-readable code matching error_message.
    lifecycle_time_s :     Seconds spent in M1 lifecycle operations.
    engine_time_s :        Seconds spent in M2 engine.
    policy_time_s :        Seconds spent in M3 policy evaluation.
    optimization_time_s :  Seconds spent in M4 optimization.
    snapshot_time_s :      Seconds spent building/publishing M5 snapshot.
    total_time_s :         End-to-end wall-clock seconds.
    responded_at :         Wall-clock creation time (seconds since epoch).
    framework_version :    Framework version.
    """

    response_id:          str
    request_id:           str
    decision_id:          str
    session_id:           str
    status:               IntegrationStatus
    snapshot_id:          str                  = ""
    selected_decision:    Optional[Dict]       = None
    decision_status:      str                  = ""
    decision_score:       float                = 0.0
    decision_confidence:  float                = 0.0
    decision_explanation: str                  = ""
    component_results:    Dict[str, Any]       = field(default_factory=dict)
    error_message:        str                  = ""
    error_code:           str                  = ""
    lifecycle_time_s:     float                = 0.0
    engine_time_s:        float                = 0.0
    policy_time_s:        float                = 0.0
    optimization_time_s:  float                = 0.0
    snapshot_time_s:      float                = 0.0
    total_time_s:         float                = 0.0
    responded_at:         float                = field(default_factory=time.time)
    framework_version:    str                  = VERSION

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def is_success(self) -> bool:
        return self.status == IntegrationStatus.SUCCESS

    @property
    def is_partial(self) -> bool:
        return self.status == IntegrationStatus.PARTIAL

    @property
    def is_failure(self) -> bool:
        return self.status in (IntegrationStatus.FAILED, IntegrationStatus.TIMEOUT)

    @property
    def has_snapshot(self) -> bool:
        return bool(self.snapshot_id)

    @property
    def has_selection(self) -> bool:
        return self.selected_decision is not None

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        request_id:   str,
        decision_id:  str,
        session_id:   str,
        status:       IntegrationStatus,
        *,
        response_id:          Optional[str]          = None,
        snapshot_id:          str                    = "",
        selected_decision:    Optional[Dict]         = None,
        decision_status:      str                    = "",
        decision_score:       float                  = 0.0,
        decision_confidence:  float                  = 0.0,
        decision_explanation: str                    = "",
        component_results:    Optional[Dict[str, Any]] = None,
        error_message:        str                    = "",
        error_code:           str                    = "",
        lifecycle_time_s:     float                  = 0.0,
        engine_time_s:        float                  = 0.0,
        policy_time_s:        float                  = 0.0,
        optimization_time_s:  float                  = 0.0,
        snapshot_time_s:      float                  = 0.0,
        total_time_s:         float                  = 0.0,
    ) -> "DecisionIntegrationResponse":
        return cls(
            response_id          = response_id or str(uuid.uuid4()),
            request_id           = request_id,
            decision_id          = decision_id,
            session_id           = session_id,
            status               = status,
            snapshot_id          = snapshot_id,
            selected_decision    = selected_decision,
            decision_status      = decision_status,
            decision_score       = decision_score,
            decision_confidence  = decision_confidence,
            decision_explanation = decision_explanation,
            component_results    = dict(component_results or {}),
            error_message        = error_message,
            error_code           = error_code,
            lifecycle_time_s     = lifecycle_time_s,
            engine_time_s        = engine_time_s,
            policy_time_s        = policy_time_s,
            optimization_time_s  = optimization_time_s,
            snapshot_time_s      = snapshot_time_s,
            total_time_s         = total_time_s,
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":          self.response_id,
            "request_id":           self.request_id,
            "decision_id":          self.decision_id,
            "session_id":           self.session_id,
            "status":               self.status.value,
            "snapshot_id":          self.snapshot_id,
            "selected_decision":    self.selected_decision,
            "decision_status":      self.decision_status,
            "decision_score":       self.decision_score,
            "decision_confidence":  self.decision_confidence,
            "decision_explanation": self.decision_explanation,
            "component_results":    self.component_results,
            "error_message":        self.error_message,
            "error_code":           self.error_code,
            "lifecycle_time_s":     self.lifecycle_time_s,
            "engine_time_s":        self.engine_time_s,
            "policy_time_s":        self.policy_time_s,
            "optimization_time_s":  self.optimization_time_s,
            "snapshot_time_s":      self.snapshot_time_s,
            "total_time_s":         self.total_time_s,
            "responded_at":         self.responded_at,
            "framework_version":    self.framework_version,
        }

    def __repr__(self) -> str:
        return (
            f"DecisionIntegrationResponse("
            f"response_id={self.response_id!r}, "
            f"decision_id={self.decision_id!r}, "
            f"status={self.status.value!r})"
        )
