"""
iios/execution/recovery/engine/recovery_context.py
==================================================
Execution-level recovery context.

Carries failure information and execution snapshot references that the
Recovery Engine uses to coordinate recovery workflows.

This is distinct from the M1 lifecycle RecoveryContext
(iios.execution.recovery.lifecycle.recovery_context).  M2's context is
engine-layer; M1's is lifecycle-layer.

C7 Execution Recovery & Resilience — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import VERSION


# ── Execution Snapshots ───────────────────────────────────────────────────────
# Lightweight capture types.  The engine accepts these as inputs rather than
# depending on C6 monitoring internal types, keeping M2 layer-decoupled.

@dataclass(frozen=True)
class ExecutionMonitoringSnapshot:
    """Lightweight monitoring state snapshot passed to the recovery engine."""

    snapshot_id:         str
    captured_at:         float
    is_healthy:          bool
    degraded_components: Tuple[str, ...]  = ()
    error_count:         int              = 0
    metadata:            Dict[str, Any]   = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":         self.snapshot_id,
            "captured_at":         self.captured_at,
            "is_healthy":          self.is_healthy,
            "degraded_components": list(self.degraded_components),
            "error_count":         self.error_count,
        }


@dataclass(frozen=True)
class ExecutionGatewaySnapshot:
    """Lightweight gateway state snapshot passed to the recovery engine."""

    snapshot_id:    str
    captured_at:    float
    is_connected:   bool
    is_operational: bool
    latency_ms:     float           = 0.0
    error_message:  str             = ""
    metadata:       Dict[str, Any]  = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":    self.snapshot_id,
            "captured_at":    self.captured_at,
            "is_connected":   self.is_connected,
            "is_operational": self.is_operational,
            "latency_ms":     self.latency_ms,
            "error_message":  self.error_message,
        }


@dataclass(frozen=True)
class ExecutionRiskSnapshot:
    """Lightweight risk state snapshot passed to the recovery engine."""

    snapshot_id:      str
    captured_at:      float
    risk_level:       str            = "UNKNOWN"
    exposure:         float          = 0.0
    is_within_limits: bool           = True
    breach_count:     int            = 0
    metadata:         Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":      self.snapshot_id,
            "captured_at":      self.captured_at,
            "risk_level":       self.risk_level,
            "exposure":         self.exposure,
            "is_within_limits": self.is_within_limits,
            "breach_count":     self.breach_count,
        }


# ── Failure Context ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FailureContext:
    """Structured description of the failure that triggered recovery."""

    failure_id:          str
    subsystem_id:        str
    failure_type:        str
    failure_reason:      str
    detected_at:         float
    severity:            str             = "MEDIUM"
    affected_components: Tuple[str, ...] = ()
    metadata:            Dict[str, Any]  = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "failure_id":          self.failure_id,
            "subsystem_id":        self.subsystem_id,
            "failure_type":        self.failure_type,
            "failure_reason":      self.failure_reason,
            "detected_at":         self.detected_at,
            "severity":            self.severity,
            "affected_components": list(self.affected_components),
        }


def make_failure_context(
    subsystem_id: str,
    failure_type: str,
    failure_reason: str,
    *,
    severity: str = "MEDIUM",
    affected_components: Tuple[str, ...] = (),
    metadata: Optional[Dict[str, Any]] = None,
    failure_id: Optional[str] = None,
    detected_at: Optional[float] = None,
) -> FailureContext:
    """Factory for FailureContext."""
    return FailureContext(
        failure_id          = failure_id   or str(uuid.uuid4()),
        subsystem_id        = subsystem_id,
        failure_type        = failure_type,
        failure_reason      = failure_reason,
        detected_at         = detected_at if detected_at is not None else time.time(),
        severity            = severity,
        affected_components = affected_components,
        metadata            = dict(metadata) if metadata else {},
    )


# ── Recovery Context ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RecoveryContext:
    """
    Engine-level recovery context for a single recovery workflow.

    Aggregates the failure context and optional execution snapshots that
    the Recovery Engine uses while coordinating recovery stages.
    """

    context_id:           str
    request_id:           str
    execution_session_id: str
    subsystem_id:         str
    failure_context:      FailureContext
    monitoring_snapshot:  Optional[ExecutionMonitoringSnapshot] = None
    gateway_snapshot:     Optional[ExecutionGatewaySnapshot]    = None
    risk_snapshot:        Optional[ExecutionRiskSnapshot]       = None
    recovery_plan_id:     str                                   = ""
    workflow_id:          str                                   = ""
    tags:                 Tuple[str, ...]                       = ()
    metadata:             Dict[str, Any]                        = field(default_factory=dict)
    created_at:           float                                 = field(default_factory=time.time)
    framework_version:    str                                   = VERSION

    @property
    def has_monitoring_snapshot(self) -> bool:
        return self.monitoring_snapshot is not None

    @property
    def has_gateway_snapshot(self) -> bool:
        return self.gateway_snapshot is not None

    @property
    def has_risk_snapshot(self) -> bool:
        return self.risk_snapshot is not None

    @property
    def failure_id(self) -> str:
        return self.failure_context.failure_id

    @property
    def failure_type(self) -> str:
        return self.failure_context.failure_type

    @property
    def failure_severity(self) -> str:
        return self.failure_context.severity

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":           self.context_id,
            "request_id":           self.request_id,
            "execution_session_id": self.execution_session_id,
            "subsystem_id":         self.subsystem_id,
            "failure_context":      self.failure_context.to_dict(),
            "recovery_plan_id":     self.recovery_plan_id,
            "workflow_id":          self.workflow_id,
            "tags":                 list(self.tags),
            "created_at":           self.created_at,
            "framework_version":    self.framework_version,
        }


def make_recovery_context(
    request_id: str,
    execution_session_id: str,
    subsystem_id: str,
    failure_context: FailureContext,
    *,
    monitoring_snapshot: Optional[ExecutionMonitoringSnapshot] = None,
    gateway_snapshot: Optional[ExecutionGatewaySnapshot] = None,
    risk_snapshot: Optional[ExecutionRiskSnapshot] = None,
    recovery_plan_id: str = "",
    workflow_id: str = "",
    tags: Tuple[str, ...] = (),
    metadata: Optional[Dict[str, Any]] = None,
    context_id: Optional[str] = None,
) -> RecoveryContext:
    """Factory for RecoveryContext."""
    return RecoveryContext(
        context_id           = context_id or str(uuid.uuid4()),
        request_id           = request_id,
        execution_session_id = execution_session_id,
        subsystem_id         = subsystem_id,
        failure_context      = failure_context,
        monitoring_snapshot  = monitoring_snapshot,
        gateway_snapshot     = gateway_snapshot,
        risk_snapshot        = risk_snapshot,
        recovery_plan_id     = recovery_plan_id,
        workflow_id          = workflow_id,
        tags                 = tags,
        metadata             = dict(metadata) if metadata else {},
    )
