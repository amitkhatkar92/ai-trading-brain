"""
tests/unit/bootstrap/test_lifecycle_manager.py
================================================
Unit tests for LifecycleManager and SystemState.
"""

from __future__ import annotations

import threading
import pytest

from iios.bootstrap.lifecycle_manager import LifecycleError, LifecycleManager
from iios.bootstrap.startup_state import SystemPhase
from iios.bootstrap.system_state import SystemState, get_system_state


@pytest.fixture(autouse=True)
def reset_system_state() -> None:
    """Reset the SystemState singleton before every test."""
    get_system_state().reset()
    yield
    get_system_state().reset()


# ---------------------------------------------------------------------------
# SystemState singleton
# ---------------------------------------------------------------------------


class TestSystemState:
    def test_singleton(self) -> None:
        a = get_system_state()
        b = get_system_state()
        assert a is b

    def test_initial_phase_uninitialized(self) -> None:
        assert get_system_state().current_phase == SystemPhase.UNINITIALIZED

    def test_valid_transition(self) -> None:
        s = get_system_state()
        s.transition_to(SystemPhase.INITIALIZING)
        assert s.current_phase == SystemPhase.INITIALIZING

    def test_invalid_transition_raises(self) -> None:
        s = get_system_state()
        with pytest.raises(ValueError, match="Invalid lifecycle transition"):
            s.transition_to(SystemPhase.RUNNING)

    def test_idempotent_same_phase(self) -> None:
        s = get_system_state()
        s.transition_to(SystemPhase.INITIALIZING)
        # Same phase should be no-op
        s.transition_to(SystemPhase.INITIALIZING)
        assert s.current_phase == SystemPhase.INITIALIZING

    def test_phase_history_recorded(self) -> None:
        s = get_system_state()
        s.transition_to(SystemPhase.INITIALIZING)
        s.transition_to(SystemPhase.INITIALIZED)
        history = s.phase_history
        assert len(history) == 2
        assert history[0].from_phase == SystemPhase.UNINITIALIZED
        assert history[0].to_phase == SystemPhase.INITIALIZING

    def test_is_running_false_initially(self) -> None:
        assert not get_system_state().is_running()

    def test_is_running_true_after_start(self) -> None:
        s = get_system_state()
        s.transition_to(SystemPhase.INITIALIZING)
        s.transition_to(SystemPhase.INITIALIZED)
        s.transition_to(SystemPhase.STARTING)
        s.transition_to(SystemPhase.RUNNING)
        assert s.is_running()

    def test_metadata_set_get(self) -> None:
        s = get_system_state()
        s.set("my_key", 42)
        assert s.get("my_key") == 42
        assert s.get("missing", "default") == "default"

    def test_phase_callback_fired(self) -> None:
        s = get_system_state()
        fired: list[bool] = []
        s.on_phase(SystemPhase.INITIALIZING, lambda: fired.append(True))
        s.transition_to(SystemPhase.INITIALIZING)
        assert len(fired) == 1

    def test_force_phase_bypasses_validation(self) -> None:
        s = get_system_state()
        # Force to RUNNING directly from UNINITIALIZED (not a valid transition)
        s.force_phase(SystemPhase.RUNNING, reason="test")
        assert s.current_phase == SystemPhase.RUNNING

    def test_uptime_increases(self) -> None:
        import time
        s = get_system_state()
        t1 = s.uptime_seconds
        time.sleep(0.01)
        t2 = s.uptime_seconds
        assert t2 > t1

    def test_thread_safe_transitions(self) -> None:
        """Multiple threads attempting transitions should not corrupt state."""
        s = get_system_state()
        s.transition_to(SystemPhase.INITIALIZING)
        errors: list[Exception] = []

        def try_transition() -> None:
            try:
                s.transition_to(SystemPhase.INITIALIZED)
            except (ValueError, Exception) as exc:
                errors.append(exc)

        threads = [threading.Thread(target=try_transition) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # Either all succeed (idempotent) or some raise ValueError (invalid) — no corruption
        assert s.current_phase in (SystemPhase.INITIALIZING, SystemPhase.INITIALIZED)


# ---------------------------------------------------------------------------
# LifecycleManager
# ---------------------------------------------------------------------------


class TestLifecycleManager:
    def test_initialize_transitions_to_initializing(self) -> None:
        mgr = LifecycleManager()
        mgr.initialize()
        assert mgr.current_phase == SystemPhase.INITIALIZING

    def test_double_initialize_is_idempotent(self) -> None:
        mgr = LifecycleManager()
        mgr.initialize()
        mgr.initialize()  # Should not raise
        assert mgr.current_phase == SystemPhase.INITIALIZING

    def test_full_startup_sequence(self) -> None:
        mgr = LifecycleManager()
        mgr.initialize()
        mgr.mark_initialized()
        mgr.start()
        mgr.mark_running()
        assert mgr.is_running

    def test_pause_and_resume(self) -> None:
        mgr = LifecycleManager()
        mgr.initialize()
        mgr.mark_initialized()
        mgr.start()
        mgr.mark_running()
        mgr.pause()
        assert mgr.is_paused
        mgr.resume()
        assert mgr.is_running

    def test_stop(self) -> None:
        mgr = LifecycleManager()
        mgr.initialize()
        mgr.mark_initialized()
        mgr.start()
        mgr.mark_running()
        mgr.stop()
        assert mgr.current_phase == SystemPhase.STOPPED

    def test_full_shutdown_sequence(self) -> None:
        mgr = LifecycleManager()
        mgr.initialize()
        mgr.mark_initialized()
        mgr.start()
        mgr.mark_running()
        mgr.stop()
        mgr.shutdown()
        assert mgr.current_phase == SystemPhase.SHUTDOWN

    def test_shutdown_auto_stops_if_running(self) -> None:
        mgr = LifecycleManager()
        mgr.initialize()
        mgr.mark_initialized()
        mgr.start()
        mgr.mark_running()
        mgr.shutdown()  # Should auto-stop first
        assert mgr.current_phase == SystemPhase.SHUTDOWN

    def test_mark_failed(self) -> None:
        mgr = LifecycleManager()
        mgr.initialize()
        mgr.mark_failed("test failure")
        assert mgr.current_phase == SystemPhase.FAILED

    def test_certify_from_running(self) -> None:
        mgr = LifecycleManager()
        mgr.initialize()
        mgr.mark_initialized()
        mgr.start()
        mgr.mark_running()
        mgr.certify()
        assert mgr.current_phase == SystemPhase.CERTIFIED

    def test_maintenance_mode(self) -> None:
        mgr = LifecycleManager()
        mgr.initialize()
        mgr.mark_initialized()
        mgr.start()
        mgr.mark_running()
        mgr.enter_maintenance()
        assert mgr.current_phase == SystemPhase.MAINTENANCE
        mgr.exit_maintenance()
        assert mgr.current_phase == SystemPhase.RUNNING

    def test_lifecycle_error_raised_for_invalid_pause(self) -> None:
        mgr = LifecycleManager()
        mgr.initialize()  # INITIALIZING — cannot pause
        with pytest.raises(LifecycleError):
            mgr.pause()

    def test_hook_fires_on_phase(self) -> None:
        mgr = LifecycleManager()
        fired: list[bool] = []
        mgr.register_hook(SystemPhase.RUNNING, lambda: fired.append(True))
        mgr.initialize()
        mgr.mark_initialized()
        mgr.start()
        mgr.mark_running()
        assert len(fired) == 1

    def test_is_operational_certified(self) -> None:
        mgr = LifecycleManager()
        mgr.initialize()
        mgr.mark_initialized()
        mgr.start()
        mgr.mark_running()
        mgr.certify()
        assert mgr.is_operational
