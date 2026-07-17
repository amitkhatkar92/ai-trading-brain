"""iios/execution/risk/controls/risk_control_response.py
==================================================
ControlResponse — lightweight wrapper around a RiskControlDecision
used for engine-level communication.

C6 Execution Intelligence — Phase 4, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    BLOCKING_ACTIONS,
    PASSTHROUGH_ACTIONS,
    ControlAction,
    PolicyType,
)
from .risk_control_decision import RiskControlDecision


@dataclass(frozen=True)
class ControlResponse:
    """
    Outer response envelope returned by the RiskControlEngine.

    Wraps a ``RiskControlDecision`` with success/failure metadata so
    callers can distinguish engine errors from control decisions.
    """

    response_id:   str
    request_id:    str
    evaluation_id: str
    succeeded:     bool
    elapsed_ms:    float
    created_at:    float

    # Present when succeeded=True
    decision:      Optional[RiskControlDecision] = field(default=None)

    # Present when succeeded=False
    error_code:    str = ""
    error_message: str = ""

    metadata:      Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def failed(self) -> bool:
        return not self.succeeded

    @property
    def action(self) -> Optional[ControlAction]:
        return self.decision.action if self.decision else None

    @property
    def allowed(self) -> bool:
        return bool(self.decision and self.decision.allowed)

    @property
    def blocked(self) -> bool:
        return bool(self.decision and self.decision.blocked)

    @property
    def is_emergency(self) -> bool:
        return bool(self.decision and self.decision.is_emergency)

    @property
    def requires_override(self) -> bool:
        return bool(self.decision and self.decision.requires_override)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":   self.response_id,
            "request_id":    self.request_id,
            "evaluation_id": self.evaluation_id,
            "succeeded":     self.succeeded,
            "elapsed_ms":    self.elapsed_ms,
            "created_at":    self.created_at,
            "action":        self.action.value if self.action else None,
            "allowed":       self.allowed,
            "blocked":       self.blocked,
            "is_emergency":  self.is_emergency,
            "error_code":    self.error_code,
            "error_message": self.error_message,
            "decision":      self.decision.to_dict() if self.decision else None,
        }


# ── Factory helpers ───────────────────────────────────────────────────────────

def make_control_response(
    request_id:    str,
    evaluation_id: str,
    decision:      RiskControlDecision,
    elapsed_ms:    float,
    *,
    metadata: Dict[str, Any] | None = None,
) -> ControlResponse:
    return ControlResponse(
        response_id=str(uuid.uuid4()),
        request_id=request_id,
        evaluation_id=evaluation_id,
        succeeded=True,
        elapsed_ms=elapsed_ms,
        created_at=time.time(),
        decision=decision,
        metadata=metadata or {},
    )


def make_error_response(
    request_id:    str,
    evaluation_id: str,
    elapsed_ms:    float,
    *,
    error_code:    str = "ERC-000",
    error_message: str = "Control evaluation failed.",
    metadata:      Dict[str, Any] | None = None,
) -> ControlResponse:
    return ControlResponse(
        response_id=str(uuid.uuid4()),
        request_id=request_id,
        evaluation_id=evaluation_id,
        succeeded=False,
        elapsed_ms=elapsed_ms,
        created_at=time.time(),
        decision=None,
        error_code=error_code,
        error_message=error_message,
        metadata=metadata or {},
    )
