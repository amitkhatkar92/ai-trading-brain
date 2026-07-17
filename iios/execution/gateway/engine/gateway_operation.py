"""iios/execution/gateway/engine/gateway_operation.py
==================================================
GatewayOperation — immutable record of a single engine operation.

Each call to submit_request(), cancel_request(), or retry_request()
produces one or more GatewayOperation records which are appended to
GatewayEngineHistory.

C6 Execution Intelligence — Phase 5, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import OperationType, VERSION


@dataclass(frozen=True)
class GatewayOperation:
    """
    Immutable record of a single gateway engine operation.

    Appended to ``GatewayEngineHistory`` as operations complete.
    Never mutated after creation.
    """

    operation_id:   str
    operation_type: OperationType
    request_id:     str
    session_id:     str
    started_at:     float
    completed_at:   Optional[float]
    elapsed_ms:     float
    is_success:     bool
    error_message:  str
    version:        str             = VERSION
    metadata:       Dict[str, Any]  = field(default_factory=dict, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def is_failure(self) -> bool:
        return not self.is_success

    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation_id":   self.operation_id,
            "operation_type": self.operation_type.value,
            "request_id":     self.request_id,
            "session_id":     self.session_id,
            "started_at":     self.started_at,
            "completed_at":   self.completed_at,
            "elapsed_ms":     self.elapsed_ms,
            "is_success":     self.is_success,
            "error_message":  self.error_message,
            "version":        self.version,
            "metadata":       dict(self.metadata),
        }

    def __repr__(self) -> str:
        return (
            f"GatewayOperation("
            f"operation_type={self.operation_type.value!r}, "
            f"request_id={self.request_id!r}, "
            f"is_success={self.is_success})"
        )


def make_gateway_operation(
    operation_type: OperationType,
    request_id:     str,
    session_id:     str,
    started_at:     float,
    completed_at:   Optional[float] = None,
    is_success:     bool            = True,
    error_message:  str             = "",
    metadata:       Optional[Dict[str, Any]] = None,
) -> GatewayOperation:
    """Build a ``GatewayOperation`` with an auto-generated ``operation_id``."""
    end = completed_at or time.time()
    return GatewayOperation(
        operation_id=str(uuid.uuid4()),
        operation_type=operation_type,
        request_id=request_id,
        session_id=session_id,
        started_at=started_at,
        completed_at=completed_at or end,
        elapsed_ms=max(0.0, (end - started_at) * 1_000.0),
        is_success=is_success,
        error_message=error_message,
        metadata=metadata or {},
    )
