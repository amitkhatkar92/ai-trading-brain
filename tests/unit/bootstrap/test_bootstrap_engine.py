"""
tests/unit/bootstrap/test_bootstrap_engine.py
===============================================
Integration-style unit tests for BootstrapEngine.

These tests run the engine against the real repository without mocking,
so they exercise the actual file system, config.py, and SQLite.

Tests that require specific environment state use tmp_path or monkeypatch.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from iios.bootstrap import (
    BootstrapEngine,
    BootstrapError,
    StartupContext,
    SystemPhase,
    get_system_state,
)


@pytest.fixture(autouse=True)
def reset_state() -> None:
    """Reset SystemState singleton before/after each test."""
    get_system_state().reset()
    yield
    get_system_state().reset()


@pytest.fixture()
def engine(tmp_path: Path) -> BootstrapEngine:
    """Return a BootstrapEngine pointing at the real repo root."""
    repo_root = Path(__file__).parents[3]  # workspace root
    return BootstrapEngine(repo_root=repo_root)


# ---------------------------------------------------------------------------
# Basic smoke test
# ---------------------------------------------------------------------------


class TestBootstrapEngineSmokeTest:
    @pytest.mark.integration
    def test_start_returns_context(self, engine: BootstrapEngine) -> None:
        ctx = engine.start()
        assert isinstance(ctx, StartupContext)
        assert ctx.operational is True
        assert ctx.run_id != ""
        engine.shutdown()

    @pytest.mark.integration
    def test_start_phase_is_running(self, engine: BootstrapEngine) -> None:
        engine.start()
        assert get_system_state().is_running()
        engine.shutdown()

    @pytest.mark.integration
    def test_start_db_initialized(self, engine: BootstrapEngine) -> None:
        ctx = engine.start()
        assert ctx.db_initialized is True
        assert ctx.db_connection is not None
        engine.shutdown()

    @pytest.mark.integration
    def test_start_python_version_set(self, engine: BootstrapEngine) -> None:
        ctx = engine.start()
        import sys
        expected = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        assert ctx.python_version == expected
        engine.shutdown()

    @pytest.mark.integration
    def test_start_config_loaded(self, engine: BootstrapEngine) -> None:
        ctx = engine.start()
        assert ctx.config_module_loaded is True
        assert ctx.decision_threshold == 6.5
        assert ctx.vix_threshold == 45.0
        engine.shutdown()

    @pytest.mark.integration
    def test_shutdown_transitions_to_shutdown_phase(self, engine: BootstrapEngine) -> None:
        engine.start()
        engine.shutdown()
        assert get_system_state().current_phase == SystemPhase.SHUTDOWN

    @pytest.mark.integration
    def test_context_accessible_after_start(self, engine: BootstrapEngine) -> None:
        ctx = engine.start()
        assert engine.context is ctx
        engine.shutdown()


# ---------------------------------------------------------------------------
# In-memory DB variant (faster, no file I/O)
# ---------------------------------------------------------------------------


class TestBootstrapEngineInMemory:
    @pytest.fixture()
    def engine_inmem(self, monkeypatch: pytest.MonkeyPatch) -> BootstrapEngine:
        """Engine with :memory: SQLite database."""
        repo_root = Path(__file__).parents[3]
        monkeypatch.setenv("IIOS_DB_PATH", ":memory:")
        monkeypatch.setenv("IIOS_ENV", "testing")
        monkeypatch.setenv("IIOS_PAPER_TRADING", "true")
        e = BootstrapEngine(repo_root=repo_root)
        return e

    @pytest.mark.integration
    def test_in_memory_db_start(self, engine_inmem: BootstrapEngine) -> None:
        ctx = engine_inmem.start()
        assert ctx.operational is True
        assert ctx.db_connection is not None
        # Verify bootstrap_runs table populated
        row = ctx.db_connection.execute(
            "SELECT env, paper_trading FROM bootstrap_runs WHERE run_id=?",
            (ctx.run_id,),
        ).fetchone()
        assert row is not None
        assert row["paper_trading"] == 1
        engine_inmem.shutdown()


# ---------------------------------------------------------------------------
# Context accumulation
# ---------------------------------------------------------------------------


class TestContextAccumulation:
    @pytest.mark.integration
    def test_completed_stages_increases(self, engine: BootstrapEngine) -> None:
        ctx = engine.start()
        assert ctx.completed_stages > 0
        engine.shutdown()

    @pytest.mark.integration
    def test_elapsed_ms_positive(self, engine: BootstrapEngine) -> None:
        ctx = engine.start()
        assert ctx.elapsed_ms > 0
        engine.shutdown()

    @pytest.mark.integration
    def test_health_checks_populated(self, engine: BootstrapEngine) -> None:
        ctx = engine.start()
        assert "database" in ctx.health_checks
        assert ctx.health_checks["database"] is True
        engine.shutdown()

    @pytest.mark.integration
    def test_no_blocking_findings_after_clean_start(self, engine: BootstrapEngine) -> None:
        ctx = engine.start()
        blocking = ctx.blocking_findings()
        assert len(blocking) == 0, f"Unexpected blocking findings: {blocking}"
        engine.shutdown()


# ---------------------------------------------------------------------------
# Progress callback
# ---------------------------------------------------------------------------


class TestProgressCallback:
    @pytest.mark.integration
    def test_progress_callback_receives_all_stages(self, engine: BootstrapEngine) -> None:
        from iios.bootstrap.startup_state import StageStatus
        progresses: list[tuple[int, str, StageStatus, float]] = []

        def cb(n: int, name: str, status: StageStatus, ms: float) -> None:
            progresses.append((n, name, status, ms))

        engine_with_cb = BootstrapEngine(
            repo_root=Path(__file__).parents[3],
            progress_callback=cb,
        )
        get_system_state().reset()
        engine_with_cb.start()
        assert len(progresses) > 0
        stage_numbers = [p[0] for p in progresses]
        assert 1 in stage_numbers
        engine_with_cb.shutdown()
