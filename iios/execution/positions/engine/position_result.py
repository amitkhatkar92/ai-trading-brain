"""iios/execution/positions/engine/position_result.py
==================================================
PositionResult — unified result returned by every Position Engine operation.

C6 Execution Intelligence — Phase 3, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .constants import OperationType

if TYPE_CHECKING:
    from iios.execution.positions.lifecycle import Position


@dataclass(frozen=True)
class PositionResult:
    """
    Immutable result returned by every Position Engine operation.

    A result is the single source of truth for whether an operation
    succeeded, what position was affected, and how long it took.
    """

    result_id:      str
    request_id:     str
    operation_type: OperationType
    succeeded:      bool
    position_id:    str
    elapsed_ms:     float
    error_code:     str
    error_message:  str
    result_count:   int
    position:       Optional[Any] = None   # M1 Position instance
    data:           Dict[str, Any] = field(default_factory=dict, compare=False)
    metadata:       Dict[str, Any] = field(default_factory=dict, compare=False)
    completed_at:   float          = field(default_factory=time.time)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def failed(self) -> bool:
        return not self.succeeded

    @property
    def has_position(self) -> bool:
        return self.position is not None

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "result_id":      self.result_id,
            "request_id":     self.request_id,
            "operation_type": self.operation_type.value,
            "succeeded":      self.succeeded,
            "position_id":    self.position_id,
            "elapsed_ms":     self.elapsed_ms,
            "error_code":     self.error_code,
            "error_message":  self.error_message,
            "result_count":   self.result_count,
            "completed_at":   self.completed_at,
            "data":           dict(self.data),
            "metadata":       dict(self.metadata),
        }
        if self.position is not None:
            try:
                d["position"] = self.position.to_dict()
            except Exception:  # noqa: BLE001
                d["position"] = str(self.position)
        return d


# ── Factory helpers ───────────────────────────────────────────────────────────

def make_success_result(
    request_id:     str,
    operation_type: OperationType,
    position_id:    str,
    elapsed_ms:     float,
    *,
    position:       Optional[Any] = None,
    result_count:   int           = 1,
    data:           Dict[str, Any] | None = None,
    metadata:       Dict[str, Any] | None = None,
) -> PositionResult:
    return PositionResult(
        result_id=str(uuid.uuid4()),
        request_id=request_id,
        operation_type=operation_type,
        succeeded=True,
        position_id=position_id,
        elapsed_ms=elapsed_ms,
        error_code="",
        error_message="",
        result_count=result_count,
        position=position,
        data=data or {},
        metadata=metadata or {},
    )


def make_failure_result(
    request_id:     str,
    operation_type: OperationType,
    error_code:     str,
    error_message:  str,
    elapsed_ms:     float,
    *,
    position_id: str           = "",
    metadata:    Dict[str, Any] | None = None,
) -> PositionResult:
    return PositionResult(
        result_id=str(uuid.uuid4()),
        request_id=request_id,
        operation_type=operation_type,
        succeeded=False,
        position_id=position_id,
        elapsed_ms=elapsed_ms,
        error_code=error_code,
        error_message=error_message,
        result_count=0,
        data={},
        metadata=metadata or {},
    )
