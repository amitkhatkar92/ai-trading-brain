"""iios/execution/snapshot/execution_snapshot.py
==================================================
ExecutionSnapshot — the canonical immutable output of the
Execution Engine, published to all downstream C6 consumers.

It represents the complete execution state at a specific point
in time. It contains data only. It performs NO execution.

C6 Execution Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.execution.snapshot.constants import (
    SnapshotLifecycle,
    SnapshotTrigger,
    VERSION,
)
from iios.execution.snapshot.execution_snapshot_metadata import SnapshotAuditMetadata


@dataclass(frozen=True)
class ExecutionSnapshot:
    """
    Immutable, versioned, auditable record of execution state
    at a specific point in time.

    This is the ONLY object published outside the Execution Engine.
    All downstream modules (OMS, EMS, Monitoring, Analytics, Risk,
    Recovery) consume ExecutionSnapshot exclusively.

    Thread-safe: frozen dataclass + all containers immutable.
    Serializable: to_dict() produces JSON-compatible output.
    Versioned:    schema_version + sequence_number support diff/history.
    Auditable:    audit_metadata carries provenance for every snapshot.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    snapshot_id:    str   = field(default_factory=lambda: f"SNAP-{uuid.uuid4().hex[:16].upper()}")
    schema_version: str   = VERSION

    # ── Primary identifiers ───────────────────────────────────────────────────
    execution_id:   str = ""
    workflow_id:    str = ""
    order_id:       str = ""
    portfolio_id:   str = ""
    decision_id:    str = ""
    strategy_id:    str = ""
    broker_id:      str = ""

    # ── Request / correlation ─────────────────────────────────────────────────
    request_id:     str = ""
    correlation_id: str = ""
    trace_id:       str = ""

    # ── Execution state ───────────────────────────────────────────────────────
    execution_state:     str = "IDLE"   # EngineExecutionState value
    order_state:         str = ""       # OrderState value (empty if unknown)
    is_terminal:         bool = False
    succeeded:           bool = False
    error_message:       str  = ""
    error_code:          str  = ""

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    lifecycle:           SnapshotLifecycle = SnapshotLifecycle.CREATED

    # ── Timing ────────────────────────────────────────────────────────────────
    captured_at:         float = field(default_factory=time.time)
    execution_started_at: Optional[float] = None
    execution_ended_at:   Optional[float] = None
    duration_ms:          float = 0.0

    # ── Execution context ref (lightweight — full context not embedded) ────────
    context_id:              str   = ""
    context_completeness:    float = 0.0
    has_market_snapshot:     bool  = False
    has_company_snapshot:    bool  = False
    has_strategy_snapshot:   bool  = False
    has_portfolio_snapshot:  bool  = False
    has_decision:            bool  = False

    # ── Execution result ref ──────────────────────────────────────────────────
    result_id:           str = ""
    validation_errors:   tuple[str, ...] = field(default_factory=tuple)

    # ── Execution statistics (inline) ─────────────────────────────────────────
    validation_duration_ms:  float = 0.0
    preparation_duration_ms: float = 0.0
    execution_phase_ms:      float = 0.0

    # ── Sequence / versioning ─────────────────────────────────────────────────
    sequence_number:     int  = 0
    version:             int  = 1

    # ── Audit metadata ────────────────────────────────────────────────────────
    audit_metadata:      Optional[SnapshotAuditMetadata] = None

    # ── Extra payload ─────────────────────────────────────────────────────────
    tags:                frozenset[str]   = field(default_factory=frozenset)
    extra:               dict[str, Any]  = field(default_factory=dict)

    # ─────────────────────────────────────────────────────────────────────────
    # Computed properties
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def failed(self) -> bool:
        return self.execution_state == "FAILED"

    @property
    def cancelled(self) -> bool:
        return self.execution_state == "CANCELLED"

    @property
    def completed(self) -> bool:
        return self.execution_state == "COMPLETED"

    @property
    def has_errors(self) -> bool:
        return bool(self.error_message) or bool(self.validation_errors)

    @property
    def has_result(self) -> bool:
        return bool(self.result_id)

    @property
    def has_context(self) -> bool:
        return bool(self.context_id)

    @property
    def has_broker(self) -> bool:
        return bool(self.broker_id)

    @property
    def snapshot_count(self) -> int:
        """Number of intelligence snapshots present in the execution context."""
        return sum([
            self.has_market_snapshot,
            self.has_company_snapshot,
            self.has_strategy_snapshot,
            self.has_portfolio_snapshot,
            self.has_decision,
        ])

    @property
    def age_sec(self) -> float:
        return time.time() - self.captured_at

    @property
    def has_all_required_ids(self) -> bool:
        return all([
            self.snapshot_id,
            self.execution_id,
            self.workflow_id,
            self.order_id,
        ])

    @property
    def trigger(self) -> str:
        if self.audit_metadata is not None:
            return self.audit_metadata.trigger.value
        return ""

    # ─────────────────────────────────────────────────────────────────────────
    # Serialisation
    # ─────────────────────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id":           self.snapshot_id,
            "schema_version":        self.schema_version,
            "execution_id":          self.execution_id,
            "workflow_id":           self.workflow_id,
            "order_id":              self.order_id,
            "portfolio_id":          self.portfolio_id,
            "decision_id":           self.decision_id,
            "strategy_id":           self.strategy_id,
            "broker_id":             self.broker_id,
            "request_id":            self.request_id,
            "correlation_id":        self.correlation_id,
            "trace_id":              self.trace_id,
            "execution_state":       self.execution_state,
            "order_state":           self.order_state,
            "is_terminal":           self.is_terminal,
            "succeeded":             self.succeeded,
            "failed":                self.failed,
            "cancelled":             self.cancelled,
            "completed":             self.completed,
            "has_errors":            self.has_errors,
            "error_message":         self.error_message,
            "error_code":            self.error_code,
            "lifecycle":             self.lifecycle.value,
            "captured_at":           self.captured_at,
            "execution_started_at":  self.execution_started_at,
            "execution_ended_at":    self.execution_ended_at,
            "duration_ms":           self.duration_ms,
            "context_id":            self.context_id,
            "context_completeness":  round(self.context_completeness, 4),
            "has_market_snapshot":   self.has_market_snapshot,
            "has_company_snapshot":  self.has_company_snapshot,
            "has_strategy_snapshot": self.has_strategy_snapshot,
            "has_portfolio_snapshot": self.has_portfolio_snapshot,
            "has_decision":          self.has_decision,
            "snapshot_count":        self.snapshot_count,
            "result_id":             self.result_id,
            "validation_errors":     list(self.validation_errors),
            "validation_duration_ms":  self.validation_duration_ms,
            "preparation_duration_ms": self.preparation_duration_ms,
            "execution_phase_ms":      self.execution_phase_ms,
            "sequence_number":       self.sequence_number,
            "version":               self.version,
            "has_all_required_ids":  self.has_all_required_ids,
            "tags":                  sorted(self.tags),
            "audit_metadata":        self.audit_metadata.to_dict() if self.audit_metadata else None,
        }

    def __repr__(self) -> str:
        return (
            f"ExecutionSnapshot("
            f"id={self.snapshot_id[:12]}, "
            f"execution={self.execution_id[:8] if self.execution_id else '?'}, "
            f"state={self.execution_state}, "
            f"seq={self.sequence_number})"
        )
