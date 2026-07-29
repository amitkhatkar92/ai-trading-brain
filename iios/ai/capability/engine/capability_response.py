"""
capability_response.py -- iios.ai.capability.engine
=====================================================
:class:`ExecutionStatus` — terminal states of a capability execution.
:class:`ExecutionResult`  — immutable result record.
:class:`CapabilityResponse` — outer response envelope returned to callers.

A9 Enterprise Capability Platform — Phase 3, Module 9
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class ExecutionStatus(str, Enum):
    """Terminal and transient states of a capability execution."""
    PENDING   = "pending"
    RUNNING   = "running"
    SUCCESS   = "success"
    FAILED    = "failed"
    TIMEOUT   = "timeout"
    CANCELLED = "cancelled"

    def is_terminal(self) -> bool:
        return self in (
            ExecutionStatus.SUCCESS,
            ExecutionStatus.FAILED,
            ExecutionStatus.TIMEOUT,
            ExecutionStatus.CANCELLED,
        )


@dataclass(frozen=True)
class ExecutionResult:
    """Immutable record of a single capability execution attempt."""

    result_id:     str
    request_id:    str
    capability_id: str
    status:        ExecutionStatus
    output:        Any             # None on failure
    error:         Optional[str]
    started_at:    float
    completed_at:  float
    duration_ms:   float

    # ── factories ─────────────────────────────────────────────────────────────

    @classmethod
    def success(
        cls,
        request_id:    str,
        capability_id: str,
        output:        Any,
        started_at:    float,
    ) -> "ExecutionResult":
        now = time.time()
        return cls(
            result_id     = str(uuid.uuid4()),
            request_id    = request_id,
            capability_id = capability_id,
            status        = ExecutionStatus.SUCCESS,
            output        = output,
            error         = None,
            started_at    = started_at,
            completed_at  = now,
            duration_ms   = (now - started_at) * 1000,
        )

    @classmethod
    def failure(
        cls,
        request_id:    str,
        capability_id: str,
        error:         str,
        started_at:    float,
    ) -> "ExecutionResult":
        now = time.time()
        return cls(
            result_id     = str(uuid.uuid4()),
            request_id    = request_id,
            capability_id = capability_id,
            status        = ExecutionStatus.FAILED,
            output        = None,
            error         = error,
            started_at    = started_at,
            completed_at  = now,
            duration_ms   = (now - started_at) * 1000,
        )

    @classmethod
    def timeout(
        cls,
        request_id:    str,
        capability_id: str,
        started_at:    float,
    ) -> "ExecutionResult":
        now = time.time()
        return cls(
            result_id     = str(uuid.uuid4()),
            request_id    = request_id,
            capability_id = capability_id,
            status        = ExecutionStatus.TIMEOUT,
            output        = None,
            error         = "Execution timed out",
            started_at    = started_at,
            completed_at  = now,
            duration_ms   = (now - started_at) * 1000,
        )

    # ── helpers ───────────────────────────────────────────────────────────────

    def is_successful(self) -> bool:
        return self.status == ExecutionStatus.SUCCESS

    def is_failed(self) -> bool:
        return self.status in (ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT)


@dataclass(frozen=True)
class CapabilityResponse:
    """Outer envelope returned to the caller by the gateway."""

    response_id:  str
    request_id:   str
    result:       ExecutionResult
    responded_at: float

    # ── factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        request_id: str,
        result:     ExecutionResult,
    ) -> "CapabilityResponse":
        return cls(
            response_id  = str(uuid.uuid4()),
            request_id   = request_id,
            result       = result,
            responded_at = time.time(),
        )

    # ── helpers ───────────────────────────────────────────────────────────────

    def is_successful(self) -> bool:
        return self.result.is_successful()
