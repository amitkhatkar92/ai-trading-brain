"""
iios/execution/recovery/snapshot/recovery_snapshot_builder.py
=============================================================
RecoverySnapshotBuilder — lifecycle-aware builder that constructs
ExecutionRecoverySnapshot objects from validated M1/M2/M3/M4 outputs.

Design rules:
  • Accepts ONLY duck-typed inputs to avoid hard circular imports.
  • Extracts information via getattr() with safe defaults.
  • Validates both inputs and the resulting snapshot.
  • Raises SnapshotBuildError when required data is missing or invalid.
  • Delegates snapshot creation to make_execution_recovery_snapshot().

C7 Execution Recovery & Resilience — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    BUILDER_ID,
    SCHEMA_VERSION,
    VERSION,
    RecoveryResult,
    SnapshotHealth,
    SnapshotStatus,
    VerificationOutcome,
)
from .exceptions import SnapshotBuildError, SnapshotNotRunningError, SnapshotValidationError
from .execution_recovery_snapshot import (
    ExecutionRecoverySnapshot,
    make_execution_recovery_snapshot,
)
from .recovery_snapshot_metadata import AuditMetadata, make_audit_metadata
from .recovery_snapshot_validation import RecoverySnapshotValidator, SnapshotValidationResult

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})

# ── Mapping helpers ───────────────────────────────────────────────────────────

_OUTCOME_TO_RESULT = {
    "success":           RecoveryResult.SUCCESS,
    "recovered":         RecoveryResult.SUCCESS,
    "completed":         RecoveryResult.SUCCESS,
    "failure":           RecoveryResult.FAILURE,
    "failed":            RecoveryResult.FAILURE,
    "partial":           RecoveryResult.PARTIAL,
    "aborted":           RecoveryResult.ABORTED,
    "unknown":           RecoveryResult.UNKNOWN,
    "no_action_needed":  RecoveryResult.SUCCESS,
}

_VERIFICATION_MAP = {
    "passed":  VerificationOutcome.PASSED,
    "failed":  VerificationOutcome.FAILED,
    "skipped": VerificationOutcome.SKIPPED,
    "pending": VerificationOutcome.PENDING,
    "unknown": VerificationOutcome.UNKNOWN,
    True:      VerificationOutcome.PASSED,
    False:     VerificationOutcome.FAILED,
}

_HEALTH_MAP = {
    "healthy":   SnapshotHealth.HEALTHY,
    "degraded":  SnapshotHealth.DEGRADED,
    "unhealthy": SnapshotHealth.UNHEALTHY,
    "unknown":   SnapshotHealth.UNKNOWN,
}


def _ga(obj: Any, attr: str, default: Any = "") -> Any:
    """Safe getattr with default."""
    return getattr(obj, attr, default)


def _gv(obj: Any, attr: str, default: str = "") -> str:
    """Get a .value string from an enum attribute, or the attr itself if str."""
    raw = _ga(obj, attr, None)
    if raw is None:
        return default
    if hasattr(raw, "value"):
        return str(raw.value)
    return str(raw) if raw else default


class RecoverySnapshotBuilder(LifecycleAwareMixin):
    """
    Lifecycle-aware builder for ExecutionRecoverySnapshot.

    Accepted sources (all duck-typed / Optional):
      lifecycle_session   — M1 RecoverySession  (required)
      engine_response     — M2 RecoveryResponse (required)
      engine_snapshot     — M2 RecoverySnapshot (optional, adds pipeline detail)
      policy_decision     — M3 RecoveryPolicyDecision (optional)
      failover_response   — M4 FailoverResponse (optional)
    """

    VERSION   = VERSION
    SYSTEM_ID = BUILDER_ID

    def __init__(self) -> None:
        super().__init__()
        self._validator = RecoverySnapshotValidator()

    def _on_start(self) -> None:
        _log.info("RecoverySnapshotBuilder started", system_id=BUILDER_ID)

    def _on_stop(self) -> None:
        _log.info("RecoverySnapshotBuilder stopped", system_id=BUILDER_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise SnapshotNotRunningError()

    # ── Public API ────────────────────────────────────────────────────────────

    def build(  # noqa: PLR0913
        self,
        lifecycle_session:  Any,
        engine_response:    Any,
        engine_snapshot:    Optional[Any] = None,
        policy_decision:    Optional[Any] = None,
        failover_response:  Optional[Any] = None,
        *,
        execution_id:   str = "",
        workflow_id:    str = "",
        gateway_id:     str = "",
        broker_id:      str = "",
        portfolio_id:   str = "",
        strategy_id:    str = "",
        metadata:       Optional[Dict[str, Any]] = None,
        snapshot_version: int = 1,
    ) -> ExecutionRecoverySnapshot:
        """
        Build and validate an ExecutionRecoverySnapshot.

        Raises:
            SnapshotNotRunningError  — builder not started
            SnapshotBuildError       — required inputs missing or invalid
            SnapshotValidationError  — resulting snapshot fails validation
        """
        self._assert_running()
        t_start = time.time()

        # Validate required inputs
        if lifecycle_session is None:
            raise SnapshotBuildError(
                "lifecycle_session is required", reason="missing_lifecycle_session"
            )
        if engine_response is None:
            raise SnapshotBuildError(
                "engine_response is required", reason="missing_engine_response"
            )

        # Extract fields from each source
        lc = self._extract_lifecycle(lifecycle_session)
        eng = self._extract_engine(engine_response, engine_snapshot)
        pol = self._extract_policy(policy_decision)
        fo = self._extract_failover(failover_response)

        # Resolve recovery result
        recovery_result = _OUTCOME_TO_RESULT.get(
            eng.get("outcome_str", "unknown"),
            RecoveryResult.UNKNOWN,
        )

        # Resolve verification outcome
        verification_result = fo.get("verification_outcome", VerificationOutcome.UNKNOWN)
        if verification_result == VerificationOutcome.UNKNOWN and engine_snapshot is not None:
            # Fallback: if engine has no failover data but snapshot is complete
            if eng.get("is_complete", False):
                verification_result = VerificationOutcome.SKIPPED

        # Resolve health
        health = fo.get("health", SnapshotHealth.UNKNOWN)

        # Build audit metadata
        build_time_ms = (time.time() - t_start) * 1000
        audit = make_audit_metadata(
            lifecycle_version = lc.get("version", VERSION),
            engine_version    = eng.get("version", VERSION),
            policy_version    = pol.get("version", VERSION),
            failover_version  = fo.get("version", VERSION),
            build_time_ms     = build_time_ms,
        )

        # Merge metadata
        merged_meta = {}
        merged_meta.update(pol.get("policy_meta", {}))
        merged_meta.update(fo.get("failover_meta", {}))
        if metadata:
            merged_meta.update(metadata)

        snapshot = make_execution_recovery_snapshot(
            recovery_session_id        = lc["session_id"],
            execution_session_id       = lc.get("execution_session_id", ""),
            lifecycle_state            = lc.get("lifecycle_state", ""),
            recovery_result            = recovery_result,
            verification_result        = verification_result,
            recovery_duration_ms       = eng.get("duration_ms", 0.0),
            audit_metadata             = audit,
            snapshot_version           = snapshot_version,
            recovery_plan_id           = lc.get("recovery_plan_id", ""),
            failure_id                 = lc.get("failure_id", ""),
            execution_id               = execution_id,
            workflow_id                = workflow_id or lc.get("workflow_id", ""),
            gateway_id                 = gateway_id,
            broker_id                  = broker_id,
            portfolio_id               = portfolio_id,
            strategy_id               = strategy_id,
            recovery_status            = SnapshotStatus.CREATED,
            recovery_health            = health,
            selected_recovery_policy   = pol.get("policy_name", ""),
            executed_failover_strategy = fo.get("action_executed", ""),
            recovery_trigger           = lc.get("recovery_trigger", ""),
            recovery_reason            = lc.get("recovery_reason", ""),
            recovery_statistics        = eng.get("statistics", {}),
            recovery_metadata          = merged_meta,
        )

        # Validate the result
        validation = self._validator.validate(snapshot)
        if not validation.is_valid:
            raise SnapshotValidationError(
                "Snapshot failed validation after build",
                errors=tuple(validation.errors),
            )

        return snapshot

    # ── Extraction helpers ────────────────────────────────────────────────────

    def _extract_lifecycle(self, session: Any) -> Dict[str, Any]:
        """Extract primitive values from a duck-typed M1 RecoverySession."""
        return {
            "session_id":          str(_ga(session, "session_id", str(uuid.uuid4()))),
            "execution_session_id": str(_ga(session, "execution_session_id", "")),
            "lifecycle_state":     _gv(session, "state", "unknown"),
            "recovery_plan_id":    str(_ga(session, "recovery_plan_id", "") or ""),
            "failure_id":          str(_ga(session, "failure_id", "") or ""),
            "workflow_id":         str(_ga(session, "workflow_id", "") or ""),
            "recovery_trigger":    _gv(session, "recovery_trigger", ""),
            "recovery_reason":     str(_ga(session, "recovery_reason", "")),
            "version":             str(_ga(session, "framework_version", VERSION) or VERSION),
        }

    def _extract_engine(
        self, response: Any, snapshot: Optional[Any]
    ) -> Dict[str, Any]:
        """Extract primitive values from duck-typed M2 RecoveryResponse + RecoverySnapshot."""
        duration = float(_ga(response, "duration_ms", 0.0) or 0.0)
        outcome_str = _gv(response, "outcome", "unknown")
        is_complete = bool(_ga(snapshot, "is_complete", False)) if snapshot else False
        stages = int(_ga(response, "pipeline_stages_completed", 0) or 0)
        stats: Dict[str, Any] = {
            "pipeline_stages_completed": stages,
            "pipeline_stages_total": int(_ga(response, "pipeline_stages_total", 0) or 0),
        }
        return {
            "outcome_str":  outcome_str,
            "duration_ms":  duration,
            "is_complete":  is_complete,
            "statistics":   stats,
            "version":      str(_ga(response, "framework_version", VERSION) or VERSION),
        }

    def _extract_policy(self, decision: Optional[Any]) -> Dict[str, Any]:
        """Extract primitive values from duck-typed M3 RecoveryPolicyDecision."""
        if decision is None:
            return {"policy_name": "", "version": VERSION, "policy_meta": {}}
        strategy_type = _gv(decision, "strategy_type", "")
        return {
            "policy_name":  str(_ga(decision, "policy_name", "")),
            "strategy_type": strategy_type,
            "confidence":   float(_ga(decision, "confidence_score", 0.0) or 0.0),
            "version":      str(_ga(decision, "version", VERSION) or VERSION),
            "policy_meta":  {"strategy_type": strategy_type},
        }

    def _extract_failover(self, response: Optional[Any]) -> Dict[str, Any]:
        """Extract primitive values from duck-typed M4 FailoverResponse."""
        if response is None:
            return {
                "action_executed":      "",
                "verification_outcome": VerificationOutcome.UNKNOWN,
                "health":               SnapshotHealth.UNKNOWN,
                "version":              VERSION,
                "failover_meta":        {},
            }

        result = _ga(response, "result", None)
        action_executed = ""
        if result is not None:
            action_executed = _gv(result, "action_executed", "")

        # Verification from M4 VerificationReport
        vr = _ga(response, "verification_report", None)
        if vr is None:
            # If result exists and is_successful → treat as skipped
            is_suc = bool(_ga(response, "is_successful", False))
            verification_outcome = (
                VerificationOutcome.SKIPPED if is_suc else VerificationOutcome.UNKNOWN
            )
        else:
            overall_str = _gv(vr, "overall_status", "unknown")
            verification_outcome = _VERIFICATION_MAP.get(
                overall_str, VerificationOutcome.UNKNOWN
            )

        # Health: operational flag → HEALTHY/UNHEALTHY
        is_operational = bool(_ga(response, "is_operational", True))
        health = SnapshotHealth.HEALTHY if is_operational else SnapshotHealth.UNHEALTHY

        return {
            "action_executed":      action_executed,
            "verification_outcome": verification_outcome,
            "health":               health,
            "version":              str(_ga(response, "response_time_ms", VERSION) and VERSION),
            "failover_meta":        {"failover_action": action_executed},
        }
