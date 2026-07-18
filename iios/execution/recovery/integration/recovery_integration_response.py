"""
iios/execution/recovery/integration/recovery_integration_response.py
====================================================================
IntegrationResponse — the client-facing output from the integration engine.

Wraps the ExecutionRecoverySnapshot and provides a clean, typed response
for all external consumers.

C7 Execution Recovery & Resilience — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, TYPE_CHECKING

from .constants import IntegrationStatus, VERSION

if TYPE_CHECKING:
    from iios.execution.recovery.snapshot import ExecutionRecoverySnapshot


@dataclass(frozen=True)
class IntegrationResponse:
    """
    Immutable response returned to callers of submit().

    The embedded ``recovery_snapshot`` is the canonical
    ExecutionRecoverySnapshot produced by the integration workflow.
    External consumers must use this snapshot as their sole view of
    the recovery outcome.
    """

    response_id:          str
    request_id:           str
    integration_status:   IntegrationStatus
    is_successful:        bool
    recovery_duration_ms: float
    response_time_ms:     float
    responded_at:         float
    recovery_snapshot:    Optional["ExecutionRecoverySnapshot"]   = None
    error_message:        str            = ""
    version:              str            = VERSION
    metadata:             Dict[str, Any] = field(default_factory=dict)

    @property
    def has_snapshot(self) -> bool:
        return self.recovery_snapshot is not None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":          self.response_id,
            "request_id":           self.request_id,
            "integration_status":   self.integration_status.value,
            "is_successful":        self.is_successful,
            "recovery_duration_ms": self.recovery_duration_ms,
            "response_time_ms":     self.response_time_ms,
            "responded_at":         self.responded_at,
            "has_snapshot":         self.has_snapshot,
            "error_message":        self.error_message,
            "recovery_snapshot":    (
                self.recovery_snapshot.to_dict() if self.recovery_snapshot else None
            ),
            "version":              self.version,
        }


def make_integration_response(
    request_id:           str,
    integration_status:   IntegrationStatus,
    is_successful:        bool,
    recovery_duration_ms: float,
    response_time_ms:     float,
    *,
    recovery_snapshot:   Optional["ExecutionRecoverySnapshot"] = None,
    error_message:       str = "",
    metadata:            Optional[Dict[str, Any]] = None,
    response_id:         Optional[str]   = None,
    responded_at:        Optional[float] = None,
) -> IntegrationResponse:
    return IntegrationResponse(
        response_id          = response_id or str(uuid.uuid4()),
        request_id           = request_id,
        integration_status   = integration_status,
        is_successful        = is_successful,
        recovery_duration_ms = recovery_duration_ms,
        response_time_ms     = response_time_ms,
        responded_at         = responded_at if responded_at is not None else time.time(),
        recovery_snapshot    = recovery_snapshot,
        error_message        = error_message,
        metadata             = dict(metadata) if metadata else {},
    )
