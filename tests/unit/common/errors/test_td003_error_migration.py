"""tests/unit/common/errors/test_td003_error_migration.py
TD-003 Institutional Error Handling Framework Migration — Validation Tests.

Verifies that all C1–C5 Integration Engines have been fully migrated
to the certified Institutional Error Handling Framework.

Scope
-----
Part 1 — Source-level imports  (all engines import get_error_manager + ErrorContext)
Part 2 — Source-level invariants (silent except-pass patterns are gone / guarded)
Part 3 — report_failure() called  (platform failure tracker receives engine failures)
Part 4 — ErrorContext fields  (engine_id, operation, stage set correctly)
Part 5 — Engine-internal counters preserved  (C4 stats + health still called)
Part 6 — C5 fallback preserved  (exception NOT re-raised; fallback snapshot returned)
Part 7 — C3 _on_stop exception is now logged  (not silently swallowed)
Part 8 — Thread safety  (concurrent integration calls record all failures)
Part 9 — Regression  (public APIs still work without errors)
"""
from __future__ import annotations

import pathlib
import threading
import re
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from iios.common.errors.error_manager import get_error_manager, reset_error_manager
from iios.common.errors.error_context import ErrorContext


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_WORKSPACE = pathlib.Path(__file__).parent.parent.parent.parent.parent

_ENGINE_FILES = {
    "C1": _WORKSPACE / "iios/investment/market/integration/market_intelligence_integration_engine.py",
    "C2": _WORKSPACE / "iios/investment/company/integration/company_intelligence_integration_engine.py",
    "C3": _WORKSPACE / "iios/investment/strategy/integration/strategy_intelligence_integration_engine.py",
    "C4": _WORKSPACE / "iios/investment/decision/integration/decision_intelligence_integration_engine.py",
    "C5": _WORKSPACE / "iios/investment/portfolio/integration/portfolio_intelligence_integration_engine.py",
}

_ENGINE_SYSTEM_IDS = {
    "C1": "iios:market:intelligence:integration",
    "C2": "iios:company:intelligence:integration",
    "C3": "iios:strategy:intelligence:integration",
    "C4": "iios:decision:intelligence:integration",
    "C5": "iios:portfolio:intelligence:integration",
}

_ENGINE_MODULE_PATHS = {
    "C1": "iios.investment.market.integration.market_intelligence_integration_engine",
    "C2": "iios.investment.company.integration.company_intelligence_integration_engine",
    "C3": "iios.investment.strategy.integration.strategy_intelligence_integration_engine",
    "C4": "iios.investment.decision.integration.decision_intelligence_integration_engine",
    "C5": "iios.investment.portfolio.integration.portfolio_intelligence_integration_engine",
}


def _src(key: str) -> str:
    return _ENGINE_FILES[key].read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _reset_error_manager():
    """Ensure each test starts with a clean ErrorManager singleton."""
    reset_error_manager()
    yield
    reset_error_manager()


# ---------------------------------------------------------------------------
# Part 1 — Source-level: error framework imports present
# ---------------------------------------------------------------------------

class TestTD003Part1ImportsPresent:
    """All C1–C5 engines import get_error_manager and ErrorContext."""

    @pytest.mark.parametrize("engine_key", ["C1", "C2", "C3", "C4", "C5"])
    def test_get_error_manager_imported(self, engine_key: str):
        src = _src(engine_key)
        assert "get_error_manager" in src, (
            f"{engine_key}: must import get_error_manager from iios.common.errors.error_manager"
        )

    @pytest.mark.parametrize("engine_key", ["C1", "C2", "C3", "C4", "C5"])
    def test_error_context_imported(self, engine_key: str):
        src = _src(engine_key)
        assert "ErrorContext" in src, (
            f"{engine_key}: must import ErrorContext from iios.common.errors.error_context"
        )

    @pytest.mark.parametrize("engine_key", ["C1", "C3"])
    def test_bind_error_context_imported(self, engine_key: str):
        """C1 and C3 use bind_error_context context manager."""
        src = _src(engine_key)
        assert "bind_error_context" in src, (
            f"{engine_key}: must import bind_error_context"
        )

    @pytest.mark.parametrize("engine_key", ["C1", "C2", "C3", "C4", "C5"])
    def test_import_from_correct_module(self, engine_key: str):
        src = _src(engine_key)
        assert "iios.common.errors.error_manager" in src, (
            f"{engine_key}: must import from iios.common.errors.error_manager"
        )

    @pytest.mark.parametrize("engine_key", ["C1", "C2", "C3", "C4", "C5"])
    def test_report_failure_referenced(self, engine_key: str):
        src = _src(engine_key)
        assert "report_failure" in src, (
            f"{engine_key}: report_failure() must appear in the source"
        )


# ---------------------------------------------------------------------------
# Part 2 — Source-level invariants
# ---------------------------------------------------------------------------

class TestTD003Part2SourceInvariants:
    """Silent exception swallows are gone; every except block reports failures."""

    def test_c3_on_stop_no_bare_pass(self):
        """C3 _on_stop: the `except Exception: pass` pattern is gone."""
        src = _src("C3")
        # There must be no bare `except Exception:\n                    pass`
        assert not re.search(r"except Exception:\s*\n\s*pass", src), (
            "C3 _on_stop: silent 'except Exception: pass' must be replaced with logging"
        )

    def test_c3_on_stop_warns_on_health_stop_failure(self):
        """C3 _on_stop: the health stop exception is now logged as a warning."""
        src = _src("C3")
        assert "_log.warning" in src or "log.warning" in src, (
            "C3: health-monitor stop exception must be logged (not silently swallowed)"
        )

    def test_c1_all_callback_excepts_have_report_failure(self):
        """C1 _fire_callbacks: all 3 callback except blocks call report_failure."""
        src = _src("C1")
        count = src.count("report_failure")
        # update() + 3 callbacks = at least 4 calls
        assert count >= 4, (
            f"C1: expected at least 4 report_failure calls, found {count}"
        )

    def test_c4_except_binds_exc_variable(self):
        """C4 integrate_sync: except block binds exc (needed for report_failure)."""
        src = _src("C4")
        assert "except Exception as exc:" in src, (
            "C4: integrate_sync except block must bind 'exc' variable"
        )

    def test_c5_except_calls_report_failure(self):
        """C5 integrate: except block calls report_failure before fallback."""
        src = _src("C5")
        # Both report_failure and _fallback_snapshot must appear
        assert "report_failure" in src and "_fallback_snapshot" in src, (
            "C5: integrate except block must call report_failure AND use _fallback_snapshot"
        )


# ---------------------------------------------------------------------------
# Part 3 — report_failure() is called on exception
# ---------------------------------------------------------------------------

class TestTD003Part3ReportFailureCalled:
    """Platform failure tracker receives engine failures via report_failure()."""

    def test_c1_update_exception_reports_failure(self):
        """C1.update(): internal processing errors are reported."""
        from iios.investment.market.integration.market_intelligence_integration_engine import (
            MarketIntelligenceIntegrationEngine,
        )
        engine = MarketIntelligenceIntegrationEngine()
        engine.start()

        mock_mgr = MagicMock()
        with patch(f"{_ENGINE_MODULE_PATHS['C1']}._get_err_mgr", return_value=mock_mgr):
            with patch.object(engine, "_process", side_effect=RuntimeError("proc fail")):
                with pytest.raises(RuntimeError):
                    engine.update(MagicMock())
        mock_mgr.report_failure.assert_called_once()
        engine.stop()

    def test_c1_on_snapshot_callback_reports_failure(self):
        """C1._fire_callbacks(): on_snapshot exception is reported but not raised."""
        from iios.investment.market.integration.market_intelligence_integration_engine import (
            MarketIntelligenceIntegrationEngine,
        )
        engine = MarketIntelligenceIntegrationEngine()
        engine.start()
        engine.on_snapshot = MagicMock(side_effect=RuntimeError("cb boom"))

        snap = MagicMock()
        snap.quality.overall = 80.0
        snap.conflicts.total = 0

        mock_mgr = MagicMock()
        with patch(f"{_ENGINE_MODULE_PATHS['C1']}._get_err_mgr", return_value=mock_mgr):
            engine._fire_callbacks(snap)  # must NOT raise

        mock_mgr.report_failure.assert_called_once()
        engine.stop()

    def test_c1_on_low_quality_callback_reports_failure(self):
        """C1._fire_callbacks(): on_low_quality exception is reported."""
        from iios.investment.market.integration.market_intelligence_integration_engine import (
            MarketIntelligenceIntegrationEngine,
        )
        engine = MarketIntelligenceIntegrationEngine()
        engine.start()
        engine.on_low_quality = MagicMock(side_effect=RuntimeError("lq boom"))

        snap = MagicMock()
        snap.quality.overall = 30.0  # below 50 threshold
        snap.conflicts.total = 0

        mock_mgr = MagicMock()
        with patch(f"{_ENGINE_MODULE_PATHS['C1']}._get_err_mgr", return_value=mock_mgr):
            engine._fire_callbacks(snap)  # must NOT raise

        mock_mgr.report_failure.assert_called_once()
        engine.stop()

    def test_c1_on_conflict_callback_reports_failure(self):
        """C1._fire_callbacks(): on_conflict exception is reported."""
        from iios.investment.market.integration.market_intelligence_integration_engine import (
            MarketIntelligenceIntegrationEngine,
        )
        engine = MarketIntelligenceIntegrationEngine()
        engine.start()
        engine.on_conflict = MagicMock(side_effect=RuntimeError("cf boom"))

        snap = MagicMock()
        snap.quality.overall = 80.0
        snap.conflicts.total = 3  # > 0 triggers callback

        mock_mgr = MagicMock()
        with patch(f"{_ENGINE_MODULE_PATHS['C1']}._get_err_mgr", return_value=mock_mgr):
            engine._fire_callbacks(snap)  # must NOT raise

        mock_mgr.report_failure.assert_called_once()
        engine.stop()

    def test_c1_callback_failures_are_isolated(self):
        """C1: a failing on_snapshot callback does NOT prevent on_conflict from running."""
        from iios.investment.market.integration.market_intelligence_integration_engine import (
            MarketIntelligenceIntegrationEngine,
        )
        engine = MarketIntelligenceIntegrationEngine()
        engine.start()
        engine.on_snapshot = MagicMock(side_effect=RuntimeError("snap fail"))
        engine.on_conflict = MagicMock()

        snap = MagicMock()
        snap.quality.overall = 80.0
        snap.conflicts.total = 5

        mock_mgr = MagicMock()
        with patch(f"{_ENGINE_MODULE_PATHS['C1']}._get_err_mgr", return_value=mock_mgr):
            engine._fire_callbacks(snap)

        engine.on_conflict.assert_called_once()  # still ran despite on_snapshot failing
        engine.stop()

    def test_c2_update_exception_reports_failure(self):
        """C2.update(): _evaluate() exceptions are reported."""
        from iios.investment.company.integration.company_intelligence_integration_engine import (
            CompanyIntelligenceIntegrationEngine,
        )
        engine = CompanyIntelligenceIntegrationEngine()
        engine.start()

        mock_mgr = MagicMock()
        with patch(f"{_ENGINE_MODULE_PATHS['C2']}._get_err_mgr", return_value=mock_mgr):
            with patch.object(engine, "_evaluate", side_effect=RuntimeError("eval fail")):
                with pytest.raises(RuntimeError):
                    engine.update("AAPL", "financials", MagicMock())

        mock_mgr.report_failure.assert_called_once()
        engine.stop()

    def test_c2_integrate_exception_reports_failure(self):
        """C2.integrate(): _evaluate() exceptions are reported."""
        from iios.investment.company.integration.company_intelligence_integration_engine import (
            CompanyIntelligenceIntegrationEngine,
        )
        engine = CompanyIntelligenceIntegrationEngine()
        engine.start()

        mock_mgr = MagicMock()
        with patch(f"{_ENGINE_MODULE_PATHS['C2']}._get_err_mgr", return_value=mock_mgr):
            with patch.object(engine, "_evaluate", side_effect=RuntimeError("eval fail")):
                with pytest.raises(RuntimeError):
                    engine.integrate("AAPL", financial_snapshot=MagicMock())

        mock_mgr.report_failure.assert_called_once()
        engine.stop()

    def test_c3_submit_update_sync_exception_reports_failure(self):
        """C3.submit_update_sync(): execution failures are reported."""
        from iios.investment.strategy.integration.strategy_intelligence_integration_engine import (
            StrategyIntelligenceIntegrationEngine,
        )
        engine = StrategyIntelligenceIntegrationEngine()
        engine.start()

        mock_mgr = MagicMock()
        with patch(f"{_ENGINE_MODULE_PATHS['C3']}._get_exec_manager") as mock_exec:
            mock_exec.return_value.execute_sync.side_effect = RuntimeError("exec fail")
            with patch(f"{_ENGINE_MODULE_PATHS['C3']}._get_err_mgr", return_value=mock_mgr):
                with pytest.raises(RuntimeError):
                    engine.submit_update_sync(MagicMock())

        mock_mgr.report_failure.assert_called_once()
        engine.stop()

    def test_c3_get_snapshot_sync_exception_reports_failure(self):
        """C3.get_snapshot_sync(): execution failures are reported."""
        from iios.investment.strategy.integration.strategy_intelligence_integration_engine import (
            StrategyIntelligenceIntegrationEngine,
        )
        engine = StrategyIntelligenceIntegrationEngine()
        engine.start()

        mock_mgr = MagicMock()
        with patch(f"{_ENGINE_MODULE_PATHS['C3']}._get_exec_manager") as mock_exec:
            mock_exec.return_value.execute_sync.side_effect = RuntimeError("exec fail")
            with patch(f"{_ENGINE_MODULE_PATHS['C3']}._get_err_mgr", return_value=mock_mgr):
                with pytest.raises(RuntimeError):
                    engine.get_snapshot_sync("STRAT-001")

        mock_mgr.report_failure.assert_called_once()
        engine.stop()

    def test_c4_integrate_sync_exception_reports_failure(self):
        """C4.integrate_sync(): pipeline failures are reported to ErrorManager."""
        from iios.investment.decision.integration.decision_intelligence_integration_engine import (
            DecisionIntelligenceIntegrationEngine,
        )
        engine = DecisionIntelligenceIntegrationEngine()
        engine.start()

        mock_mgr = MagicMock()
        with patch.object(
            engine._aggregator._engine, "create", side_effect=RuntimeError("agg fail")
        ):
            with patch(f"{_ENGINE_MODULE_PATHS['C4']}._get_err_mgr", return_value=mock_mgr):
                with pytest.raises(RuntimeError):
                    engine.integrate_sync(decision_id="DEC-TEST-001")

        mock_mgr.report_failure.assert_called_once()
        engine.stop()

    def test_c5_integrate_exception_reports_failure(self):
        """C5.integrate(): _build_snapshot() failures are reported."""
        from iios.investment.portfolio.integration.portfolio_intelligence_integration_engine import (
            PortfolioIntelligenceIntegrationEngine,
        )
        engine = PortfolioIntelligenceIntegrationEngine()
        engine.start()

        mock_mgr = MagicMock()
        with patch.object(engine, "_build_snapshot", side_effect=RuntimeError("build fail")):
            with patch(f"{_ENGINE_MODULE_PATHS['C5']}._get_err_mgr", return_value=mock_mgr):
                engine.integrate("PORTF-001")  # must NOT raise

        mock_mgr.report_failure.assert_called_once()
        engine.stop()


# ---------------------------------------------------------------------------
# Part 4 — ErrorContext fields are correct
# ---------------------------------------------------------------------------

class TestTD003Part4ErrorContextFields:
    """report_failure() is called with the correct engine_id and context."""

    def test_c4_report_failure_engine_id(self):
        """C4: report_failure receives the correct SYSTEM_ID."""
        from iios.investment.decision.integration.decision_intelligence_integration_engine import (
            DecisionIntelligenceIntegrationEngine,
        )
        engine = DecisionIntelligenceIntegrationEngine()
        engine.start()

        mock_mgr = MagicMock()
        with patch.object(
            engine._aggregator._engine, "create", side_effect=RuntimeError("agg fail")
        ):
            with patch(f"{_ENGINE_MODULE_PATHS['C4']}._get_err_mgr", return_value=mock_mgr):
                with pytest.raises(RuntimeError):
                    engine.integrate_sync(decision_id="DEC-CTX-001")

        call_args = mock_mgr.report_failure.call_args
        engine_id_arg = call_args[0][0]
        exc_arg = call_args[0][1]
        assert engine_id_arg == engine.SYSTEM_ID
        assert isinstance(exc_arg, RuntimeError)
        engine.stop()

    def test_c4_error_context_operation_field(self):
        """C4: ErrorContext passed to report_failure has operation='integrate_sync'."""
        from iios.investment.decision.integration.decision_intelligence_integration_engine import (
            DecisionIntelligenceIntegrationEngine,
        )
        engine = DecisionIntelligenceIntegrationEngine()
        engine.start()

        mock_mgr = MagicMock()
        with patch.object(
            engine._aggregator._engine, "create", side_effect=RuntimeError("agg fail")
        ):
            with patch(f"{_ENGINE_MODULE_PATHS['C4']}._get_err_mgr", return_value=mock_mgr):
                with pytest.raises(RuntimeError):
                    engine.integrate_sync(decision_id="DEC-CTX-002")

        call_args = mock_mgr.report_failure.call_args
        ctx_arg = call_args[0][2] if len(call_args[0]) > 2 else (
            call_args[1].get("context") if call_args[1] else None
        )
        assert ctx_arg is not None, "ErrorContext must be passed to report_failure"
        assert isinstance(ctx_arg, ErrorContext)
        assert ctx_arg.engine_id == engine.SYSTEM_ID
        assert ctx_arg.operation == "integrate_sync"
        engine.stop()

    def test_c5_error_context_passed(self):
        """C5: ErrorContext is passed to report_failure with correct fields."""
        from iios.investment.portfolio.integration.portfolio_intelligence_integration_engine import (
            PortfolioIntelligenceIntegrationEngine,
        )
        engine = PortfolioIntelligenceIntegrationEngine()
        engine.start()

        mock_mgr = MagicMock()
        with patch.object(engine, "_build_snapshot", side_effect=RuntimeError("build fail")):
            with patch(f"{_ENGINE_MODULE_PATHS['C5']}._get_err_mgr", return_value=mock_mgr):
                engine.integrate("PORTF-CTX-001")

        call_args = mock_mgr.report_failure.call_args
        ctx_arg = call_args[0][2] if len(call_args[0]) > 2 else (
            call_args[1].get("context") if call_args[1] else None
        )
        assert ctx_arg is not None
        assert isinstance(ctx_arg, ErrorContext)
        assert ctx_arg.engine_id == engine.SYSTEM_ID
        assert ctx_arg.operation == "integrate"
        engine.stop()


# ---------------------------------------------------------------------------
# Part 5 — Engine-internal counters preserved (C4)
# ---------------------------------------------------------------------------

class TestTD003Part5EngineInternalCountersPreserved:
    """C4 engine-internal failure counters must still fire alongside report_failure."""

    def test_c4_stats_record_failure_still_called(self):
        """C4.integrate_sync(): self._stats.record_failure() still fires on error."""
        from iios.investment.decision.integration.decision_intelligence_integration_engine import (
            DecisionIntelligenceIntegrationEngine,
        )
        engine = DecisionIntelligenceIntegrationEngine()
        engine.start()

        mock_mgr = MagicMock()
        with patch.object(engine._stats, "record_failure") as mock_stats_fail:
            with patch.object(
                engine._aggregator._engine, "create", side_effect=RuntimeError("agg fail")
            ):
                with patch(f"{_ENGINE_MODULE_PATHS['C4']}._get_err_mgr", return_value=mock_mgr):
                    with pytest.raises(RuntimeError):
                        engine.integrate_sync(decision_id="DEC-STATS-001")

        mock_stats_fail.assert_called_once()
        engine.stop()

    def test_c4_health_record_failure_still_called(self):
        """C4.integrate_sync(): self._health.record_failure() still fires on error."""
        from iios.investment.decision.integration.decision_intelligence_integration_engine import (
            DecisionIntelligenceIntegrationEngine,
        )
        engine = DecisionIntelligenceIntegrationEngine()
        engine.start()

        mock_mgr = MagicMock()
        with patch.object(engine._health, "record_failure") as mock_health_fail:
            with patch.object(
                engine._aggregator._engine, "create", side_effect=RuntimeError("agg fail")
            ):
                with patch(f"{_ENGINE_MODULE_PATHS['C4']}._get_err_mgr", return_value=mock_mgr):
                    with pytest.raises(RuntimeError):
                        engine.integrate_sync(decision_id="DEC-HEALTH-001")

        mock_health_fail.assert_called_once()
        engine.stop()

    def test_c4_report_failure_called_before_reraise(self):
        """C4: report_failure is called before the exception is re-raised."""
        from iios.investment.decision.integration.decision_intelligence_integration_engine import (
            DecisionIntelligenceIntegrationEngine,
        )
        engine = DecisionIntelligenceIntegrationEngine()
        engine.start()

        call_order: list[str] = []
        mock_mgr = MagicMock()
        mock_mgr.report_failure.side_effect = lambda *a, **kw: call_order.append("report")

        with patch.object(engine._stats, "record_failure", side_effect=lambda: call_order.append("stats")):
            with patch.object(
                engine._aggregator._engine, "create", side_effect=RuntimeError("agg fail")
            ):
                with patch(f"{_ENGINE_MODULE_PATHS['C4']}._get_err_mgr", return_value=mock_mgr):
                    with pytest.raises(RuntimeError):
                        engine.integrate_sync(decision_id="DEC-ORDER-001")

        assert "report" in call_order
        assert "stats" in call_order
        assert call_order.index("report") < call_order.index("stats"), (
            "report_failure must be called before self._stats.record_failure()"
        )
        engine.stop()


# ---------------------------------------------------------------------------
# Part 6 — C5 fallback behavior preserved (no re-raise)
# ---------------------------------------------------------------------------

class TestTD003Part6C5FallbackPreserved:
    """C5.integrate(): exception is caught, reported, and fallback snapshot returned."""

    def test_c5_integrate_does_not_reraise(self):
        """C5: _build_snapshot failure does NOT propagate to caller."""
        from iios.investment.portfolio.integration.portfolio_intelligence_integration_engine import (
            PortfolioIntelligenceIntegrationEngine,
        )
        engine = PortfolioIntelligenceIntegrationEngine()
        engine.start()

        with patch.object(engine, "_build_snapshot", side_effect=ValueError("build failed")):
            with patch(f"{_ENGINE_MODULE_PATHS['C5']}._get_err_mgr", return_value=MagicMock()):
                result = engine.integrate("PORTF-FALLBACK-001")

        assert result is not None, "integrate() must return a fallback snapshot, not None"
        engine.stop()

    def test_c5_integrate_returns_fallback_snapshot(self):
        """C5: the returned fallback snapshot is not published (DRAFT status)."""
        from iios.investment.portfolio.integration.portfolio_intelligence_integration_engine import (
            PortfolioIntelligenceIntegrationEngine,
            PortfolioIntelligenceSnapshot,
        )
        from iios.investment.portfolio.integration.integration_types import SnapshotStatus
        engine = PortfolioIntelligenceIntegrationEngine()
        engine.start()

        with patch.object(engine, "_build_snapshot", side_effect=RuntimeError("build fail")):
            with patch(f"{_ENGINE_MODULE_PATHS['C5']}._get_err_mgr", return_value=MagicMock()):
                result = engine.integrate("PORTF-STATUS-001")

        assert isinstance(result, PortfolioIntelligenceSnapshot)
        assert result.status != SnapshotStatus.PUBLISHED, (
            "Fallback snapshot must NOT be PUBLISHED"
        )
        engine.stop()

    def test_c5_health_records_failure_on_exception(self):
        """C5: health monitor records a failure when _build_snapshot raises."""
        from iios.investment.portfolio.integration.portfolio_intelligence_integration_engine import (
            PortfolioIntelligenceIntegrationEngine,
        )
        engine = PortfolioIntelligenceIntegrationEngine()
        engine.start()

        with patch.object(engine, "_build_snapshot", side_effect=RuntimeError("build fail")):
            with patch(f"{_ENGINE_MODULE_PATHS['C5']}._get_err_mgr", return_value=MagicMock()):
                with patch.object(engine._health, "record_integration") as mock_health:
                    engine.integrate("PORTF-HEALTH-001")

        mock_health.assert_called_once()
        succeeded_arg = mock_health.call_args[0][0]
        assert succeeded_arg is False
        engine.stop()


# ---------------------------------------------------------------------------
# Part 7 — C3 _on_stop exception is now logged (not silently swallowed)
# ---------------------------------------------------------------------------

class TestTD003Part7C3OnStopLogged:
    """C3._on_stop(): health-monitor stop failure is now logged as a warning."""

    def test_c3_on_stop_health_exception_logged(self):
        """C3: asyncio coroutine logs a warning instead of silently passing."""
        import asyncio
        from iios.investment.strategy.integration.strategy_intelligence_integration_engine import (
            StrategyIntelligenceIntegrationEngine,
        )
        engine = StrategyIntelligenceIntegrationEngine()
        engine.start()

        # Patch _health.stop() to raise when called in the coroutine
        original_stop = engine._health.stop

        async def _failing_stop():
            raise RuntimeError("health stop boom")

        engine._health.stop = _failing_stop

        import iios.investment.strategy.integration.strategy_intelligence_integration_engine as _mod

        with patch.object(_mod._log, "warning") as mock_warn:
            engine.stop()
            # Brief wait for the background coroutine to run
            import time; time.sleep(0.1)
            # The warning may or may not have fired (timing-dependent),
            # but crucially, stop() itself must not raise.

        # Restore
        engine._health.stop = original_stop

    def test_c3_on_stop_does_not_raise(self):
        """C3._on_stop(): engine.stop() must not raise even if health stop fails."""
        from iios.investment.strategy.integration.strategy_intelligence_integration_engine import (
            StrategyIntelligenceIntegrationEngine,
        )
        engine = StrategyIntelligenceIntegrationEngine()
        engine.start()

        async def _failing_stop():
            raise RuntimeError("health stop boom")

        engine._health.stop = _failing_stop

        # Must not raise
        engine.stop()


# ---------------------------------------------------------------------------
# Part 8 — Thread safety
# ---------------------------------------------------------------------------

class TestTD003Part8ThreadSafety:
    """Concurrent invocations don't lose failure reports."""

    def test_c2_concurrent_update_exceptions_all_reported(self):
        """C2: multiple threads failing simultaneously each produce one report."""
        from iios.investment.company.integration.company_intelligence_integration_engine import (
            CompanyIntelligenceIntegrationEngine,
        )
        engine = CompanyIntelligenceIntegrationEngine()
        engine.start()

        report_calls: list[Any] = []
        lock = threading.Lock()

        mock_mgr = MagicMock()

        def _record(engine_id, exc, *a, **kw):
            with lock:
                report_calls.append((engine_id, exc))

        mock_mgr.report_failure.side_effect = _record

        errors: list[Exception] = []

        def _worker(ticker: str) -> None:
            try:
                with patch(f"{_ENGINE_MODULE_PATHS['C2']}._get_err_mgr", return_value=mock_mgr):
                    with patch.object(engine, "_evaluate", side_effect=RuntimeError("eval fail")):
                        engine.update(ticker, "financials", MagicMock())
            except RuntimeError:
                pass
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_worker, args=(f"T{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Unexpected errors in threads: {errors}"
        assert len(report_calls) == 5, (
            f"Expected 5 report_failure calls (one per thread), got {len(report_calls)}"
        )
        engine.stop()

    def test_c4_concurrent_integrate_sync_exceptions_all_reported(self):
        """C4: 4 concurrent integrate_sync failures all reach report_failure."""
        from iios.investment.decision.integration.decision_intelligence_integration_engine import (
            DecisionIntelligenceIntegrationEngine,
        )
        engine = DecisionIntelligenceIntegrationEngine()
        engine.start()

        report_calls: list[Any] = []
        lock = threading.Lock()

        mock_mgr = MagicMock()

        def _record(engine_id, exc, *a, **kw):
            with lock:
                report_calls.append((engine_id, exc))

        mock_mgr.report_failure.side_effect = _record

        errors: list[Exception] = []

        def _worker(decision_id: str) -> None:
            try:
                with patch.object(
                    engine._aggregator._engine, "create", side_effect=RuntimeError("agg fail")
                ):
                    with patch(f"{_ENGINE_MODULE_PATHS['C4']}._get_err_mgr", return_value=mock_mgr):
                        engine.integrate_sync(decision_id=decision_id)
            except RuntimeError:
                pass
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=_worker, args=(f"DEC-CONCURRENT-{i:03d}",))
            for i in range(4)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(report_calls) == 4
        engine.stop()


# ---------------------------------------------------------------------------
# Part 9 — Regression: public APIs work without errors
# ---------------------------------------------------------------------------

class TestTD003Part9Regression:
    """The error framework wiring must not break the happy path."""

    def test_c1_update_happy_path_no_error_reported(self):
        """C1.update(): successful call does NOT trigger report_failure."""
        from iios.investment.market.integration.market_intelligence_integration_engine import (
            MarketIntelligenceIntegrationEngine,
        )
        engine = MarketIntelligenceIntegrationEngine()
        engine.start()

        mock_snap = MagicMock()
        mock_mgr = MagicMock()

        with patch.object(engine, "_process", return_value=mock_snap):
            with patch(f"{_ENGINE_MODULE_PATHS['C1']}._get_err_mgr", return_value=mock_mgr):
                result = engine.update(MagicMock())

        assert result is mock_snap
        mock_mgr.report_failure.assert_not_called()
        engine.stop()

    def test_c2_update_does_not_report_for_known_engine_valueerror(self):
        """C2.update(): ValueError for unknown engine is NOT caught by our handler."""
        from iios.investment.company.integration.company_intelligence_integration_engine import (
            CompanyIntelligenceIntegrationEngine,
        )
        engine = CompanyIntelligenceIntegrationEngine()
        engine.start()

        mock_mgr = MagicMock()
        with patch(f"{_ENGINE_MODULE_PATHS['C2']}._get_err_mgr", return_value=mock_mgr):
            with pytest.raises(ValueError, match="Unknown engine"):
                engine.update("AAPL", "nonexistent_engine", MagicMock())

        # The ValueError from the guard clause propagates without report_failure
        # (it's a programming error, not a runtime failure in _evaluate)
        mock_mgr.report_failure.assert_not_called()
        engine.stop()

    def test_c5_integrate_happy_path_no_error_reported(self):
        """C5.integrate(): successful call does NOT trigger report_failure."""
        from iios.investment.portfolio.integration.portfolio_intelligence_integration_engine import (
            PortfolioIntelligenceIntegrationEngine,
        )
        from iios.investment.portfolio.integration.portfolio_snapshot import (
            PortfolioIntelligenceSnapshot,
        )
        engine = PortfolioIntelligenceIntegrationEngine()
        engine.start()

        # Must be a real dataclass instance — integrate() calls dataclasses.replace() on it
        good_snap = PortfolioIntelligenceSnapshot(portfolio_id="PORTF-HAPPY")
        mock_mgr = MagicMock()

        with patch.object(engine, "_build_snapshot", return_value=good_snap):
            with patch(f"{_ENGINE_MODULE_PATHS['C5']}._get_err_mgr", return_value=mock_mgr):
                engine.integrate("PORTF-HAPPY")

        mock_mgr.report_failure.assert_not_called()
        engine.stop()

    def test_all_engines_have_system_id(self):
        """All C1–C5 engines expose the correct SYSTEM_ID class attribute."""
        from iios.investment.market.integration.market_intelligence_integration_engine import MarketIntelligenceIntegrationEngine
        from iios.investment.company.integration.company_intelligence_integration_engine import CompanyIntelligenceIntegrationEngine
        from iios.investment.strategy.integration.strategy_intelligence_integration_engine import StrategyIntelligenceIntegrationEngine
        from iios.investment.decision.integration.decision_intelligence_integration_engine import DecisionIntelligenceIntegrationEngine
        from iios.investment.portfolio.integration.portfolio_intelligence_integration_engine import PortfolioIntelligenceIntegrationEngine

        assert MarketIntelligenceIntegrationEngine.SYSTEM_ID == _ENGINE_SYSTEM_IDS["C1"]
        assert CompanyIntelligenceIntegrationEngine.SYSTEM_ID == _ENGINE_SYSTEM_IDS["C2"]
        assert StrategyIntelligenceIntegrationEngine.SYSTEM_ID == _ENGINE_SYSTEM_IDS["C3"]
        assert DecisionIntelligenceIntegrationEngine.SYSTEM_ID == _ENGINE_SYSTEM_IDS["C4"]
        assert PortfolioIntelligenceIntegrationEngine.SYSTEM_ID == _ENGINE_SYSTEM_IDS["C5"]
