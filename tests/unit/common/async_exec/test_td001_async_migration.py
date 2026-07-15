"""tests/unit/common/async_exec/test_td001_async_migration.py
TD-001 Async Migration Validation Tests.

Verifies that C1 (Market), C3 (Strategy), and C4 (Decision) integration engines
have been fully migrated from raw asyncio / ThreadPoolExecutor patterns to the
Institutional Async Execution Framework (AsyncExecutionManager).

Checks:
  1. No legacy async patterns remain in source files
  2. execute_sync() is wired for C3 sync wrappers
  3. execute() is wired for C1 async_update and C4 integrate
  4. Execution metrics are recorded for all migrated paths
  5. Thread safety under concurrent invocations
"""
from __future__ import annotations

import ast
import asyncio
import inspect
import os
import re
import threading
import time
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio

from iios.common.async_exec.async_execution_manager import (
    get_execution_manager,
    reset_execution_manager,
)
from iios.common.async_exec.migration_analysis import (
    PLATFORM_ASYNC_PROFILES,
    engines_needing_standardization,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_WORKSPACE = Path(__file__).parent.parent.parent.parent.parent

_C1_PATH = _WORKSPACE / "iios/investment/market/integration/market_intelligence_integration_engine.py"
_C3_PATH = _WORKSPACE / "iios/investment/strategy/integration/strategy_intelligence_integration_engine.py"
_C4_PATH = _WORKSPACE / "iios/investment/decision/integration/decision_intelligence_integration_engine.py"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _ast_names_used(source: str) -> set[str]:
    """Return all Name and Attribute nodes used in the AST."""
    tree = ast.parse(source)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return names


# ---------------------------------------------------------------------------
# Part 1 — Source-level: no legacy patterns
# ---------------------------------------------------------------------------

class TestTD001Part1LegacyPatternsAbsent:
    """Verify legacy asyncio / ThreadPoolExecutor patterns are gone."""

    def test_c1_no_asyncio_get_event_loop(self):
        src = _source(_C1_PATH)
        assert "asyncio.get_event_loop" not in src, (
            "C1: asyncio.get_event_loop() must not appear after TD-001 migration"
        )

    def test_c1_no_threadpoolexecutor_import(self):
        src = _source(_C1_PATH)
        assert "ThreadPoolExecutor" not in src, (
            "C1: ThreadPoolExecutor must be removed after TD-001 migration"
        )

    def test_c1_no_asyncio_import(self):
        src = _source(_C1_PATH)
        # asyncio should no longer be needed in C1
        assert "import asyncio" not in src, (
            "C1: 'import asyncio' must be removed after TD-001 migration"
        )

    def test_c1_no_self_executor(self):
        src = _source(_C1_PATH)
        assert "self._executor" not in src, (
            "C1: self._executor (ThreadPoolExecutor) must be removed"
        )

    def test_c3_no_asyncio_run_in_sync_wrappers(self):
        src = _source(_C3_PATH)
        # asyncio.run() must not appear in submit_update_sync / get_snapshot_sync
        # We parse the AST to check the specific methods
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in (
                "submit_update_sync", "get_snapshot_sync"
            ):
                method_src = ast.unparse(node)
                assert "asyncio.run(" not in method_src, (
                    f"C3.{node.name}: asyncio.run() must be replaced with execute_sync()"
                )

    def test_c3_no_threadpoolexecutor_import(self):
        src = _source(_C3_PATH)
        assert "ThreadPoolExecutor" not in src, (
            "C3: unused ThreadPoolExecutor import must be removed"
        )

    def test_c4_no_asyncio_import(self):
        src = _source(_C4_PATH)
        assert "import asyncio" not in src, (
            "C4: 'import asyncio' must be removed after TD-001 migration"
        )

    def test_c4_no_run_in_executor(self):
        src = _source(_C4_PATH)
        assert "run_in_executor" not in src, (
            "C4: run_in_executor() must be replaced with AsyncExecutionManager.execute()"
        )


# ---------------------------------------------------------------------------
# Part 2 — Source-level: framework patterns present
# ---------------------------------------------------------------------------

class TestTD001Part2FrameworkPatternsPresent:
    """Verify execution-manager imports and call-sites are present."""

    def test_c1_imports_get_exec_manager(self):
        src = _source(_C1_PATH)
        assert "_get_exec_manager" in src, (
            "C1: must import get_execution_manager as _get_exec_manager"
        )

    def test_c1_async_update_uses_execute(self):
        src = _source(_C1_PATH)
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "async_update":
                method_src = ast.unparse(node)
                assert "_get_exec_manager" in method_src, (
                    "C1.async_update: must call _get_exec_manager().execute()"
                )
                assert "WorkloadType" in method_src, (
                    "C1.async_update: must pass WorkloadType.IO_BOUND"
                )
                return
        pytest.fail("C1: async_update method not found")

    def test_c3_imports_get_exec_manager(self):
        src = _source(_C3_PATH)
        assert "_get_exec_manager" in src, (
            "C3: must import get_execution_manager as _get_exec_manager"
        )

    def test_c3_submit_update_sync_uses_execute_sync(self):
        src = _source(_C3_PATH)
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "submit_update_sync":
                method_src = ast.unparse(node)
                assert "execute_sync" in method_src, (
                    "C3.submit_update_sync: must call execute_sync()"
                )
                return
        pytest.fail("C3: submit_update_sync method not found")

    def test_c3_get_snapshot_sync_uses_execute_sync(self):
        src = _source(_C3_PATH)
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "get_snapshot_sync":
                method_src = ast.unparse(node)
                assert "execute_sync" in method_src, (
                    "C3.get_snapshot_sync: must call execute_sync()"
                )
                return
        pytest.fail("C3: get_snapshot_sync method not found")

    def test_c4_imports_get_exec_manager(self):
        src = _source(_C4_PATH)
        assert "_get_exec_manager" in src, (
            "C4: must import get_execution_manager as _get_exec_manager"
        )

    def test_c4_integrate_uses_execute(self):
        src = _source(_C4_PATH)
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "integrate":
                method_src = ast.unparse(node)
                assert "_get_exec_manager" in method_src, (
                    "C4.integrate: must call _get_exec_manager().execute()"
                )
                assert "WorkloadType" in method_src, (
                    "C4.integrate: must pass WorkloadType.IO_BOUND"
                )
                return
        pytest.fail("C4: integrate async method not found")


# ---------------------------------------------------------------------------
# Part 3 — migration_analysis.py profiles updated
# ---------------------------------------------------------------------------

class TestTD001Part3MigrationProfilesUpdated:
    """Verify PLATFORM_ASYNC_PROFILES reflects the completed migration."""

    def test_c1_no_longer_needs_standardization(self):
        profile = PLATFORM_ASYNC_PROFILES["iios:market:intelligence:integration"]
        assert profile.recommended_action == "no_change", (
            "C1 profile must be 'no_change' after TD-001"
        )
        assert profile.migration_complexity == "none"

    def test_c1_has_own_executor_false(self):
        profile = PLATFORM_ASYNC_PROFILES["iios:market:intelligence:integration"]
        assert profile.has_own_executor is False, (
            "C1: has_own_executor must be False after removing ThreadPoolExecutor"
        )

    def test_c3_no_longer_needs_standardization(self):
        profile = PLATFORM_ASYNC_PROFILES["iios:strategy:intelligence:integration"]
        assert profile.recommended_action == "no_change"
        assert profile.migration_complexity == "none"

    def test_c3_has_own_executor_false(self):
        profile = PLATFORM_ASYNC_PROFILES["iios:strategy:intelligence:integration"]
        assert profile.has_own_executor is False

    def test_c4_no_longer_needs_standardization(self):
        profile = PLATFORM_ASYNC_PROFILES["iios:decision:intelligence:integration"]
        assert profile.recommended_action == "no_change"
        assert profile.migration_complexity == "none"

    def test_engines_needing_standardization_excludes_c1_c3_c4(self):
        pending = dict(engines_needing_standardization())
        assert "iios:market:intelligence:integration" not in pending
        assert "iios:strategy:intelligence:integration" not in pending
        assert "iios:decision:intelligence:integration" not in pending


# ---------------------------------------------------------------------------
# Part 4 — Runtime: metrics are recorded
# ---------------------------------------------------------------------------

class TestTD001Part4MetricsRecorded:
    """Verify execution-manager metrics are updated by migrated paths."""

    def setup_method(self):
        reset_execution_manager()

    def teardown_method(self):
        reset_execution_manager()

    def test_c1_async_update_records_metric(self):
        from iios.investment.market.integration.market_intelligence_integration_engine import (
            MarketIntelligenceIntegrationEngine,
        )
        engine = MarketIntelligenceIntegrationEngine()
        engine.start()

        # build a minimal bundle
        from iios.investment.market.integration.models import IntelligenceBundle
        bundle = IntelligenceBundle(bar_index=1, timestamp=time.time())

        mgr = get_execution_manager()
        before = mgr.statistics().total_submitted

        asyncio.run(engine.async_update(bundle))

        after = mgr.statistics().total_submitted
        assert after > before, "C1.async_update: must increment total_submitted in metrics"
        engine.stop()

    def test_c3_submit_update_sync_records_metric(self):
        from iios.investment.strategy.integration.strategy_intelligence_integration_engine import (
            StrategyIntelligenceIntegrationEngine,
        )
        from iios.investment.strategy.integration.aggregation_state import make_update
        from iios.investment.strategy.integration.integration_constants import IntelligenceSource

        engine = StrategyIntelligenceIntegrationEngine()
        engine.start()

        update = make_update(
            strategy_id="TEST-001",
            source=IntelligenceSource.LEARNING,
            payload={"dummy": True},
        )

        mgr = get_execution_manager()
        before = mgr.statistics().total_submitted

        engine.submit_update_sync(update)

        after = mgr.statistics().total_submitted
        assert after > before, "C3.submit_update_sync: must increment total_submitted"
        engine.stop()

    def test_c3_get_snapshot_sync_records_metric(self):
        from iios.investment.strategy.integration.strategy_intelligence_integration_engine import (
            StrategyIntelligenceIntegrationEngine,
        )

        engine = StrategyIntelligenceIntegrationEngine()
        engine.start()

        mgr = get_execution_manager()
        before = mgr.statistics().total_submitted

        result = engine.get_snapshot_sync("NONEXISTENT-999")
        assert result is None  # no data for this strategy

        after = mgr.statistics().total_submitted
        assert after > before, "C3.get_snapshot_sync: must increment total_submitted"
        engine.stop()

    def test_c4_integrate_records_metric(self):
        from iios.investment.decision.integration.decision_intelligence_integration_engine import (
            DecisionIntelligenceIntegrationEngine,
        )

        engine = DecisionIntelligenceIntegrationEngine()
        engine.start()

        mgr = get_execution_manager()
        before = mgr.statistics().total_submitted

        asyncio.run(engine.integrate(decision_id="DEC-TEST-001"))

        after = mgr.statistics().total_submitted
        assert after > before, "C4.integrate: must increment total_submitted"
        engine.stop()


# ---------------------------------------------------------------------------
# Part 5 — Runtime: public API signatures unchanged
# ---------------------------------------------------------------------------

class TestTD001Part5PublicAPIsUnchanged:
    """Migration must not change any public method signature."""

    def test_c1_async_update_signature(self):
        from iios.investment.market.integration.market_intelligence_integration_engine import (
            MarketIntelligenceIntegrationEngine,
        )
        sig = inspect.signature(MarketIntelligenceIntegrationEngine.async_update)
        params = list(sig.parameters.keys())
        assert params == ["self", "bundle"], (
            f"C1.async_update signature changed: {params}"
        )

    def test_c1_async_update_is_coroutine(self):
        from iios.investment.market.integration.market_intelligence_integration_engine import (
            MarketIntelligenceIntegrationEngine,
        )
        assert inspect.iscoroutinefunction(
            MarketIntelligenceIntegrationEngine.async_update
        ), "C1.async_update must remain an async def"

    def test_c3_submit_update_sync_signature(self):
        from iios.investment.strategy.integration.strategy_intelligence_integration_engine import (
            StrategyIntelligenceIntegrationEngine,
        )
        sig = inspect.signature(StrategyIntelligenceIntegrationEngine.submit_update_sync)
        params = list(sig.parameters.keys())
        assert params == ["self", "update"], (
            f"C3.submit_update_sync signature changed: {params}"
        )

    def test_c3_get_snapshot_sync_signature(self):
        from iios.investment.strategy.integration.strategy_intelligence_integration_engine import (
            StrategyIntelligenceIntegrationEngine,
        )
        sig = inspect.signature(StrategyIntelligenceIntegrationEngine.get_snapshot_sync)
        params = list(sig.parameters.keys())
        assert params == ["self", "strategy_id"], (
            f"C3.get_snapshot_sync signature changed: {params}"
        )

    def test_c4_integrate_sync_signature_unchanged(self):
        from iios.investment.decision.integration.decision_intelligence_integration_engine import (
            DecisionIntelligenceIntegrationEngine,
        )
        sig = inspect.signature(DecisionIntelligenceIntegrationEngine.integrate_sync)
        params = list(sig.parameters.keys())
        assert "decision_id" in params
        assert "evidence" in params
        assert "recommendation" in params

    def test_c4_integrate_is_coroutine(self):
        from iios.investment.decision.integration.decision_intelligence_integration_engine import (
            DecisionIntelligenceIntegrationEngine,
        )
        assert inspect.iscoroutinefunction(
            DecisionIntelligenceIntegrationEngine.integrate
        ), "C4.integrate must remain an async def"


# ---------------------------------------------------------------------------
# Part 6 — Runtime: thread safety under concurrent calls
# ---------------------------------------------------------------------------

class TestTD001Part6ThreadSafety:
    """Concurrent callers should not produce errors or corrupt state."""

    def setup_method(self):
        reset_execution_manager()

    def teardown_method(self):
        reset_execution_manager()

    def test_c3_concurrent_submit_update_sync(self):
        from iios.investment.strategy.integration.strategy_intelligence_integration_engine import (
            StrategyIntelligenceIntegrationEngine,
        )
        from iios.investment.strategy.integration.aggregation_state import make_update
        from iios.investment.strategy.integration.integration_constants import IntelligenceSource

        engine = StrategyIntelligenceIntegrationEngine()
        engine.start()

        errors: list[Exception] = []

        def _worker(i: int) -> None:
            try:
                update = make_update(
                    strategy_id=f"STRAT-{i % 5:03d}",
                    source=IntelligenceSource.LEARNING,
                    payload={"worker": i},
                )
                engine.submit_update_sync(update)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        assert not errors, f"C3 concurrent submit_update_sync raised: {errors[:3]}"
        engine.stop()

    def test_c4_concurrent_integrate_sync(self):
        from iios.investment.decision.integration.decision_intelligence_integration_engine import (
            DecisionIntelligenceIntegrationEngine,
        )

        engine = DecisionIntelligenceIntegrationEngine()
        engine.start()

        errors: list[Exception] = []

        def _worker(i: int) -> None:
            try:
                engine.integrate_sync(decision_id=f"DEC-{i:04d}")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        assert not errors, f"C4 concurrent integrate_sync raised: {errors[:3]}"
        engine.stop()
