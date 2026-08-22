"""
tests/unit/bootstrap/test_startup_state.py
============================================
Unit tests for startup_state.py — phase transitions, stage results,
validation findings, and BootstrapStage descriptors.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from iios.bootstrap.startup_state import (
    BootstrapError,
    BootstrapStage,
    ShutdownError,
    StageStatus,
    StartupStageResult,
    SystemPhase,
    ValidationFinding,
    ValidationSeverity,
    allowed_transitions,
    is_valid_transition,
)


# ---------------------------------------------------------------------------
# SystemPhase
# ---------------------------------------------------------------------------


class TestSystemPhase:
    def test_is_active_running(self) -> None:
        assert SystemPhase.RUNNING.is_active is True

    def test_is_active_certified(self) -> None:
        assert SystemPhase.CERTIFIED.is_active is True

    def test_is_active_paused(self) -> None:
        assert SystemPhase.PAUSED.is_active is False

    def test_is_terminal_shutdown(self) -> None:
        assert SystemPhase.SHUTDOWN.is_terminal is True

    def test_is_terminal_running(self) -> None:
        assert SystemPhase.RUNNING.is_terminal is False

    def test_is_transitioning_initializing(self) -> None:
        assert SystemPhase.INITIALIZING.is_transitioning is True

    def test_is_transitioning_running(self) -> None:
        assert SystemPhase.RUNNING.is_transitioning is False


class TestPhaseTransitions:
    def test_valid_uninitialized_to_initializing(self) -> None:
        assert is_valid_transition(SystemPhase.UNINITIALIZED, SystemPhase.INITIALIZING)

    def test_invalid_uninitialized_to_running(self) -> None:
        assert not is_valid_transition(SystemPhase.UNINITIALIZED, SystemPhase.RUNNING)

    def test_valid_running_to_pausing(self) -> None:
        assert is_valid_transition(SystemPhase.RUNNING, SystemPhase.PAUSING)

    def test_valid_failed_to_recovery(self) -> None:
        assert is_valid_transition(SystemPhase.FAILED, SystemPhase.RECOVERY)

    def test_invalid_shutdown_to_anything(self) -> None:
        for phase in SystemPhase:
            assert not is_valid_transition(SystemPhase.SHUTDOWN, phase)

    def test_allowed_transitions_uninitialized(self) -> None:
        result = allowed_transitions(SystemPhase.UNINITIALIZED)
        assert SystemPhase.INITIALIZING in result
        assert len(result) == 1

    def test_allowed_transitions_running_includes_pause_stop_certified(self) -> None:
        result = allowed_transitions(SystemPhase.RUNNING)
        assert SystemPhase.PAUSING in result
        assert SystemPhase.STOPPING in result
        assert SystemPhase.CERTIFIED in result
        assert SystemPhase.FAILED in result

    def test_idempotent_same_phase(self) -> None:
        # Same-phase not in transition table (would be caught by SystemState idempotent check)
        assert not is_valid_transition(SystemPhase.RUNNING, SystemPhase.RUNNING)


# ---------------------------------------------------------------------------
# StartupStageResult
# ---------------------------------------------------------------------------


class TestStartupStageResult:
    def _make_result(self, status: StageStatus = StageStatus.RUNNING) -> StartupStageResult:
        return StartupStageResult(
            stage_number=1, stage_name="test_stage", status=status
        )

    def test_mark_completed(self) -> None:
        r = self._make_result()
        r.mark_completed()
        assert r.status == StageStatus.COMPLETED
        assert r.completed_at is not None
        assert r.succeeded is True

    def test_mark_failed(self) -> None:
        r = self._make_result()
        exc = ValueError("boom")
        r.mark_failed(exc, "Test failure")
        assert r.status == StageStatus.FAILED
        assert r.error is exc
        assert r.error_message == "Test failure"
        assert r.succeeded is False

    def test_mark_skipped(self) -> None:
        r = self._make_result()
        r.mark_skipped("dependency missing")
        assert r.status == StageStatus.SKIPPED
        assert r.metadata["skip_reason"] == "dependency missing"
        assert r.succeeded is True

    def test_duration_ms_increases(self) -> None:
        r = self._make_result()
        time.sleep(0.01)
        r.mark_completed()
        assert r.duration_ms >= 10.0

    def test_duration_ms_in_flight(self) -> None:
        r = self._make_result()
        assert r.duration_ms >= 0.0
        assert r.completed_at is None


# ---------------------------------------------------------------------------
# BootstrapStage
# ---------------------------------------------------------------------------


class TestBootstrapStage:
    def test_equality_by_number(self) -> None:
        s1 = BootstrapStage(number=5, name="a", description="", handler=lambda ctx: None)
        s2 = BootstrapStage(number=5, name="b", description="", handler=lambda ctx: None)
        assert s1 == s2

    def test_hash_by_number(self) -> None:
        s1 = BootstrapStage(number=7, name="a", description="", handler=lambda ctx: None)
        s2 = BootstrapStage(number=7, name="b", description="", handler=lambda ctx: None)
        assert hash(s1) == hash(s2)

    def test_repr(self) -> None:
        s = BootstrapStage(number=3, name="my_stage", description="", handler=lambda ctx: None)
        assert "3" in repr(s)
        assert "my_stage" in repr(s)

    def test_default_can_retry(self) -> None:
        s = BootstrapStage(number=1, name="x", description="", handler=lambda ctx: None)
        assert s.can_retry is True
        assert s.max_retries == 3


# ---------------------------------------------------------------------------
# ValidationFinding
# ---------------------------------------------------------------------------


class TestValidationFinding:
    def test_blocks_startup_on_error(self) -> None:
        f = ValidationFinding(
            check_name="test",
            severity=ValidationSeverity.ERROR,
            message="bad",
        )
        assert f.blocks_startup is True

    def test_blocks_startup_on_critical(self) -> None:
        f = ValidationFinding(
            check_name="test",
            severity=ValidationSeverity.CRITICAL,
            message="critical",
        )
        assert f.blocks_startup is True

    def test_does_not_block_on_warning(self) -> None:
        f = ValidationFinding(
            check_name="test",
            severity=ValidationSeverity.WARNING,
            message="just a warning",
        )
        assert f.blocks_startup is False

    def test_str_includes_check_name_and_message(self) -> None:
        f = ValidationFinding(
            check_name="python_version",
            severity=ValidationSeverity.CRITICAL,
            message="Python 3.11 too old",
            detail="Got 3.11",
        )
        s = str(f)
        assert "python_version" in s
        assert "Python 3.11 too old" in s
        assert "Got 3.11" in s


# ---------------------------------------------------------------------------
# BootstrapError / ShutdownError
# ---------------------------------------------------------------------------


class TestBootstrapError:
    def test_string_includes_stage_info(self) -> None:
        err = BootstrapError(
            "something failed",
            stage_number=11,
            stage_name="config_import",
            cause=ImportError("no module"),
        )
        s = str(err)
        assert "something failed" in s
        assert "11" in s
        assert "config_import" in s
        assert "ImportError" in s

    def test_no_cause(self) -> None:
        err = BootstrapError("simple error")
        assert "simple error" in str(err)
        assert err.cause is None

    def test_shutdown_error_is_runtime_error(self) -> None:
        err = ShutdownError("shutdown boom")
        assert isinstance(err, RuntimeError)
