"""tests/unit/investment/test_investment_engine.py"""
from __future__ import annotations

import asyncio
import threading

import pytest

from iios.investment import (
    # constants
    AnalysisStatus, AssetClass, IntelligenceType, InvestmentObjective,
    RiskProfile, SessionStatus, TimeHorizon, WorkflowStatus,
    INVESTMENT_ENGINE_VERSION,
    # exceptions
    AnalysisFailedError, AssetClassNotSupportedError,
    DomainEngineAlreadyRegisteredError, DomainEngineNotFoundError,
    EngineAlreadyRunningError, EngineNotInitializedError,
    InvestmentEngineError, InvestmentNotFoundError,
    RegistryItemAlreadyExistsError, RegistryItemNotFoundError,
    RegistryOverflowError, RequestValidationError,
    SessionNotFoundError, WorkflowNotFoundError,
    # context
    InvestmentContextState, get_investment_context, reset_investment_context,
    investment_session, inv_stage_scope,
    # models
    InvestmentAnalysis, InvestmentContext, InvestmentHistory,
    InvestmentMetadata, InvestmentMetrics, InvestmentRequest, InvestmentResult,
    InvestmentSession, InvestmentStatistics,
    # workflow
    InvestmentWorkflow, NoOpWorkflow, WorkflowExecutor,
    # registry
    InvestmentRegistry, get_investment_registry, reset_investment_registry,
    # manager
    InvestmentManager, get_investment_manager, reset_investment_manager,
    # services
    InvestmentService,
    # monitoring
    InvestmentMonitor,
    # factory
    InvestmentFactory,
    # engine
    InvestmentIntelligenceEngine, get_investment_engine, reset_investment_engine,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _req(
    symbols:     list[str]        = None,
    asset_class: AssetClass       = AssetClass.EQUITY,
    objective:   InvestmentObjective = InvestmentObjective.GROWTH,
) -> InvestmentRequest:
    return InvestmentRequest(
        asset_class=asset_class,
        symbols=symbols or ["AAPL"],
        objective=objective,
    )


def _analysis(
    request_id:  str             = "r1",
    status:      AnalysisStatus  = AnalysisStatus.COMPLETED,
    confidence:  float           = 0.8,
) -> InvestmentAnalysis:
    a = InvestmentAnalysis(
        request_id=request_id,
        intelligence_type=IntelligenceType.MARKET,
        asset_class=AssetClass.EQUITY,
        symbols=["AAPL"],
        confidence=confidence,
        status=status,
    )
    return a


@pytest.fixture(autouse=True)
def _reset_all():
    reset_investment_engine()
    reset_investment_manager()
    reset_investment_registry()
    reset_investment_context()
    yield
    reset_investment_engine()
    reset_investment_manager()
    reset_investment_registry()
    reset_investment_context()


# ═══════════════════════════════════════════════════════════════════════════════
# TestConstants
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_asset_class_values(self):
        assert AssetClass.EQUITY.value      == "equity"
        assert AssetClass.BOND.value        == "bond"
        assert AssetClass.CRYPTO.value      == "crypto"
        assert AssetClass.OPTION.value      == "option"

    def test_intelligence_type_values(self):
        assert IntelligenceType.MARKET.value    == "market"
        assert IntelligenceType.COMPANY.value   == "company"
        assert IntelligenceType.EXECUTION.value == "execution"

    def test_analysis_status_values(self):
        assert AnalysisStatus.PENDING.value   == "pending"
        assert AnalysisStatus.COMPLETED.value == "completed"
        assert AnalysisStatus.FAILED.value    == "failed"

    def test_time_horizon_values(self):
        assert TimeHorizon.INTRADAY.value   == "intraday"
        assert TimeHorizon.VERY_LONG.value  == "very_long"

    def test_risk_profile_values(self):
        assert RiskProfile.CONSERVATIVE.value == "conservative"
        assert RiskProfile.SPECULATIVE.value  == "speculative"

    def test_version(self):
        assert INVESTMENT_ENGINE_VERSION == "1.0.0"


# ═══════════════════════════════════════════════════════════════════════════════
# TestExceptions
# ═══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_base_error(self):
        e = InvestmentEngineError("boom", "II-999")
        assert "II-999" in str(e)

    def test_not_found(self):
        e = InvestmentNotFoundError("r1")
        assert "r1" in str(e)
        assert e.code == "II-011"

    def test_workflow_not_found(self):
        e = WorkflowNotFoundError("w1")
        assert e.code == "II-021"

    def test_registry_overflow(self):
        e = RegistryOverflowError(100)
        assert "100" in str(e)
        assert e.code == "II-033"

    def test_engine_not_initialized(self):
        e = EngineNotInitializedError()
        assert "II-051" in str(e)

    def test_engine_already_running(self):
        e = EngineAlreadyRunningError()
        assert "II-052" in str(e)

    def test_session_not_found(self):
        e = SessionNotFoundError("s1")
        assert e.code == "II-061"

    def test_asset_class_not_supported(self):
        e = AssetClassNotSupportedError("unknown_class")
        assert e.code == "II-071"

    def test_domain_engine_not_found(self):
        e = DomainEngineNotFoundError("market")
        assert e.code == "II-081"

    def test_hierarchy(self):
        assert issubclass(InvestmentNotFoundError, InvestmentEngineError)
        assert issubclass(EngineNotInitializedError, InvestmentEngineError)
        assert issubclass(DomainEngineNotFoundError, InvestmentEngineError)


# ═══════════════════════════════════════════════════════════════════════════════
# TestInvestmentContextState (TLS)
# ═══════════════════════════════════════════════════════════════════════════════

class TestInvestmentContextState:
    def test_session(self):
        with investment_session("src") as ctx:
            assert ctx.source_id == "src"

    def test_stage_scope(self):
        with investment_session() as ctx:
            assert ctx.current_stage == ""
            with inv_stage_scope("validate"):
                assert ctx.current_stage == "validate"
            assert ctx.current_stage == ""

    def test_diagnostics(self):
        with investment_session() as ctx:
            ctx.add_diagnostic("WARNING", "w")
            ctx.add_diagnostic("ERROR",   "e")
            assert len(ctx.warnings()) == 1
            assert len(ctx.errors())   == 1

    def test_elapsed(self):
        import time
        with investment_session() as ctx:
            time.sleep(0.01)
            assert ctx.elapsed_ms() > 0

    def test_to_dict(self):
        with investment_session("src") as ctx:
            d = ctx.to_dict()
            assert "session_id" in d
            assert d["source_id"] == "src"


# ═══════════════════════════════════════════════════════════════════════════════
# TestInvestmentRequest
# ═══════════════════════════════════════════════════════════════════════════════

class TestInvestmentRequest:
    def test_defaults(self):
        r = InvestmentRequest()
        assert r.request_id
        assert r.asset_class == AssetClass.EQUITY
        assert r.symbols == []

    def test_to_dict(self):
        r = _req(["AAPL", "MSFT"])
        d = r.to_dict()
        assert d["asset_class"] == "equity"
        assert "AAPL" in d["symbols"]

    def test_unique_ids(self):
        r1 = InvestmentRequest()
        r2 = InvestmentRequest()
        assert r1.request_id != r2.request_id

    def test_intelligence_types_empty(self):
        r = _req()
        assert r.intelligence_types == []


# ═══════════════════════════════════════════════════════════════════════════════
# TestInvestmentContext (model)
# ═══════════════════════════════════════════════════════════════════════════════

class TestInvestmentContextModel:
    def test_set_and_get_result(self):
        ctx = InvestmentContext()
        ctx.set_result(IntelligenceType.MARKET, {"signal": "bullish"})
        assert ctx.get_result(IntelligenceType.MARKET) == {"signal": "bullish"}

    def test_missing_result_returns_default(self):
        ctx = InvestmentContext()
        assert ctx.get_result(IntelligenceType.COMPANY, "fallback") == "fallback"

    def test_to_dict(self):
        ctx = InvestmentContext(session_id="s1", request_id="r1")
        d   = ctx.to_dict()
        assert d["session_id"] == "s1"
        assert "context_id" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestInvestmentAnalysis
# ═══════════════════════════════════════════════════════════════════════════════

class TestInvestmentAnalysis:
    def test_defaults(self):
        a = InvestmentAnalysis()
        assert a.status == AnalysisStatus.PENDING
        assert a.confidence == 0.0

    def test_mark_completed(self):
        a = InvestmentAnalysis()
        a.mark_completed(confidence=0.85)
        assert a.status == AnalysisStatus.COMPLETED
        assert a.confidence == pytest.approx(0.85)
        assert a.completed_at is not None

    def test_mark_failed(self):
        a = InvestmentAnalysis()
        a.mark_failed("network error")
        assert a.status == AnalysisStatus.FAILED
        assert "network error" in a.errors

    def test_to_dict(self):
        a = _analysis()
        d = a.to_dict()
        assert d["status"] == "completed"
        assert "analysis_id" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestInvestmentResult
# ═══════════════════════════════════════════════════════════════════════════════

class TestInvestmentResult:
    def test_completed_analyses(self):
        a1 = _analysis(status=AnalysisStatus.COMPLETED)
        a2 = _analysis(status=AnalysisStatus.FAILED)
        r  = InvestmentResult(analyses=[a1, a2])
        assert len(r.completed_analyses) == 1
        assert len(r.failed_analyses)    == 1

    def test_to_dict(self):
        r = InvestmentResult(request_id="r1")
        d = r.to_dict()
        assert d["request_id"] == "r1"
        assert "result_id" in d

    def test_unique_ids(self):
        r1 = InvestmentResult()
        r2 = InvestmentResult()
        assert r1.result_id != r2.result_id


# ═══════════════════════════════════════════════════════════════════════════════
# TestInvestmentSession
# ═══════════════════════════════════════════════════════════════════════════════

class TestInvestmentSession:
    def test_defaults(self):
        s = InvestmentSession()
        assert s.is_active()
        assert s.session_id

    def test_add_request_and_result(self):
        s = InvestmentSession()
        s.add_request(_req())
        s.add_result(InvestmentResult())
        assert len(s.requests) == 1
        assert len(s.results)  == 1

    def test_close(self):
        s = InvestmentSession()
        s.close()
        assert not s.is_active()
        assert s.closed_at is not None

    def test_to_dict(self):
        s = InvestmentSession(name="test_session")
        d = s.to_dict()
        assert d["name"] == "test_session"


# ═══════════════════════════════════════════════════════════════════════════════
# TestInvestmentMetadata
# ═══════════════════════════════════════════════════════════════════════════════

class TestInvestmentMetadata:
    def test_defaults(self):
        m = InvestmentMetadata(result_id="r1")
        assert m.metadata_id
        assert m.tags == []

    def test_get_attribute(self):
        m = InvestmentMetadata(attributes={"region": "APAC"})
        assert m.get("region") == "APAC"
        assert m.get("missing", "default") == "default"

    def test_to_dict(self):
        m = InvestmentMetadata(result_id="r1", source="bloomberg")
        d = m.to_dict()
        assert d["source"] == "bloomberg"


# ═══════════════════════════════════════════════════════════════════════════════
# TestInvestmentStatistics
# ═══════════════════════════════════════════════════════════════════════════════

class TestInvestmentStatistics:
    def test_rates_zero_when_empty(self):
        s = InvestmentStatistics()
        assert s.avg_duration_ms == 0.0
        assert s.success_rate    == 0.0

    def test_success_rate(self):
        s = InvestmentStatistics(total_requests=10, completed=7)
        assert s.success_rate == pytest.approx(0.7)

    def test_to_dict(self):
        s = InvestmentStatistics(total_requests=5)
        d = s.to_dict()
        assert d["total_requests"] == 5


# ═══════════════════════════════════════════════════════════════════════════════
# TestInvestmentHistory
# ═══════════════════════════════════════════════════════════════════════════════

class TestInvestmentHistory:
    def test_store_and_get(self):
        h = InvestmentHistory()
        r = InvestmentResult(request_id="r1")
        h.store(r)
        assert h.get(r.result_id).result_id == r.result_id  # type: ignore[union-attr]

    def test_not_found_raises(self):
        h = InvestmentHistory()
        with pytest.raises(InvestmentNotFoundError):
            h.get("ghost")

    def test_by_request(self):
        h  = InvestmentHistory()
        r1 = InvestmentResult(request_id="req-A")
        r2 = InvestmentResult(request_id="req-A")
        r3 = InvestmentResult(request_id="req-B")
        for r in [r1, r2, r3]:
            h.store(r)
        assert len(h.by_request("req-A")) == 2

    def test_recent(self):
        h = InvestmentHistory()
        for _ in range(5):
            h.store(InvestmentResult())
        assert len(h.recent(3)) == 3

    def test_idempotent_store(self):
        h = InvestmentHistory()
        r = InvestmentResult()
        h.store(r)
        h.store(r)   # should not raise or duplicate
        assert h.count() == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TestNoOpWorkflow
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoOpWorkflow:
    def test_workflow_id(self):
        assert NoOpWorkflow().workflow_id == "noop"

    def test_execute_returns_completed(self):
        wf  = NoOpWorkflow()
        req = _req()
        ctx = InvestmentContext(request_id=req.request_id)
        a   = wf.execute(req, ctx)
        assert a.status == AnalysisStatus.COMPLETED
        assert a.confidence == pytest.approx(1.0)

    def test_supports_all_asset_classes(self):
        wf = NoOpWorkflow()
        for ac in AssetClass:
            assert wf.supports(ac)

    def test_to_dict(self):
        d = NoOpWorkflow().to_dict()
        assert d["workflow_id"] == "noop"


# ═══════════════════════════════════════════════════════════════════════════════
# TestWorkflowExecutor
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkflowExecutor:
    def test_execute_single_noop(self):
        exe = WorkflowExecutor()
        req = _req()
        a   = exe.execute(req, [NoOpWorkflow()])
        assert len(a) == 1
        assert a[0].status == AnalysisStatus.COMPLETED

    def test_execute_no_workflows(self):
        exe = WorkflowExecutor()
        a   = exe.execute(_req(), [])
        assert a == []

    def test_execute_filter_unsupported(self):
        """Workflow that only supports BOND should be skipped for EQUITY."""
        class BondOnlyWF(InvestmentWorkflow):
            @property
            def workflow_id(self): return "bond_only"
            @property
            def name(self): return "Bond Only"
            @property
            def supported_asset_classes(self): return [AssetClass.BOND]
            def execute(self, req, ctx): return InvestmentAnalysis()

        exe = WorkflowExecutor()
        a   = exe.execute(_req(asset_class=AssetClass.EQUITY), [BondOnlyWF()])
        assert a == []

    def test_execute_parallel(self):
        exe = WorkflowExecutor()
        req = _req()
        a   = exe.execute_parallel(req, [NoOpWorkflow()])
        assert len(a) == 1

    def test_execute_workflow_error_captured(self):
        class BrokenWF(InvestmentWorkflow):
            @property
            def workflow_id(self): return "broken"
            @property
            def name(self): return "Broken"
            def execute(self, req, ctx):
                raise RuntimeError("boom")

        exe = WorkflowExecutor()
        a   = exe.execute(_req(), [BrokenWF()])
        assert a[0].status == AnalysisStatus.FAILED
        assert "boom" in a[0].errors[0]

    def test_priority_order(self):
        executed = []

        def make_wf(wid: str, prio: int):
            class _W(InvestmentWorkflow):
                @property
                def workflow_id(self): return wid
                @property
                def name(self): return wid
                @property
                def priority(self): return prio
                def execute(self, req, ctx):
                    executed.append(wid)
                    a = InvestmentAnalysis(request_id=req.request_id)
                    a.mark_completed()
                    return a
            return _W()

        exe  = WorkflowExecutor()
        wfs  = [make_wf("high", 10), make_wf("low", 0)]  # low priority = runs first
        exe.execute(_req(), wfs)
        assert executed == ["low", "high"]


# ═══════════════════════════════════════════════════════════════════════════════
# TestInvestmentRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestInvestmentRegistry:
    def test_all_asset_classes_preregistered(self):
        """Default registry registers all AssetClass values."""
        reg = get_investment_registry()
        for ac in AssetClass:
            assert reg.is_supported(ac), f"{ac} not pre-registered"

    def test_register_workflow(self):
        reg = InvestmentRegistry()
        reg.register_workflow(NoOpWorkflow())
        assert reg.has_workflow("noop")

    def test_duplicate_workflow_raises(self):
        reg = InvestmentRegistry()
        reg.register_workflow(NoOpWorkflow())
        with pytest.raises(RegistryItemAlreadyExistsError):
            reg.register_workflow(NoOpWorkflow())

    def test_overwrite_workflow(self):
        reg = InvestmentRegistry()
        reg.register_workflow(NoOpWorkflow())
        reg.register_workflow(NoOpWorkflow(), overwrite=True)   # no error

    def test_get_workflow_not_found(self):
        reg = InvestmentRegistry()
        with pytest.raises(RegistryItemNotFoundError):
            reg.get_workflow("ghost")

    def test_register_domain_engine(self):
        reg = InvestmentRegistry()
        reg.register_domain_engine(IntelligenceType.MARKET, object())
        assert reg.has_domain_engine(IntelligenceType.MARKET)

    def test_domain_engine_not_found(self):
        reg = InvestmentRegistry()
        with pytest.raises(DomainEngineNotFoundError):
            reg.get_domain_engine(IntelligenceType.COMPANY)

    def test_duplicate_domain_engine_raises(self):
        reg = InvestmentRegistry()
        reg.register_domain_engine(IntelligenceType.SECTOR, object())
        with pytest.raises(DomainEngineAlreadyRegisteredError):
            reg.register_domain_engine(IntelligenceType.SECTOR, object())

    def test_singleton(self):
        r1 = get_investment_registry()
        r2 = get_investment_registry()
        assert r1 is r2

    def test_statistics(self):
        reg = InvestmentRegistry()
        reg.register_asset_class(AssetClass.EQUITY)
        s = reg.statistics()
        assert s["asset_classes"] >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# TestInvestmentManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestInvestmentManager:
    def test_analyze_with_noop(self):
        mgr = InvestmentManager()
        mgr.register_workflow(NoOpWorkflow())
        res = mgr.analyze(_req())
        assert res.succeeded
        assert len(res.analyses) == 1

    def test_analyze_no_workflows_uses_noop(self):
        """Manager with no registered workflows falls back to NoOp."""
        mgr = InvestmentManager()
        res = mgr.analyze(_req())
        assert res.succeeded

    def test_analyze_confidence_aggregated(self):
        mgr = InvestmentManager()
        mgr.register_workflow(NoOpWorkflow())   # confidence = 1.0
        res = mgr.analyze(_req())
        assert res.overall_confidence == pytest.approx(1.0)

    def test_get_result(self):
        mgr = InvestmentManager()
        res = mgr.analyze(_req())
        fetched = mgr.get(res.result_id)
        assert fetched.result_id == res.result_id

    def test_not_found_raises(self):
        mgr = InvestmentManager()
        with pytest.raises(InvestmentNotFoundError):
            mgr.get("ghost")

    def test_session_lifecycle(self):
        mgr = InvestmentManager()
        s   = mgr.create_session("my-session")
        assert s.is_active()
        mgr.close_session(s.session_id)
        assert not mgr.get_session(s.session_id).is_active()

    def test_session_not_found(self):
        mgr = InvestmentManager()
        with pytest.raises(SessionNotFoundError):
            mgr.get_session("ghost")

    def test_statistics_incremented(self):
        mgr = InvestmentManager()
        mgr.analyze(_req())
        s = mgr.statistics()
        assert s["total_requests"] == 1
        assert s["completed"]      >= 1

    def test_parallel_analyze(self):
        mgr = InvestmentManager()
        mgr.register_workflow(NoOpWorkflow())
        res = mgr.analyze(_req(), parallel=True)
        assert res.succeeded

    def test_recent(self):
        mgr = InvestmentManager()
        for _ in range(3):
            mgr.analyze(_req())
        assert len(mgr.recent(10)) == 3

    def test_singleton(self):
        m1 = get_investment_manager()
        m2 = get_investment_manager()
        assert m1 is m2


# ═══════════════════════════════════════════════════════════════════════════════
# TestInvestmentService
# ═══════════════════════════════════════════════════════════════════════════════

class TestInvestmentService:
    def test_store_and_get(self):
        svc = InvestmentService()
        r   = InvestmentResult(request_id="r1")
        svc.store(r)
        assert svc.get(r.result_id).result_id == r.result_id

    def test_not_found_raises(self):
        svc = InvestmentService()
        with pytest.raises(InvestmentNotFoundError):
            svc.get("ghost")

    def test_set_and_get_metadata(self):
        svc = InvestmentService()
        r   = InvestmentResult()
        svc.store(r)
        m   = svc.set_metadata(r.result_id, source="bloomberg", tags=["equity"])
        assert m.source       == "bloomberg"
        assert "equity" in m.tags
        assert svc.get_metadata(r.result_id) is m

    def test_archive(self):
        svc = InvestmentService()
        r   = InvestmentResult()
        svc.store(r)
        svc.archive(r.result_id)
        assert svc.is_archived(r.result_id)

    def test_replay(self):
        svc = InvestmentService()
        r   = InvestmentResult(request_id="req-1")
        svc.store(r)
        replay = svc.replay(r.result_id)
        assert replay["request_id"]         == "req-1"
        assert replay["can_replay"]         is True

    def test_replay_archived_disallowed(self):
        svc = InvestmentService()
        r   = InvestmentResult()
        svc.store(r)
        svc.archive(r.result_id)
        replay = svc.replay(r.result_id)
        assert replay["can_replay"] is False

    def test_search(self):
        svc = InvestmentService()
        r   = InvestmentResult(summary={"asset_class": "equity"}, status=AnalysisStatus.COMPLETED)
        svc.store(r)
        found = svc.search(asset_class="equity")
        assert any(x.result_id == r.result_id for x in found)


# ═══════════════════════════════════════════════════════════════════════════════
# TestInvestmentMetrics
# ═══════════════════════════════════════════════════════════════════════════════

class TestInvestmentMetrics:
    def test_zero_rates(self):
        m = InvestmentMetrics()
        assert m.success_rate == 0.0

    def test_success_rate(self):
        m = InvestmentMetrics(total_requests=10, completed=6)
        assert m.success_rate == pytest.approx(0.6)

    def test_to_dict(self):
        m = InvestmentMetrics(total_requests=5)
        d = m.to_dict()
        assert d["total_requests"] == 5
        assert "success_rate" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestInvestmentMonitor
# ═══════════════════════════════════════════════════════════════════════════════

class TestInvestmentMonitor:
    def test_sample_once(self):
        mon = InvestmentMonitor(sampler=lambda: {"requests": 5}, interval_seconds=60)
        s   = mon.sample_once()
        assert s["requests"] == 5
        assert "sampled_at" in s

    def test_start_stop(self):
        mon = InvestmentMonitor(sampler=lambda: {}, interval_seconds=0.05)
        mon.start()
        assert mon.is_running
        mon.stop()
        assert not mon.is_running


# ═══════════════════════════════════════════════════════════════════════════════
# TestAssetClassFramework
# ═══════════════════════════════════════════════════════════════════════════════

class TestAssetClassFramework:
    def test_all_standard_classes_defined(self):
        expected = {
            "equity", "etf", "index", "mutual_fund", "bond",
            "commodity", "currency", "crypto", "derivative",
            "option", "future", "structured",
        }
        actual = {ac.value for ac in AssetClass}
        assert expected == actual

    def test_registry_pre_registers_all(self):
        reg = get_investment_registry()
        for ac in AssetClass:
            assert reg.is_supported(ac)

    def test_register_custom_asset_class(self):
        reg = InvestmentRegistry()
        reg.register_asset_class(AssetClass.CRYPTO, handler=object(), metadata={"type": "digital"})
        info = reg.get_asset_class_info(AssetClass.CRYPTO)
        assert info["metadata"]["type"] == "digital"

    def test_get_unsupported_raises(self):
        reg = InvestmentRegistry()
        with pytest.raises(AssetClassNotSupportedError):
            reg.get_asset_class_info(AssetClass.BOND)  # not registered

    def test_supported_list_completeness(self):
        reg = get_investment_registry()
        supported = reg.supported_asset_classes()
        assert len(supported) == len(AssetClass)


# ═══════════════════════════════════════════════════════════════════════════════
# TestInvestmentFactory
# ═══════════════════════════════════════════════════════════════════════════════

class TestInvestmentFactory:
    def test_make_request(self):
        r = InvestmentFactory.make_request(["AAPL"], market="NYSE", currency="USD")
        assert r.symbols    == ["AAPL"]
        assert r.market     == "NYSE"
        assert r.currency   == "USD"

    def test_make_context(self):
        r   = _req()
        ctx = InvestmentFactory.make_context(r, session_id="s1")
        assert ctx.request_id == r.request_id
        assert ctx.session_id == "s1"

    def test_make_session(self):
        s = InvestmentFactory.make_session("test", "src")
        assert s.name      == "test"
        assert s.source_id == "src"

    def test_make_noop_workflow(self):
        wf = InvestmentFactory.make_noop_workflow()
        assert wf.workflow_id == "noop"

    def test_make_function_workflow(self):
        def fn(req, ctx):
            a = InvestmentAnalysis(request_id=req.request_id)
            a.mark_completed(confidence=0.5)
            return a

        wf  = InvestmentFactory.make_function_workflow("fn_wf", "FN", fn)
        req = _req()
        ctx = InvestmentFactory.make_context(req)
        a   = wf.execute(req, ctx)
        assert a.status     == AnalysisStatus.COMPLETED
        assert a.confidence == pytest.approx(0.5)


# ═══════════════════════════════════════════════════════════════════════════════
# TestInvestmentIntelligenceEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestInvestmentIntelligenceEngine:
    def test_initialize_and_running(self):
        eng = InvestmentIntelligenceEngine()
        assert not eng.is_running
        eng.initialize()
        assert eng.is_running

    def test_double_init_raises(self):
        eng = InvestmentIntelligenceEngine()
        eng.initialize()
        with pytest.raises(EngineAlreadyRunningError):
            eng.initialize()

    def test_not_initialized_raises(self):
        eng = InvestmentIntelligenceEngine()
        with pytest.raises(EngineNotInitializedError):
            eng.analyze(_req())

    def test_shutdown(self):
        eng = InvestmentIntelligenceEngine()
        eng.initialize()
        eng.shutdown()
        assert not eng.is_running

    def test_analyze(self):
        eng = InvestmentIntelligenceEngine()
        eng.initialize()
        res = eng.analyze(_req())
        assert res.succeeded

    def test_analyze_parallel(self):
        eng = InvestmentIntelligenceEngine()
        eng.initialize()
        res = eng.analyze(_req(), parallel=True)
        assert res.succeeded

    def test_analyze_async(self):
        eng = InvestmentIntelligenceEngine()
        eng.initialize()

        async def _run():
            return await eng.analyze_async(_req())

        res = asyncio.run(_run())
        assert res.succeeded

    def test_register_workflow(self):
        eng = InvestmentIntelligenceEngine()
        eng.initialize()
        eng.register_workflow(NoOpWorkflow(), overwrite=True)
        assert get_investment_registry().has_workflow("noop")

    def test_register_domain_engine(self):
        eng = InvestmentIntelligenceEngine()
        eng.initialize()
        eng.register_domain_engine(IntelligenceType.MARKET, object())
        assert get_investment_registry().has_domain_engine(IntelligenceType.MARKET)

    def test_create_and_get_session(self):
        eng = InvestmentIntelligenceEngine()
        eng.initialize()
        s   = eng.create_session("my-session")
        assert eng.get_session(s.session_id).session_id == s.session_id

    def test_health(self):
        eng = InvestmentIntelligenceEngine()
        eng.initialize()
        h   = eng.health()
        assert h["running"]  is True
        assert h["version"]  == "1.0.0"

    def test_stats(self):
        eng = InvestmentIntelligenceEngine()
        eng.initialize()
        s   = eng.stats()
        assert s["version"] == "1.0.0"

    def test_get_result(self):
        eng = InvestmentIntelligenceEngine()
        eng.initialize()
        res = eng.analyze(_req())
        assert eng.get(res.result_id).result_id == res.result_id

    def test_singleton(self):
        e1 = get_investment_engine()
        e2 = get_investment_engine()
        assert e1 is e2


# ═══════════════════════════════════════════════════════════════════════════════
# TestConcurrency
# ═══════════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    def test_concurrent_analyses(self):
        mgr     = InvestmentManager()
        mgr.register_workflow(NoOpWorkflow())
        results = []
        errors  = []

        def _run(i: int):
            try:
                results.append(mgr.analyze(_req([f"SYM{i}"])))
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        threads = [threading.Thread(target=_run, args=(i,)) for i in range(15)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors)  == 0
        assert len(results) == 15
        assert all(r.succeeded for r in results)

    def test_concurrent_workflow_registration(self):
        reg    = InvestmentRegistry()
        errors = []

        def _reg(i: int):
            try:
                reg.register_workflow(
                    InvestmentFactory.make_noop_workflow() if i == 0
                    else InvestmentFactory.make_function_workflow(
                        f"fn{i}", f"FN{i}",
                        lambda req, ctx: (
                            lambda a: (a.mark_completed(), a)[1]
                        )(InvestmentAnalysis(request_id=req.request_id)),
                    ),
                    overwrite=True,
                )
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        threads = [threading.Thread(target=_reg, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_concurrent_history(self):
        h      = InvestmentHistory()
        errors = []

        def _store(_):
            try:
                h.store(InvestmentResult())
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        threads = [threading.Thread(target=_store, args=(i,)) for i in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert h.count() == 30


# ═══════════════════════════════════════════════════════════════════════════════
# TestPackageImports
# ═══════════════════════════════════════════════════════════════════════════════

class TestPackageImports:
    def test_all_symbols_importable(self):
        import iios.investment as pkg
        for name in pkg.__all__:
            assert hasattr(pkg, name), f"Missing: {name}"

    def test_exception_hierarchy(self):
        assert issubclass(InvestmentNotFoundError,       InvestmentEngineError)
        assert issubclass(EngineAlreadyRunningError,     InvestmentEngineError)
        assert issubclass(DomainEngineNotFoundError,     InvestmentEngineError)

    def test_version(self):
        import iios.investment as pkg
        assert pkg.__version__ == "1.0.0"
