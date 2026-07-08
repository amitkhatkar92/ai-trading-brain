"""
iios/decisions/models/decision_result.py
=========================================
DecisionResult — full workflow execution summary wrapping a Decision.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..decision_constants import WorkflowStage
from .decision import Decision


@dataclass
class StageRecord:
    """Timing and outcome record for one workflow stage."""
    stage:       WorkflowStage
    succeeded:   bool
    duration_ms: float
    note:        str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage":       self.stage.value,
            "succeeded":   self.succeeded,
            "duration_ms": round(self.duration_ms, 2),
            "note":        self.note,
        }


@dataclass
class DecisionResult:
    """
    Full output of a Decision Engine workflow invocation.

    Attributes
    ----------
    result_id           : Unique result identifier.
    request_id          : Parent DecisionRequest.
    decision            : The resolved Decision object.
    stage_records       : Per-stage timing and outcome.
    total_candidates    : How many candidates were evaluated.
    total_elapsed_ms    : End-to-end wall-clock time.
    policy_pass_count   : Candidates that passed all policies.
    policy_fail_count   : Candidates that failed at least one policy.
    warnings            : Non-blocking result warnings.
    errors              : Blocking result errors.
    succeeded           : True if a decision was completed.
    created_at          : Unix result timestamp.
    """

    result_id:         str                 = field(default_factory=lambda: str(uuid.uuid4()))
    request_id:        str                 = ""
    decision:          Decision            = field(default_factory=Decision)
    stage_records:     list[StageRecord]   = field(default_factory=list)
    total_candidates:  int                 = 0
    total_elapsed_ms:  float               = 0.0
    policy_pass_count: int                 = 0
    policy_fail_count: int                 = 0
    warnings:          list[str]           = field(default_factory=list)
    errors:            list[str]           = field(default_factory=list)
    succeeded:         bool                = False
    created_at:        float               = field(default_factory=time.time)

    def add_stage(
        self,
        stage:       WorkflowStage,
        succeeded:   bool,
        duration_ms: float,
        note:        str = "",
    ) -> None:
        self.stage_records.append(
            StageRecord(stage=stage, succeeded=succeeded, duration_ms=duration_ms, note=note)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id":         self.result_id,
            "request_id":        self.request_id,
            "decision":          self.decision.to_dict(),
            "stage_records":     [s.to_dict() for s in self.stage_records],
            "total_candidates":  self.total_candidates,
            "total_elapsed_ms":  round(self.total_elapsed_ms, 2),
            "policy_pass_count": self.policy_pass_count,
            "policy_fail_count": self.policy_fail_count,
            "warnings":          list(self.warnings),
            "errors":            list(self.errors),
            "succeeded":         self.succeeded,
            "created_at":        self.created_at,
        }
