"""iios/execution/positions/integration/position_integration_response.py
==================================================
IntegrationResponse — unified result returned by every
PositionIntegrationEngine operation.

C6 Execution Intelligence — Phase 3, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import IntegrationOperationType


@dataclass(frozen=True)
class IntegrationResponse:
    """
    Immutable result returned by every integration operation.

    Attributes
    ----------
    response_id
        Unique UUID for this response.
    operation
        The :class:`IntegrationOperationType` that produced this response.
    succeeded
        Whether the operation completed without error.
    position_id
        The position affected (empty if N/A or if operation failed).
    message
        Human-readable description of the outcome.
    snapshot_dict
        Serialized ``PositionSnapshot.to_dict()`` if a snapshot was
        published as part of this operation.  ``None`` otherwise.
    data
        Arbitrary extra data from the operation.
    errors
        Tuple of error strings.  Empty on success.
    correlation_id
        External correlation ID threaded from the request.
    elapsed_ms
        Wall-clock duration of the integration operation in milliseconds.
    responded_at
        Unix timestamp of response creation.
    """

    response_id:    str
    operation:      IntegrationOperationType
    succeeded:      bool
    position_id:    str
    message:        str
    snapshot_dict:  Optional[Dict[str, Any]]
    data:           Dict[str, Any] = field(default_factory=dict, compare=False)
    errors:         Tuple[str, ...]= field(default_factory=tuple)
    correlation_id: str            = ""
    elapsed_ms:     float          = 0.0
    responded_at:   float          = field(default_factory=time.time)

    @property
    def failed(self) -> bool:
        return not self.succeeded

    @property
    def has_snapshot(self) -> bool:
        return self.snapshot_dict is not None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":    self.response_id,
            "operation":      self.operation.value,
            "succeeded":      self.succeeded,
            "position_id":    self.position_id,
            "message":        self.message,
            "snapshot_dict":  self.snapshot_dict,
            "data":           dict(self.data),
            "errors":         list(self.errors),
            "correlation_id": self.correlation_id,
            "elapsed_ms":     self.elapsed_ms,
            "responded_at":   self.responded_at,
        }


# ── Factory helpers ───────────────────────────────────────────────────────────

def make_success_response(
    operation:      IntegrationOperationType,
    position_id:    str,
    message:        str,
    elapsed_ms:     float,
    *,
    snapshot_dict:  Optional[Dict[str, Any]] = None,
    correlation_id: str = "",
    data:           Optional[Dict[str, Any]] = None,
) -> IntegrationResponse:
    return IntegrationResponse(
        response_id=str(uuid.uuid4()),
        operation=operation,
        succeeded=True,
        position_id=position_id,
        message=message,
        snapshot_dict=snapshot_dict,
        data=data or {},
        errors=(),
        correlation_id=correlation_id,
        elapsed_ms=elapsed_ms,
    )


def make_failure_response(
    operation:      IntegrationOperationType,
    message:        str,
    elapsed_ms:     float,
    *,
    position_id:    str = "",
    errors:         Tuple[str, ...] = (),
    correlation_id: str = "",
) -> IntegrationResponse:
    return IntegrationResponse(
        response_id=str(uuid.uuid4()),
        operation=operation,
        succeeded=False,
        position_id=position_id,
        message=message,
        snapshot_dict=None,
        data={},
        errors=errors or (message,),
        correlation_id=correlation_id,
        elapsed_ms=elapsed_ms,
    )
