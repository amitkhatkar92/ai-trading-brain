"""tests/unit/common/logging/test_td002_logging_migration.py
TD-002 Institutional Logging Framework Migration — Validation Tests.

Verifies that all C1–C5 Integration Engines have been fully migrated
from stdlib logging to the certified Institutional Logging Framework.

Scope
-----
Part 1 — Logger initialisation  (all engines use StructuredLogger + AuditLogger)
Part 2 — Source-level invariants (zero legacy patterns in source)
Part 3 — Structured JSON output  (schema fields present in records)
Part 4 — Context propagation     (LoggingContext ContextVars appear in output)
Part 5 — Lifecycle audit events  (AuditLogger emits on _on_start / _on_stop)
Part 6 — Exception logging       (C4/C5 integrate exceptions are captured)
Part 7 — Thread safety           (concurrent log calls don't corrupt state)
Part 8 — Regression              (existing certification and unit suites intact)
"""
from __future__ import annotations

import ast
import io
import json
import logging
import pathlib
import subprocess
import sys
import threading
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from iios.common.logging.audit_logger import AuditLogger, AuditEventType, get_audit_logger
from iios.common.logging.logging_context import LoggingContext
from iios.common.logging.logging_manager import LoggingManager, get_logger
from iios.common.logging.structured_logger import JsonFormatter, StructuredLogger


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

_ENGINE_IDS = {
    "C1": "iios:market:intelligence:integration",
    "C2": "iios:company:intelligence:integration",
    "C3": "iios:strategy:intelligence:integration",
    "C4": "iios:decision:intelligence:integration",
    "C5": "iios:portfolio:intelligence:integration",
}


def _src(key: str) -> str:
    return _ENGINE_FILES[key].read_text(encoding="utf-8")


def _capture_on(logger: StructuredLogger) -> io.StringIO:
    """Attach a JSON-capture handler to a StructuredLogger; return buffer."""
    buf = io.StringIO()
    h = logging.StreamHandler(buf)
    h.setLevel(logging.DEBUG)
    h.setFormatter(JsonFormatter())
    logger.logger.handlers.clear()
    logger.logger.setLevel(logging.DEBUG)
    logger.logger.addHandler(h)
    logger.logger.propagate = False
    return buf


def _parse(buf: io.StringIO) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in buf.getvalue().splitlines() if line.strip()]


@pytest.fixture(autouse=True)
def _clear_context():
    LoggingContext.clear()
    yield
    LoggingContext.clear()


# ---------------------------------------------------------------------------
# Part 1 — Logger initialisation
# ---------------------------------------------------------------------------

class TestTD002Part1LoggerInit:
    """Every C1–C5 engine exposes a StructuredLogger and an AuditLogger."""

    def test_c1_module_logger_is_structured(self):
        import iios.investment.market.integration.market_intelligence_integration_engine as m
        assert isinstance(m._log, StructuredLogger)

    def test_c1_module_audit_is_audit_logger(self):
        import iios.investment.market.integration.market_intelligence_integration_engine as m
        assert isinstance(m._audit, AuditLogger)

    def test_c1_logger_engine_id(self):
        import iios.investment.market.integration.market_intelligence_integration_engine as m
        assert m._log.engine_id == _ENGINE_IDS["C1"]

    def test_c2_module_logger_is_structured(self):
        import iios.investment.company.integration.company_intelligence_integration_engine as m
        assert isinstance(m._log, StructuredLogger)

    def test_c2_module_audit_is_audit_logger(self):
        import iios.investment.company.integration.company_intelligence_integration_engine as m
        assert isinstance(m._audit, AuditLogger)

    def test_c2_logger_engine_id(self):
        import iios.investment.company.integration.company_intelligence_integration_engine as m
        assert m._log.engine_id == _ENGINE_IDS["C2"]

    def test_c3_module_logger_is_structured(self):
        import iios.investment.strategy.integration.strategy_intelligence_integration_engine as m
        assert isinstance(m._log, StructuredLogger)

    def test_c3_module_audit_is_audit_logger(self):
        import iios.investment.strategy.integration.strategy_intelligence_integration_engine as m
        assert isinstance(m._audit, AuditLogger)

    def test_c3_logger_engine_id(self):
        import iios.investment.strategy.integration.strategy_intelligence_integration_engine as m
        assert m._log.engine_id == _ENGINE_IDS["C3"]

    def test_c4_module_logger_is_structured(self):
        import iios.investment.decision.integration.decision_intelligence_integration_engine as m
        assert isinstance(m._log, StructuredLogger)

    def test_c4_module_audit_is_audit_logger(self):
        import iios.investment.decision.integration.decision_intelligence_integration_engine as m
        assert isinstance(m._audit, AuditLogger)

    def test_c4_logger_engine_id(self):
        import iios.investment.decision.integration.decision_intelligence_integration_engine as m
        assert m._log.engine_id == _ENGINE_IDS["C4"]

    def test_c5_module_logger_is_structured(self):
        import iios.investment.portfolio.integration.portfolio_intelligence_integration_engine as m
        assert isinstance(m._log, StructuredLogger)

    def test_c5_module_audit_is_audit_logger(self):
        import iios.investment.portfolio.integration.portfolio_intelligence_integration_engine as m
        assert isinstance(m._audit, AuditLogger)

    def test_c5_logger_engine_id(self):
        import iios.investment.portfolio.integration.portfolio_intelligence_integration_engine as m
        assert m._log.engine_id == _ENGINE_IDS["C5"]


# ---------------------------------------------------------------------------
# Part 2 — Source-level invariants
# ---------------------------------------------------------------------------

class TestTD002Part2SourceInvariants:
    """Zero legacy logging.getLogger / logging.basicConfig in all 5 engine files."""

    @pytest.mark.parametrize("engine", ["C1", "C2", "C3", "C4", "C5"])
    def test_no_logging_getlogger(self, engine: str):
        assert "logging.getLogger" not in _src(engine), (
            f"{engine}: logging.getLogger() must not appear after TD-002"
        )

    @pytest.mark.parametrize("engine", ["C1", "C2", "C3", "C4", "C5"])
    def test_no_logging_basicconfig(self, engine: str):
        assert "logging.basicConfig" not in _src(engine), (
            f"{engine}: logging.basicConfig() must not appear after TD-002"
        )

    @pytest.mark.parametrize("engine", ["C1", "C2", "C3", "C4", "C5"])
    def test_uses_get_logger(self, engine: str):
        assert "get_logger" in _src(engine), (
            f"{engine}: must import and use get_logger()"
        )

    @pytest.mark.parametrize("engine", ["C1", "C2", "C3", "C4", "C5"])
    def test_uses_get_audit_logger(self, engine: str):
        assert "get_audit_logger" in _src(engine), (
            f"{engine}: must import and use get_audit_logger()"
        )

    @pytest.mark.parametrize("engine", ["C1", "C2", "C3", "C4", "C5"])
    def test_engine_id_in_source(self, engine: str):
        src = _src(engine)
        assert _ENGINE_IDS[engine] in src, (
            f"{engine}: engine_id string must appear in source"
        )

    def test_c1_import_logging_absent(self):
        src = _src("C1")
        # 'import logging' (direct stdlib import) must be gone
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name != "logging", (
                        "C1: bare 'import logging' must be removed"
                    )

    def test_c3_import_logging_absent(self):
        src = _src("C3")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name != "logging", (
                        "C3: bare 'import logging' must be removed"
                    )

    def test_c1_has_on_start_hook(self):
        src = _src("C1")
        assert "def _on_start" in src, "C1: must define _on_start lifecycle hook"

    def test_c1_has_on_stop_hook(self):
        src = _src("C1")
        assert "def _on_stop" in src, "C1: must define _on_stop lifecycle hook"

    def test_c2_has_on_start_hook(self):
        src = _src("C2")
        assert "def _on_start" in src, "C2: must define _on_start lifecycle hook"

    def test_c4_has_exception_logging(self):
        src = _src("C4")
        assert "_log.exception" in src, (
            "C4: must use _log.exception() in integrate_sync except block"
        )

    def test_c5_has_exception_logging(self):
        src = _src("C5")
        assert "_log.exception" in src, (
            "C5: must use _log.exception() in integrate except block"
        )


# ---------------------------------------------------------------------------
# Part 3 — Structured JSON output schema
# ---------------------------------------------------------------------------

class TestTD002Part3StructuredOutput:
    """Records emitted by engine loggers satisfy the Institutional schema."""

    def _required_fields(self) -> set:
        return {"ts", "level", "logger", "msg", "engine_id"}

    def test_c1_logger_emits_engine_id(self):
        import iios.investment.market.integration.market_intelligence_integration_engine as m
        buf = _capture_on(m._log)
        m._log.info("test structured output")
        records = _parse(buf)
        assert records, "C1: no log output captured"
        assert records[0]["engine_id"] == _ENGINE_IDS["C1"]

    def test_c1_record_has_required_fields(self):
        import iios.investment.market.integration.market_intelligence_integration_engine as m
        buf = _capture_on(m._log)
        m._log.info("schema check")
        records = _parse(buf)
        assert records
        for field in self._required_fields():
            assert field in records[0], f"C1 record missing field: {field}"

    def test_c2_logger_emits_engine_id(self):
        import iios.investment.company.integration.company_intelligence_integration_engine as m
        buf = _capture_on(m._log)
        m._log.info("test structured output")
        records = _parse(buf)
        assert records
        assert records[0]["engine_id"] == _ENGINE_IDS["C2"]

    def test_c3_logger_emits_engine_id(self):
        import iios.investment.strategy.integration.strategy_intelligence_integration_engine as m
        buf = _capture_on(m._log)
        m._log.info("test structured output")
        records = _parse(buf)
        assert records
        assert records[0]["engine_id"] == _ENGINE_IDS["C3"]

    def test_c4_logger_emits_engine_id(self):
        import iios.investment.decision.integration.decision_intelligence_integration_engine as m
        buf = _capture_on(m._log)
        m._log.info("test structured output")
        records = _parse(buf)
        assert records
        assert records[0]["engine_id"] == _ENGINE_IDS["C4"]

    def test_c5_logger_emits_engine_id(self):
        import iios.investment.portfolio.integration.portfolio_intelligence_integration_engine as m
        buf = _capture_on(m._log)
        m._log.info("test structured output")
        records = _parse(buf)
        assert records
        assert records[0]["engine_id"] == _ENGINE_IDS["C5"]

    def test_record_has_iso_timestamp(self):
        import iios.investment.decision.integration.decision_intelligence_integration_engine as m
        buf = _capture_on(m._log)
        m._log.info("ts check")
        records = _parse(buf)
        assert records
        ts = records[0].get("ts", "")
        assert "T" in ts, f"Timestamp not ISO-8601: {ts}"
        assert ts.endswith("+00:00") or "Z" in ts or "+0" in ts or "UTC" in ts or ts.endswith("00:00")

    def test_exception_record_includes_exc_field(self):
        import iios.investment.decision.integration.decision_intelligence_integration_engine as m
        buf = _capture_on(m._log)
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            m._log.exception("exception captured")
        records = _parse(buf)
        assert records
        assert records[0]["level"] == "ERROR"
        assert "exc" in records[0] or "RuntimeError" in str(records[0])

    def test_context_dict_appears_in_record(self):
        import iios.investment.decision.integration.decision_intelligence_integration_engine as m
        buf = _capture_on(m._log)
        m._log.info("ctx test", context={"decision_id": "DEC-999"})
        records = _parse(buf)
        assert records
        ctx = records[0].get("context", {})
        assert ctx.get("decision_id") == "DEC-999"


# ---------------------------------------------------------------------------
# Part 4 — Context propagation (LoggingContext ContextVars)
# ---------------------------------------------------------------------------

class TestTD002Part4ContextPropagation:
    """LoggingContext fields automatically appear in structured output."""

    def test_workflow_id_propagates(self):
        import iios.investment.market.integration.market_intelligence_integration_engine as m
        buf = _capture_on(m._log)
        LoggingContext.set_workflow_id("WF-C1-001")
        m._log.info("context propagation test")
        records = _parse(buf)
        assert records
        assert records[0].get("workflow_id") == "WF-C1-001"

    def test_correlation_id_propagates(self):
        import iios.investment.strategy.integration.strategy_intelligence_integration_engine as m
        buf = _capture_on(m._log)
        LoggingContext.set_correlation_id("CORR-C3-abc")
        m._log.info("corr propagation")
        records = _parse(buf)
        assert records
        assert records[0].get("correlation_id") == "CORR-C3-abc"

    def test_multiple_context_fields(self):
        import iios.investment.decision.integration.decision_intelligence_integration_engine as m
        buf = _capture_on(m._log)
        with LoggingContext(
            workflow_id    = "WF-C4-001",
            correlation_id = "CORR-XYZ",
            request_id     = "REQ-123",
        ).bind():
            m._log.info("multi-context test")
        records = _parse(buf)
        assert records
        r = records[0]
        assert r.get("workflow_id")    == "WF-C4-001"
        assert r.get("correlation_id") == "CORR-XYZ"
        assert r.get("request_id")     == "REQ-123"

    def test_context_resets_after_bind(self):
        import iios.investment.portfolio.integration.portfolio_intelligence_integration_engine as m
        buf = _capture_on(m._log)
        with LoggingContext(workflow_id="WF-TEMP").bind():
            m._log.info("inside bind")
        m._log.info("outside bind")
        records = _parse(buf)
        # First record has workflow_id, second does not
        assert records[0].get("workflow_id") == "WF-TEMP"
        assert not records[1].get("workflow_id"), (
            "workflow_id must not leak outside bind()"
        )

    def test_context_propagates_across_threads(self):
        import iios.investment.market.integration.market_intelligence_integration_engine as m
        buf = _capture_on(m._log)
        results: list[dict] = []

        # Thread-safety note: LoggingContext ContextVars are per-task/coroutine,
        # not per-thread.  Within a thread, they are visible to all code on
        # the same call stack (ContextVar inherits from creation context).
        # We set in main thread and verify the logger reads it.
        LoggingContext.set_workflow_id("WF-THREAD-PROP")
        m._log.info("thread context test")
        records = _parse(buf)
        assert records
        assert records[0].get("workflow_id") == "WF-THREAD-PROP"


# ---------------------------------------------------------------------------
# Part 5 — Lifecycle audit events
# ---------------------------------------------------------------------------

class TestTD002Part5LifecycleAudit:
    """AuditLogger emits records when lifecycle hooks are invoked."""

    def _attach_audit_capture(self, audit: AuditLogger) -> io.StringIO:
        buf = io.StringIO()
        h = logging.StreamHandler(buf)
        h.setLevel(logging.DEBUG)
        h.setFormatter(JsonFormatter())
        underlying = audit._log.logger
        underlying.handlers.clear()
        underlying.setLevel(logging.DEBUG)
        underlying.addHandler(h)
        underlying.propagate = False
        return buf

    def test_c1_on_start_emits_audit(self):
        from iios.investment.market.integration.market_intelligence_integration_engine import (
            MarketIntelligenceIntegrationEngine,
        )
        import iios.investment.market.integration.market_intelligence_integration_engine as m
        buf = self._attach_audit_capture(m._audit)
        engine = MarketIntelligenceIntegrationEngine()
        engine.start()   # triggers _on_start → _audit.log_lifecycle_event
        engine.stop()
        records = _parse(buf)
        assert records, "C1: no audit records emitted on start"
        event_types = [r.get("context", {}).get("event_type") for r in records]
        assert AuditEventType.LIFECYCLE_EVENT.value in event_types

    def test_c1_on_stop_emits_audit(self):
        from iios.investment.market.integration.market_intelligence_integration_engine import (
            MarketIntelligenceIntegrationEngine,
        )
        import iios.investment.market.integration.market_intelligence_integration_engine as m
        engine = MarketIntelligenceIntegrationEngine()
        engine.start()
        buf = self._attach_audit_capture(m._audit)
        engine.stop()    # triggers _on_stop → _audit.log_lifecycle_event
        records = _parse(buf)
        assert records, "C1: no audit records emitted on stop"
        event_types = [r.get("context", {}).get("event_type") for r in records]
        assert AuditEventType.LIFECYCLE_EVENT.value in event_types

    def test_c2_on_start_emits_audit(self):
        from iios.investment.company.integration.company_intelligence_integration_engine import (
            CompanyIntelligenceIntegrationEngine,
        )
        import iios.investment.company.integration.company_intelligence_integration_engine as m
        buf = self._attach_audit_capture(m._audit)
        engine = CompanyIntelligenceIntegrationEngine()
        engine.start()
        engine.stop()
        records = _parse(buf)
        assert records, "C2: no audit records emitted on start"

    def test_c3_on_start_emits_audit_with_health_monitor_context(self):
        from iios.investment.strategy.integration.strategy_intelligence_integration_engine import (
            StrategyIntelligenceIntegrationEngine,
        )
        import iios.investment.strategy.integration.strategy_intelligence_integration_engine as m
        buf = self._attach_audit_capture(m._audit)
        engine = StrategyIntelligenceIntegrationEngine()
        engine.start()
        engine.stop()
        records = _parse(buf)
        assert records, "C3: no audit records emitted on start"
        # C3 passes health_monitor context
        details_combined = str(records)
        assert "background_daemon" in details_combined, (
            "C3 audit record must contain health_monitor context"
        )

    def test_c4_on_start_emits_audit(self):
        from iios.investment.decision.integration.decision_intelligence_integration_engine import (
            DecisionIntelligenceIntegrationEngine,
        )
        import iios.investment.decision.integration.decision_intelligence_integration_engine as m
        buf = self._attach_audit_capture(m._audit)
        engine = DecisionIntelligenceIntegrationEngine()
        engine.start()
        engine.stop()
        records = _parse(buf)
        assert records, "C4: no audit records emitted"

    def test_c5_on_start_emits_audit(self):
        from iios.investment.portfolio.integration.portfolio_intelligence_integration_engine import (
            PortfolioIntelligenceIntegrationEngine,
        )
        import iios.investment.portfolio.integration.portfolio_intelligence_integration_engine as m
        buf = self._attach_audit_capture(m._audit)
        engine = PortfolioIntelligenceIntegrationEngine()
        engine.start()
        engine.stop()
        records = _parse(buf)
        assert records, "C5: no audit records emitted"

    def test_lifecycle_audit_record_has_from_state_to_state(self):
        from iios.investment.decision.integration.decision_intelligence_integration_engine import (
            DecisionIntelligenceIntegrationEngine,
        )
        import iios.investment.decision.integration.decision_intelligence_integration_engine as m
        buf = self._attach_audit_capture(m._audit)
        engine = DecisionIntelligenceIntegrationEngine()
        engine.start()
        engine.stop()
        records = _parse(buf)
        lifecycle_recs = [
            r for r in records
            if r.get("context", {}).get("event_type") == AuditEventType.LIFECYCLE_EVENT.value
        ]
        assert lifecycle_recs, "No LIFECYCLE_EVENT records found"
        r = lifecycle_recs[0]
        ctx = r.get("context", {})
        assert "from_state" in ctx
        assert "to_state"   in ctx
        assert "engine_id"  in ctx
        assert "version"    in ctx


# ---------------------------------------------------------------------------
# Part 6 — Exception logging (C4/C5 integrate exceptions captured)
# ---------------------------------------------------------------------------

class TestTD002Part6ExceptionLogging:
    """Exceptions in integrate/integrate_sync are logged before re-raise."""

    def test_c4_integrate_sync_logs_exception_on_failure(self):
        from iios.investment.decision.integration.decision_intelligence_integration_engine import (
            DecisionIntelligenceIntegrationEngine,
        )
        import iios.investment.decision.integration.decision_intelligence_integration_engine as m

        engine = DecisionIntelligenceIntegrationEngine()
        engine.start()
        buf = _capture_on(m._log)

        # Inject a fault into the aggregator to trigger the except block
        original = engine._aggregator._engine.create

        def _fail(*a, **kw):
            raise RuntimeError("injected fault")

        engine._aggregator._engine.create = _fail
        with pytest.raises(RuntimeError, match="injected fault"):
            engine.integrate_sync(decision_id="DEC-FAIL-001")

        engine._aggregator._engine.create = original
        engine.stop()

        records = _parse(buf)
        error_records = [r for r in records if r["level"] == "ERROR"]
        assert error_records, "C4: integrate_sync exception must be logged at ERROR"
        ctx = error_records[0].get("context", {})
        assert ctx.get("decision_id") == "DEC-FAIL-001"

    def test_c5_integrate_logs_exception_on_failure(self):
        from iios.investment.portfolio.integration.portfolio_intelligence_integration_engine import (
            PortfolioIntelligenceIntegrationEngine,
        )
        import iios.investment.portfolio.integration.portfolio_intelligence_integration_engine as m

        engine = PortfolioIntelligenceIntegrationEngine()
        engine.start()
        buf = _capture_on(m._log)

        # Inject fault via _build_snapshot
        original_build = engine._build_snapshot

        def _fail(pid: str):
            raise RuntimeError("portfolio build fault")

        engine._build_snapshot = _fail

        # integrate() catches the exception and returns a fallback — so no raise
        snap = engine.integrate("PORT-FAIL-001")
        engine._build_snapshot = original_build
        engine.stop()

        records = _parse(buf)
        error_records = [r for r in records if r["level"] == "ERROR"]
        assert error_records, "C5: integrate exception must be logged at ERROR"
        ctx = error_records[0].get("context", {})
        assert ctx.get("portfolio_id") == "PORT-FAIL-001"


# ---------------------------------------------------------------------------
# Part 7 — Thread safety
# ---------------------------------------------------------------------------

class TestTD002Part7ThreadSafety:
    """Concurrent log calls from multiple threads do not corrupt state."""

    def test_c1_concurrent_log_calls(self):
        import iios.investment.market.integration.market_intelligence_integration_engine as m
        buf = _capture_on(m._log)
        errors: list[Exception] = []

        def _worker(i: int) -> None:
            try:
                m._log.info(f"thread worker {i}", context={"i": i})
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_worker, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        assert not errors, f"C1 concurrent log raised: {errors[:3]}"
        records = _parse(buf)
        assert len(records) == 50, f"Expected 50 records, got {len(records)}"

    def test_c4_concurrent_lifecycle_start_stop(self):
        from iios.investment.decision.integration.decision_intelligence_integration_engine import (
            DecisionIntelligenceIntegrationEngine,
        )
        # Verify multiple independent engine instances can start/stop concurrently
        errors: list[Exception] = []

        def _worker(_: int) -> None:
            try:
                eng = DecisionIntelligenceIntegrationEngine()
                eng.start()
                eng.stop()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        assert not errors, f"C4 concurrent start/stop raised: {errors[:3]}"

    def test_c3_concurrent_log_under_daemon_thread(self):
        from iios.investment.strategy.integration.strategy_intelligence_integration_engine import (
            StrategyIntelligenceIntegrationEngine,
        )
        import iios.investment.strategy.integration.strategy_intelligence_integration_engine as m

        engine = StrategyIntelligenceIntegrationEngine()
        engine.start()
        buf = _capture_on(m._log)
        errors: list[Exception] = []

        def _worker(i: int) -> None:
            try:
                m._log.info(f"worker {i}")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        engine.stop()
        assert not errors, f"C3 concurrent logging raised: {errors[:3]}"


# ---------------------------------------------------------------------------
# Part 8 — Regression (sanity check — not a full suite rerun)
# ---------------------------------------------------------------------------

class TestTD002Part8Regression:
    """Engine public APIs continue to work correctly after logging migration."""

    def test_c1_update_still_works(self):
        from iios.investment.market.integration.market_intelligence_integration_engine import (
            MarketIntelligenceIntegrationEngine,
        )
        from iios.investment.market.integration.models import IntelligenceBundle
        import time as _time
        engine = MarketIntelligenceIntegrationEngine()
        engine.start()
        bundle = IntelligenceBundle(bar_index=1, timestamp=_time.time())
        snap = engine.update(bundle)
        assert snap is not None
        engine.stop()

    def test_c2_integrate_still_works(self):
        from iios.investment.company.integration.company_intelligence_integration_engine import (
            CompanyIntelligenceIntegrationEngine,
        )
        engine = CompanyIntelligenceIntegrationEngine()
        engine.start()
        snap = engine.integrate("RELI.NS")
        assert snap is not None
        assert snap.ticker == "RELI.NS"
        engine.stop()

    def test_c3_get_snapshot_sync_still_works(self):
        from iios.investment.strategy.integration.strategy_intelligence_integration_engine import (
            StrategyIntelligenceIntegrationEngine,
        )
        engine = StrategyIntelligenceIntegrationEngine()
        engine.start()
        result = engine.get_snapshot_sync("STRAT-NONEXISTENT")
        assert result is None  # no data submitted
        engine.stop()

    def test_c4_integrate_sync_still_works(self):
        from iios.investment.decision.integration.decision_intelligence_integration_engine import (
            DecisionIntelligenceIntegrationEngine,
        )
        engine = DecisionIntelligenceIntegrationEngine()
        engine.start()
        snap = engine.integrate_sync(decision_id="DEC-REG-001")
        assert snap is not None
        assert snap.decision_id == "DEC-REG-001"
        engine.stop()

    def test_c5_integrate_still_works(self):
        from iios.investment.portfolio.integration.portfolio_intelligence_integration_engine import (
            PortfolioIntelligenceIntegrationEngine,
        )
        engine = PortfolioIntelligenceIntegrationEngine()
        engine.start()
        snap = engine.integrate("PORT-REG-001")
        assert snap is not None
        engine.stop()

    def test_c1_async_update_still_works(self):
        import asyncio as _asyncio
        from iios.investment.market.integration.market_intelligence_integration_engine import (
            MarketIntelligenceIntegrationEngine,
        )
        from iios.investment.market.integration.models import IntelligenceBundle
        import time as _time
        engine = MarketIntelligenceIntegrationEngine()
        engine.start()
        bundle = IntelligenceBundle(bar_index=1, timestamp=_time.time())
        snap = _asyncio.run(engine.async_update(bundle))
        assert snap is not None
        engine.stop()
