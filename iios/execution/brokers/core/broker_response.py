"""iios/execution/brokers/core/broker_response.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BrokerResponse:
    """Uniform response envelope returned from every broker adapter method."""

    success:       bool             = True
    data:          dict[str, Any]   = field(default_factory=dict)
    error_code:    str              = ""
    error_message: str              = ""
    response_id:   str              = field(default_factory=lambda: str(uuid.uuid4()))
    request_id:    str              = ""
    broker_id:     str              = ""
    operation:     str              = ""
    latency_ms:    float            = 0.0
    raw_payload:   dict[str, Any]   = field(default_factory=dict)
    metadata:      dict[str, Any]   = field(default_factory=dict)
    created_at:    float            = field(default_factory=time.time)

    # ── Factories ──────────────────────────────────────────────────────────────

    @classmethod
    def ok(
        cls,
        data:       dict[str, Any] = {},
        *,
        request_id: str   = "",
        broker_id:  str   = "",
        operation:  str   = "",
        latency_ms: float = 0.0,
    ) -> BrokerResponse:
        return cls(
            success=True,
            data=dict(data),
            request_id=request_id,
            broker_id=broker_id,
            operation=operation,
            latency_ms=latency_ms,
        )

    @classmethod
    def fail(
        cls,
        error_code:    str,
        error_message: str,
        *,
        request_id: str   = "",
        broker_id:  str   = "",
        operation:  str   = "",
        latency_ms: float = 0.0,
    ) -> BrokerResponse:
        return cls(
            success=False,
            error_code=error_code,
            error_message=error_message,
            request_id=request_id,
            broker_id=broker_id,
            operation=operation,
            latency_ms=latency_ms,
        )

    # ── Properties ────────────────────────────────────────────────────────────

    def is_success(self) -> bool:
        return self.success

    def is_error(self) -> bool:
        return not self.success

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_id":   self.response_id,
            "request_id":    self.request_id,
            "broker_id":     self.broker_id,
            "operation":     self.operation,
            "success":       self.success,
            "data":          self.data,
            "error_code":    self.error_code,
            "error_message": self.error_message,
            "latency_ms":    self.latency_ms,
            "metadata":      self.metadata,
            "created_at":    self.created_at,
        }
