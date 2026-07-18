"""
iios/execution/recovery/engine/recovery_validation.py
=====================================================
Stateless validator for the Execution Recovery Engine.

Validates requests, contexts, sessions, pipeline consistency, and
subsystem health snapshots.

C7 Execution Recovery & Resilience — Phase 1, Module 2
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence

from .recovery_context import (
    ExecutionGatewaySnapshot,
    ExecutionMonitoringSnapshot,
    ExecutionRiskSnapshot,
    FailureContext,
    RecoveryContext,
)
from .recovery_request import RecoveryRequest


class RecoveryEngineValidationResult:
    """Mutable accumulator of validation errors and warnings."""

    __slots__ = ("_errors", "_warnings")

    def __init__(self) -> None:
        self._errors:   List[str] = []
        self._warnings: List[str] = []

    @property
    def is_valid(self) -> bool:
        return len(self._errors) == 0

    @property
    def errors(self) -> List[str]:
        return list(self._errors)

    @property
    def warnings(self) -> List[str]:
        return list(self._warnings)

    def add_error(self, msg: str) -> None:
        self._errors.append(msg)

    def add_warning(self, msg: str) -> None:
        self._warnings.append(msg)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid":  self.is_valid,
            "errors":    self._errors,
            "warnings":  self._warnings,
        }


class RecoveryEngineValidator:
    """
    Stateless validator for engine-layer recovery objects.

    All methods return a RecoveryEngineValidationResult.
    """

    # ── Request ───────────────────────────────────────────────────────────────

    def validate_request(self, request: RecoveryRequest) -> RecoveryEngineValidationResult:
        """Validate a RecoveryRequest before creating a pipeline."""
        r = RecoveryEngineValidationResult()
        if not getattr(request, "request_id", ""):
            r.add_error("request_id must not be empty")
        if not getattr(request, "execution_session_id", ""):
            r.add_error("execution_session_id must not be empty")
        if not getattr(request, "subsystem_id", ""):
            r.add_error("subsystem_id must not be empty")
        if not getattr(request, "recovery_reason", ""):
            r.add_warning("recovery_reason is empty")
        failure = getattr(request, "failure_context", None)
        if failure is None:
            r.add_error("failure_context must not be None")
        else:
            fc_result = self.validate_failure_context(failure)
            for err in fc_result.errors:
                r.add_error(f"failure_context: {err}")
            for warn in fc_result.warnings:
                r.add_warning(f"failure_context: {warn}")
        return r

    # ── Failure context ───────────────────────────────────────────────────────

    def validate_failure_context(self, fc: FailureContext) -> RecoveryEngineValidationResult:
        """Validate a FailureContext."""
        r = RecoveryEngineValidationResult()
        if not getattr(fc, "failure_id", ""):
            r.add_error("failure_id must not be empty")
        if not getattr(fc, "subsystem_id", ""):
            r.add_error("subsystem_id must not be empty")
        if not getattr(fc, "failure_type", ""):
            r.add_error("failure_type must not be empty")
        if not getattr(fc, "failure_reason", ""):
            r.add_warning("failure_reason is empty")
        if getattr(fc, "detected_at", None) is None:
            r.add_error("detected_at must not be None")
        return r

    # ── Recovery context ──────────────────────────────────────────────────────

    def validate_context(self, ctx: RecoveryContext) -> RecoveryEngineValidationResult:
        """Validate an engine-level RecoveryContext."""
        r = RecoveryEngineValidationResult()
        if not getattr(ctx, "context_id", ""):
            r.add_error("context_id must not be empty")
        if not getattr(ctx, "request_id", ""):
            r.add_error("request_id must not be empty")
        if not getattr(ctx, "execution_session_id", ""):
            r.add_error("execution_session_id must not be empty")
        if not getattr(ctx, "subsystem_id", ""):
            r.add_error("subsystem_id must not be empty")
        if getattr(ctx, "failure_context", None) is None:
            r.add_error("failure_context must not be None")
        else:
            fc_result = self.validate_failure_context(ctx.failure_context)
            for err in fc_result.errors:
                r.add_error(f"failure_context: {err}")
        # Warn if no snapshots provided
        if (
            not getattr(ctx, "has_monitoring_snapshot", False)
            and not getattr(ctx, "has_gateway_snapshot", False)
            and not getattr(ctx, "has_risk_snapshot", False)
        ):
            r.add_warning("no execution snapshots provided; failure context is unverified")
        return r

    # ── Workflow consistency ──────────────────────────────────────────────────

    def validate_workflow_consistency(
        self,
        stage_order: Sequence[str],
        completed_stages: Sequence[str],
    ) -> RecoveryEngineValidationResult:
        """Validate that completed pipeline stages are in the correct order."""
        r = RecoveryEngineValidationResult()
        if not stage_order:
            r.add_error("stage_order must not be empty")
            return r
        expected_index = 0
        for stage in completed_stages:
            if stage not in stage_order:
                r.add_error(f"unknown pipeline stage: {stage!r}")
                continue
            idx = list(stage_order).index(stage)
            if idx < expected_index:
                r.add_error(
                    f"pipeline stage out of order: {stage!r} "
                    f"(expected after index {expected_index}, got {idx})"
                )
            expected_index = idx + 1
        return r

    # ── Subsystem health ──────────────────────────────────────────────────────

    def validate_subsystem_health(
        self,
        monitoring: ExecutionMonitoringSnapshot,
    ) -> RecoveryEngineValidationResult:
        """Validate that the monitoring snapshot indicates system is recoverable."""
        r = RecoveryEngineValidationResult()
        if monitoring is None:
            r.add_error("monitoring snapshot is None")
            return r
        if getattr(monitoring, "error_count", 0) > 100:
            r.add_warning(
                f"high error count ({monitoring.error_count}) — recovery may be difficult"
            )
        if getattr(monitoring, "degraded_components", None):
            count = len(monitoring.degraded_components)
            r.add_warning(f"{count} degraded component(s) detected")
        return r

    # ── Lifecycle consistency ─────────────────────────────────────────────────

    def validate_lifecycle_consistency(
        self,
        request_id: str,
        session_id: str,
        context_request_id: str,
    ) -> RecoveryEngineValidationResult:
        """Validate that request, context, and session IDs are consistent."""
        r = RecoveryEngineValidationResult()
        if not request_id:
            r.add_error("request_id is empty")
        if not session_id:
            r.add_error("session_id is empty")
        if context_request_id and context_request_id != request_id:
            r.add_error(
                f"context request_id {context_request_id!r} does not match "
                f"request_id {request_id!r}"
            )
        return r
