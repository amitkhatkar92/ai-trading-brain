"""tests/unit/investment/portfolio/construction/test_engine_integration.py

End-to-end integration tests for PortfolioConstructionEngine — the full
construction pipeline from recommendations to ConstructionResult.
"""
from __future__ import annotations

import threading
import pytest

from iios.investment.portfolio.construction.construction_types import (
    ConstructionStatus,
    ConstructionType,
    WeightingMethod,
)
from iios.investment.portfolio.construction.portfolio_blueprint import (
    ConstructionRequest,
    ConstructionResult,
)
from iios.investment.portfolio.construction.portfolio_construction_engine import (
    ConstructionIntegrationRefs,
    PortfolioConstructionEngine,
)
from tests.unit.investment.portfolio.construction.conftest import make_recs, _rec


class TestEngineLifecycle:
    def test_start_and_stop(self):
        e = PortfolioConstructionEngine()
        e.start()
        assert e.is_running
        e.stop()
        assert not e.is_running

    def test_double_start_safe(self):
        e = PortfolioConstructionEngine()
        e.start()
        e.start()
        assert e.is_running
        e.stop()

    def test_construct_before_start_raises(self):
        e = PortfolioConstructionEngine()
        with pytest.raises(RuntimeError):
            e.construct("PF-1", make_recs(5))

    def test_configure_integrations(self, engine):
        refs = ConstructionIntegrationRefs(decision_intelligence=object())
        engine.configure_integrations(refs)
        # No error; integration is stored


class TestPortfolioRegistration:
    def test_register(self, engine):
        engine.register_portfolio("PF-100")
        assert engine.is_registered("PF-100")

    def test_deregister(self, engine):
        engine.register_portfolio("PF-200")
        removed = engine.deregister_portfolio("PF-200")
        assert removed
        assert not engine.is_registered("PF-200")

    def test_deregister_nonexistent(self, engine):
        assert not engine.deregister_portfolio("nonexistent")

    def test_list_portfolios(self, engine):
        engine.register_portfolio("PF-A")
        engine.register_portfolio("PF-B")
        names = engine.list_portfolios()
        assert "PF-A" in names
        assert "PF-B" in names

    def test_portfolio_count(self, engine):
        engine.register_portfolio("PF-X")
        assert engine.portfolio_count() >= 1


class TestConstructionPipeline:
    def test_success_with_10_recs(self, engine, recs_10):
        req = ConstructionRequest(portfolio_id="PF-1", min_holdings=2)
        result = engine.construct("PF-1", recs_10, req)
        assert result.succeeded
        assert result.has_blueprint
        assert result.recommendations_in == 10
        assert result.recommendations_selected > 0

    def test_result_has_blueprint(self, engine, recs_10):
        result = engine.construct("PF-2", recs_10)
        assert result.blueprint is not None
        assert result.blueprint.total_slots > 0

    def test_auto_register_on_construct(self, engine, recs_5):
        result = engine.construct("PF-AUTO", recs_5, auto_register=True)
        assert result.succeeded
        assert engine.is_registered("PF-AUTO")

    def test_failed_with_no_recs(self, engine):
        result = engine.construct("PF-EMPTY", [])
        assert result.failed
        assert len(result.errors) > 0

    def test_quality_summary_populated(self, engine, recs_10):
        result = engine.construct("PF-Q", recs_10)
        assert "overall_score" in result.quality_summary
        assert 0.0 <= result.quality_summary["overall_score"] <= 1.0

    def test_constraint_summary_populated(self, engine, recs_10):
        result = engine.construct("PF-C", recs_10)
        assert "is_compliant" in result.constraint_summary

    def test_validation_summary_populated(self, engine, recs_10):
        result = engine.construct("PF-V", recs_10)
        assert "portfolio_valid" in result.validation_summary

    def test_duration_positive(self, engine, recs_5):
        result = engine.construct("PF-DUR", recs_5)
        assert result.duration_ms >= 0.0

    def test_version_increments(self, engine, recs_5):
        result1 = engine.construct("PF-VER", recs_5)
        result2 = engine.construct("PF-VER", recs_5)
        bp1 = result1.blueprint
        bp2 = result2.blueprint
        assert bp2.version == bp1.version + 1

    def test_equal_weight_result(self, engine, recs_5):
        req = ConstructionRequest(
            portfolio_id    = "PF-EW",
            weighting_method= WeightingMethod.EQUAL,
            target_cash_pct = 0.0,
            min_holdings    = 1,
        )
        result = engine.construct("PF-EW", recs_5, req)
        assert result.succeeded
        slots  = result.blueprint.slots
        w0 = slots[0].target_weight
        for s in slots:
            assert abs(s.target_weight - w0) < 1e-4

    def test_deterministic_same_inputs(self, engine, recs_5):
        req = ConstructionRequest(portfolio_id="PF-DET")
        engine.register_portfolio("PF-DET")
        r1 = engine.construct("PF-DET", recs_5, req)
        engine2 = PortfolioConstructionEngine()
        engine2.start()
        r2 = engine2.construct("PF-DET", recs_5, req)
        engine2.stop()
        syms1 = tuple(s.symbol for s in r1.blueprint.slots)
        syms2 = tuple(s.symbol for s in r2.blueprint.slots)
        assert syms1 == syms2


class TestQueryAPIs:
    def test_current_blueprint_none_before_construct(self, registered_engine):
        snap = registered_engine.current_blueprint("PF-001")
        assert snap is None   # no construction yet

    def test_current_blueprint_after_construct(self, registered_engine, recs_10):
        registered_engine.construct("PF-001", recs_10)
        snap = registered_engine.current_blueprint("PF-001")
        assert snap is not None
        assert snap.total_holdings > 0

    def test_construction_history_empty_before(self, registered_engine):
        h = registered_engine.construction_history("PF-001")
        assert isinstance(h, list)
        assert len(h) == 0

    def test_construction_history_after_construct(self, registered_engine, recs_10):
        registered_engine.construct("PF-001", recs_10)
        h = registered_engine.construction_history("PF-001")
        assert len(h) >= 1
        assert "blueprint_id" in h[0]

    def test_quality_score_after_construct(self, registered_engine, recs_10):
        registered_engine.construct("PF-001", recs_10)
        q = registered_engine.quality_score("PF-001")
        assert q is not None
        assert 0.0 <= q <= 1.0

    def test_quality_score_none_before(self, registered_engine):
        assert registered_engine.quality_score("PF-001") is None

    def test_portfolio_statistics_after_construct(self, registered_engine, recs_10):
        registered_engine.construct("PF-001", recs_10)
        s = registered_engine.portfolio_statistics("PF-001")
        assert s is not None

    def test_engine_statistics_snapshot(self, engine, recs_5):
        engine.construct("PF-S", recs_5)
        snap = engine.statistics_snapshot()
        assert "total_runs" in snap
        assert snap["total_runs"] >= 1

    def test_health_report(self, engine, recs_5):
        engine.construct("PF-H", recs_5)
        h = engine.health()
        assert "overall_status" in h
        assert "error_rate" in h


class TestEventCallback:
    def test_event_emitted_on_success(self, recs_10):
        events = []

        def cb(event: str, payload):
            events.append(event)

        e = PortfolioConstructionEngine(event_callback=cb)
        e.start()
        e.construct("PF-EV", recs_10)
        e.stop()

        assert "engine_started" in events
        assert "construction_completed" in events
        assert "engine_stopped" in events

    def test_event_emitted_on_failure(self):
        events = []

        def cb(event: str, payload):
            events.append(event)

        e = PortfolioConstructionEngine(event_callback=cb)
        e.start()
        e.construct("PF-FAIL", [])
        e.stop()

        assert "construction_failed" in events or "construction_completed" not in events

    def test_callback_exception_does_not_propagate(self, recs_5):
        def bad_cb(event, payload):
            raise RuntimeError("boom")

        e = PortfolioConstructionEngine(event_callback=bad_cb)
        e.start()
        result = e.construct("PF-CB", recs_5)
        e.stop()
        # Engine should not fail because callback raised
        assert result is not None


class TestConcurrency:
    def test_concurrent_construction(self, engine):
        results = []
        errors  = []
        lock    = threading.Lock()

        def run(pid: str):
            recs = make_recs(5)
            try:
                result = engine.construct(pid, recs)
                with lock:
                    results.append(result)
            except Exception as exc:
                with lock:
                    errors.append(str(exc))

        threads = [threading.Thread(target=run, args=(f"PF-T{i}",)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 10
        assert all(r.succeeded for r in results)

    def test_concurrent_registration(self, engine):
        errors  = []
        lock    = threading.Lock()

        def reg(pid: str):
            try:
                engine.register_portfolio(pid)
            except Exception as exc:
                with lock:
                    errors.append(str(exc))

        threads = [threading.Thread(target=reg, args=(f"PF-R{i}",)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert engine.portfolio_count() >= 20


class TestConstraintRegistryIntegration:
    def test_access_registry_via_engine(self, engine):
        reg = engine.constraint_registry
        assert reg is not None

    def test_register_constraint_via_engine(self, engine, max_weight_constraint):
        engine.constraint_registry.register(max_weight_constraint)
        c = engine.constraint_registry.get("max_single_weight")
        assert c is not None

    def test_constraint_evaluated_during_construct(self, engine, max_weight_constraint, recs_10):
        engine.constraint_registry.register(max_weight_constraint)
        result = engine.construct("PF-CON", recs_10)
        assert result.succeeded
        assert "is_compliant" in result.constraint_summary
