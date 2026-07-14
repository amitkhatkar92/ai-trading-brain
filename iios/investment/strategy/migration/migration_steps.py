"""iios/investment/strategy/migration/migration_steps.py
Step definitions and executors for the migration workflow.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from iios.investment.strategy.migration.migration_status import MigrationPhase


class StepResult(str, Enum):
    PASSED  = "passed"
    SKIPPED = "skipped"
    FAILED  = "failed"
    PARTIAL = "partial"


@dataclass(frozen=True)
class MigrationStepResult:
    """Immutable result for a single migration step."""
    step_id:       str
    step_type:     MigrationPhase
    strategy_id:   str
    strategy_name: str
    result:        StepResult
    message:       str
    detail:        str = ""
    duration_ms:   float = 0.0
    occurred_at:   datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    artifacts:     Dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return self.result in (StepResult.PASSED, StepResult.SKIPPED)

    @property
    def is_failure(self) -> bool:
        return self.result == StepResult.FAILED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id":       self.step_id,
            "step_type":     self.step_type.value,
            "strategy_id":   self.strategy_id,
            "strategy_name": self.strategy_name,
            "result":        self.result.value,
            "message":       self.message,
            "detail":        self.detail,
            "duration_ms":   round(self.duration_ms, 2),
            "occurred_at":   self.occurred_at.isoformat(),
        }


# ── Step factory helpers ───────────────────────────────────────────────────────

def _step(
    step_type:     MigrationPhase,
    strategy_id:   str,
    strategy_name: str,
    result:        StepResult,
    message:       str,
    detail:        str = "",
    duration_ms:   float = 0.0,
    artifacts:     Optional[Dict[str, Any]] = None,
) -> MigrationStepResult:
    return MigrationStepResult(
        step_id=str(uuid.uuid4()),
        step_type=step_type,
        strategy_id=strategy_id,
        strategy_name=strategy_name,
        result=result,
        message=message,
        detail=detail,
        duration_ms=duration_ms,
        artifacts=artifacts or {},
    )


class MigrationStepExecutor:
    """
    Executes individual migration steps and returns MigrationStepResult.
    Each step is idempotent and reversible where possible.
    """

    # ── Phase 1: Discovery ────────────────────────────────────────────────────

    def execute_discovery(
        self,
        strategy_id:   str,
        strategy_name: str,
        metadata_found: bool,
    ) -> MigrationStepResult:
        start = time.monotonic()
        result = StepResult.PASSED if metadata_found else StepResult.FAILED
        msg    = (f"Strategy '{strategy_name}' discovered successfully"
                  if metadata_found
                  else f"Strategy '{strategy_name}' not found in any legacy source")
        return _step(
            MigrationPhase.DISCOVERY, strategy_id, strategy_name, result, msg,
            duration_ms=(time.monotonic() - start) * 1000,
        )

    # ── Phase 2: Validation ───────────────────────────────────────────────────

    def execute_validation(
        self,
        strategy_id:   str,
        strategy_name: str,
        validation_passed: bool,
        error_count:   int,
        warning_count: int,
    ) -> MigrationStepResult:
        start = time.monotonic()
        if validation_passed:
            result = StepResult.PASSED if warning_count == 0 else StepResult.PARTIAL
        else:
            result = StepResult.FAILED
        msg = (
            f"Validation passed ({warning_count} warnings)"
            if validation_passed
            else f"Validation failed ({error_count} errors, {warning_count} warnings)"
        )
        return _step(
            MigrationPhase.VALIDATION, strategy_id, strategy_name, result, msg,
            duration_ms=(time.monotonic() - start) * 1000,
            artifacts={"error_count": error_count, "warning_count": warning_count},
        )

    # ── Phase 3: Preparation ──────────────────────────────────────────────────

    def execute_preparation(
        self,
        strategy_id:   str,
        strategy_name: str,
        adapter_id:    str,
        adaptation_mode: str,
    ) -> MigrationStepResult:
        start = time.monotonic()
        return _step(
            MigrationPhase.PREPARATION, strategy_id, strategy_name,
            StepResult.PASSED,
            f"Adapter created (mode: {adaptation_mode})",
            duration_ms=(time.monotonic() - start) * 1000,
            artifacts={"adapter_id": adapter_id, "adaptation_mode": adaptation_mode},
        )

    # ── Phase 4: Migration ────────────────────────────────────────────────────

    def execute_migration(
        self,
        strategy_id:   str,
        strategy_name: str,
        registered:    bool,
        registry_name: str,
    ) -> MigrationStepResult:
        start = time.monotonic()
        result = StepResult.PASSED if registered else StepResult.FAILED
        msg = (
            f"Strategy registered in '{registry_name}'"
            if registered
            else f"Failed to register strategy in '{registry_name}'"
        )
        return _step(
            MigrationPhase.MIGRATION, strategy_id, strategy_name, result, msg,
            duration_ms=(time.monotonic() - start) * 1000,
            artifacts={"registry": registry_name},
        )

    # ── Phase 5: Verification ─────────────────────────────────────────────────

    def execute_verification(
        self,
        strategy_id:   str,
        strategy_name: str,
        equivalence_passed: bool,
        test_count:    int,
        fail_count:    int,
    ) -> MigrationStepResult:
        start = time.monotonic()
        if equivalence_passed:
            result = StepResult.PASSED
            msg    = f"Behavior equivalence verified ({test_count} tests passed)"
        else:
            result = StepResult.PARTIAL if fail_count < test_count else StepResult.FAILED
            msg    = f"Behavior divergence detected ({fail_count}/{test_count} tests failed)"
        return _step(
            MigrationPhase.VERIFICATION, strategy_id, strategy_name, result, msg,
            duration_ms=(time.monotonic() - start) * 1000,
            artifacts={"test_count": test_count, "fail_count": fail_count},
        )

    # ── Phase 6: Approval ─────────────────────────────────────────────────────

    def execute_approval(
        self,
        strategy_id:   str,
        strategy_name: str,
        auto_approved: bool,
        approver:      str = "auto",
    ) -> MigrationStepResult:
        start = time.monotonic()
        result = StepResult.PASSED if auto_approved else StepResult.SKIPPED
        msg = (
            f"Migration auto-approved by {approver}"
            if auto_approved
            else "Migration pending manual approval"
        )
        return _step(
            MigrationPhase.APPROVAL, strategy_id, strategy_name, result, msg,
            duration_ms=(time.monotonic() - start) * 1000,
            artifacts={"approver": approver, "auto_approved": auto_approved},
        )

    # ── Phase 7: Rollback ─────────────────────────────────────────────────────

    def execute_rollback(
        self,
        strategy_id:   str,
        strategy_name: str,
        reason:        str,
        success:       bool,
    ) -> MigrationStepResult:
        start = time.monotonic()
        result = StepResult.PASSED if success else StepResult.FAILED
        msg = (
            f"Rollback completed: {reason}"
            if success
            else f"Rollback failed: {reason}"
        )
        return _step(
            MigrationPhase.ROLLBACK, strategy_id, strategy_name, result, msg,
            duration_ms=(time.monotonic() - start) * 1000,
            artifacts={"reason": reason},
        )

    # ── Phase 8: Archive ──────────────────────────────────────────────────────

    def execute_archive(
        self,
        strategy_id:   str,
        strategy_name: str,
        archive_path:  str,
    ) -> MigrationStepResult:
        start = time.monotonic()
        return _step(
            MigrationPhase.ARCHIVE, strategy_id, strategy_name,
            StepResult.PASSED,
            f"Strategy archived to: {archive_path}",
            duration_ms=(time.monotonic() - start) * 1000,
            artifacts={"archive_path": archive_path},
        )
