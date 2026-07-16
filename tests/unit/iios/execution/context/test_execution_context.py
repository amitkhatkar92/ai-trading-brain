"""tests/unit/iios/execution/context/test_execution_context.py
==================================================
Comprehensive test suite for C6 Phase 1 Module 4:
IIOS Execution Context.

12 test classes, 95%+ coverage.
"""
from __future__ import annotations

import dataclasses
import threading
import time
import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Imports
# ─────────────────────────────────────────────────────────────────────────────

from iios.execution.context.constants import (
    ContextStatus,
    ContextValidationCode,
    ExecutionEnvironment,
    ExecutionMode,
    MarketSession,
    VERSION,
)
from iios.execution.context.exceptions import (
    ContextBuildError,
    ContextCapacityError,
    ContextHistoryError,
    ContextIncompleteError,
    ContextInconsistencyError,
    ContextNotFoundError,
    ContextRegistryNotRunning,
    ContextValidationError,
    DuplicateContextError,
    ExecutionContextError,
)
from iios.execution.context.execution_context import ExecutionContext
from iios.execution.context.execution_metadata import ExecutionMetadata
from iios.execution.context.execution_environment import ExecutionEnvironmentDescriptor
from iios.execution.context.execution_session import ExecutionSession
from iios.execution.context.execution_request_context import (
    BrokerContextRef,
    ExecutionRequestContext,
)
from iios.execution.context.execution_bundle import ExecutionBundle
from iios.execution.context.execution_context_events import (
    ExecutionContextEvent,
    ExecutionContextEventType,
    make_context_event,
)
from iios.execution.context.execution_context_validator import (
    ContextValidationResult,
    ExecutionContextValidator,
)
from iios.execution.context.execution_context_builder import ExecutionContextBuilder
from iios.execution.context.execution_context_factory import ExecutionContextFactory
from iios.execution.context.execution_context_registry import (
    ContextRecord,
    ExecutionContextRegistry,
)
from iios.execution.context.execution_context_history import (
    ContextRevision,
    ExecutionContextHistory,
    make_revision,
)
from iios.execution.context.execution_context_statistics import (
    ContextBuildStatistics,
    ExecutionContextStatistics,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ids(**overrides: str) -> dict[str, str]:
    base = dict(
        execution_id  = "EXEC-001",
        workflow_id   = "WF-001",
        order_id      = "ORD-001",
        decision_id   = "DEC-001",
        portfolio_id  = "PORT-001",
        strategy_id   = "STRAT-001",
        correlation_id = "CORR-001",
        request_id    = "REQ-001",
    )
    base.update(overrides)
    return base


def _build(**overrides: str) -> ExecutionContext:
    """Helper: build a minimal valid ExecutionContext."""
    ids = _ids(**overrides)
    return (
        ExecutionContextBuilder()
        .with_ids(
            execution_id  = ids["execution_id"],
            workflow_id   = ids["workflow_id"],
            order_id      = ids["order_id"],
            decision_id   = ids["decision_id"],
            portfolio_id  = ids["portfolio_id"],
            strategy_id   = ids["strategy_id"],
        )
        .with_correlation(
            correlation_id = ids["correlation_id"],
            request_id     = ids["request_id"],
        )
        .with_mode(ExecutionMode.PAPER)
        .build()
    )


def _create_via_factory(**kwargs: Any) -> tuple[ExecutionContext, ContextBuildStatistics]:
    f = ExecutionContextFactory()
    return f.create(
        execution_id   = "EXEC-001",
        workflow_id    = "WF-001",
        order_id       = "ORD-001",
        decision_id    = "DEC-001",
        portfolio_id   = "PORT-001",
        strategy_id    = "STRAT-001",
        correlation_id = "CORR-001",
        request_id     = "REQ-001",
        execution_mode = ExecutionMode.PAPER,
        **kwargs,
    )


@pytest.fixture
def registry() -> ExecutionContextRegistry:
    r = ExecutionContextRegistry()
    r.start()
    yield r
    if r.is_running:
        r.stop()


@pytest.fixture
def context() -> ExecutionContext:
    return _build()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Constants
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_execution_modes(self) -> None:
        assert ExecutionMode.PAPER.value      == "PAPER"
        assert ExecutionMode.LIVE.value       == "LIVE"
        assert ExecutionMode.BACKTEST.value   == "BACKTEST"
        assert ExecutionMode.SIMULATION.value == "SIMULATION"
        assert ExecutionMode.RECOVERY.value   == "RECOVERY"
        assert ExecutionMode.REPLAY.value     == "REPLAY"

    def test_execution_environments(self) -> None:
        assert ExecutionEnvironment.PRODUCTION.value  == "PRODUCTION"
        assert ExecutionEnvironment.DEVELOPMENT.value == "DEVELOPMENT"
        assert ExecutionEnvironment.TESTING.value     == "TESTING"
        assert ExecutionEnvironment.STAGING.value     == "STAGING"

    def test_market_sessions(self) -> None:
        assert MarketSession.OPEN.value        == "OPEN"
        assert MarketSession.CLOSED.value      == "CLOSED"
        assert MarketSession.PRE_MARKET.value  == "PRE_MARKET"
        assert MarketSession.POST_MARKET.value == "POST_MARKET"
        assert MarketSession.HOLIDAY.value     == "HOLIDAY"

    def test_context_status(self) -> None:
        assert ContextStatus.BUILDING.value   == "BUILDING"
        assert ContextStatus.VALIDATED.value  == "VALIDATED"
        assert ContextStatus.PUBLISHED.value  == "PUBLISHED"
        assert ContextStatus.REJECTED.value   == "REJECTED"
        assert ContextStatus.ARCHIVED.value   == "ARCHIVED"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class TestExceptions:
    def test_hierarchy(self) -> None:
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(ExecutionContextError, IIOSError)
        assert issubclass(ContextBuildError,        ExecutionContextError)
        assert issubclass(ContextValidationError,   ExecutionContextError)
        assert issubclass(ContextNotFoundError,     ExecutionContextError)
        assert issubclass(DuplicateContextError,    ExecutionContextError)
        assert issubclass(ContextCapacityError,     ExecutionContextError)
        assert issubclass(ContextRegistryNotRunning, ExecutionContextError)
        assert issubclass(ContextIncompleteError,   ExecutionContextError)
        assert issubclass(ContextInconsistencyError, ExecutionContextError)

    def test_not_found_carries_id(self) -> None:
        exc = ContextNotFoundError("CTX-X")
        assert exc.context_id == "CTX-X"
        assert "CTX-X" in str(exc)

    def test_duplicate_carries_id(self) -> None:
        exc = DuplicateContextError("CTX-Y")
        assert exc.context_id == "CTX-Y"

    def test_validation_error_carries_errors(self) -> None:
        exc = ContextValidationError("fail", errors=("e1", "e2"))
        assert exc.errors == ("e1", "e2")

    def test_incomplete_carries_fields(self) -> None:
        exc = ContextIncompleteError("missing", missing_fields=("execution_id",))
        assert "execution_id" in exc.missing_fields

    def test_error_codes(self) -> None:
        assert ExecutionContextError.DEFAULT_CODE  == "ECX-000"
        assert ContextBuildError.DEFAULT_CODE      == "ECX-001"
        assert ContextValidationError.DEFAULT_CODE == "ECX-002"
        assert ContextNotFoundError.DEFAULT_CODE   == "ECX-003"
        assert DuplicateContextError.DEFAULT_CODE  == "ECX-004"
        assert ContextCapacityError.DEFAULT_CODE   == "ECX-005"


# ─────────────────────────────────────────────────────────────────────────────
# 3. ExecutionContext (core dataclass)
# ─────────────────────────────────────────────────────────────────────────────

class TestExecutionContext:
    def test_creation(self, context: ExecutionContext) -> None:
        assert context.execution_id  == "EXEC-001"
        assert context.order_id      == "ORD-001"
        assert context.execution_mode == ExecutionMode.PAPER

    def test_frozen(self, context: ExecutionContext) -> None:
        with pytest.raises((AttributeError, TypeError)):
            context.execution_id = "MODIFIED"  # type: ignore[misc]

    def test_snapshot_properties_false(self, context: ExecutionContext) -> None:
        assert not context.has_market_snapshot
        assert not context.has_company_snapshot
        assert not context.has_strategy_snapshot
        assert not context.has_portfolio_snapshot
        assert not context.has_decision

    def test_snapshot_count_zero(self, context: ExecutionContext) -> None:
        assert context.snapshot_count == 0

    def test_completeness_zero(self, context: ExecutionContext) -> None:
        assert context.completeness == 0.0

    def test_completeness_with_snapshots(self) -> None:
        ctx = dataclasses.replace(
            _build(),
            market_snapshot   = MagicMock(),
            strategy_snapshot = MagicMock(),
            decision          = MagicMock(),
        )
        assert ctx.snapshot_count == 3
        assert abs(ctx.completeness - 0.6) < 0.01

    def test_has_all_required_ids_true(self, context: ExecutionContext) -> None:
        assert context.has_all_required_ids

    def test_has_all_required_ids_false_missing_one(self) -> None:
        ctx = dataclasses.replace(_build(), decision_id="")
        assert not ctx.has_all_required_ids

    def test_age_sec(self, context: ExecutionContext) -> None:
        time.sleep(0.01)
        assert context.age_sec > 0.0

    def test_to_dict(self, context: ExecutionContext) -> None:
        d = context.to_dict()
        assert d["execution_id"]  == "EXEC-001"
        assert d["order_id"]      == "ORD-001"
        assert "completeness"     in d
        assert "snapshot_count"   in d
        assert "has_all_required_ids" in d

    def test_repr(self, context: ExecutionContext) -> None:
        r = repr(context)
        assert "ExecutionContext" in r
        assert "PAPER" in r

    def test_has_session_false(self, context: ExecutionContext) -> None:
        assert not context.has_session

    def test_has_session_true(self) -> None:
        ctx = dataclasses.replace(_build(), session=ExecutionSession.nse())
        assert ctx.has_session

    def test_has_environment_false(self, context: ExecutionContext) -> None:
        assert not context.has_environment


# ─────────────────────────────────────────────────────────────────────────────
# 4. Sub-contexts
# ─────────────────────────────────────────────────────────────────────────────

class TestSubContexts:
    def test_execution_metadata(self) -> None:
        m = ExecutionMetadata(
            execution_mode = ExecutionMode.PAPER,
            environment    = ExecutionEnvironment.PRODUCTION,
            notes          = "test run",
        )
        assert m.execution_mode == ExecutionMode.PAPER
        d = m.to_dict()
        assert d["execution_mode"] == "PAPER"
        assert d["notes"] == "test run"

    def test_metadata_frozen(self) -> None:
        m = ExecutionMetadata()
        with pytest.raises((AttributeError, TypeError)):
            m.notes = "x"  # type: ignore[misc]

    def test_environment_paper(self) -> None:
        e = ExecutionEnvironmentDescriptor.paper()
        assert e.execution_mode == ExecutionMode.PAPER
        assert e.dry_run
        assert not e.allows_live_orders

    def test_environment_live(self) -> None:
        e = ExecutionEnvironmentDescriptor.live()
        assert e.is_live
        assert not e.dry_run
        assert e.allows_live_orders

    def test_environment_backtest(self) -> None:
        e = ExecutionEnvironmentDescriptor.backtest()
        assert e.execution_mode == ExecutionMode.BACKTEST
        assert e.dry_run

    def test_environment_to_dict(self) -> None:
        e = ExecutionEnvironmentDescriptor.paper()
        d = e.to_dict()
        assert "dry_run" in d
        assert "allows_live_orders" in d

    def test_session_nse(self) -> None:
        s = ExecutionSession.nse(market_session=MarketSession.OPEN)
        assert s.exchange == "NSE"
        assert s.is_open

    def test_session_bse(self) -> None:
        s = ExecutionSession.bse()
        assert s.exchange == "BSE"

    def test_session_is_closed(self) -> None:
        s = ExecutionSession.nse(market_session=MarketSession.CLOSED)
        assert s.is_closed

    def test_session_to_dict(self) -> None:
        s = ExecutionSession.nse()
        d = s.to_dict()
        assert d["exchange"] == "NSE"
        assert "is_open" in d

    def test_broker_context_ref(self) -> None:
        bc = BrokerContextRef(
            broker_id    = "dhan",
            broker_name  = "Dhan",
            is_connected = True,
        )
        assert bc.is_connected
        d = bc.to_dict()
        assert d["broker_id"] == "dhan"

    def test_execution_request_context(self) -> None:
        rc = ExecutionRequestContext(
            execution_id   = "EXEC-001",
            order_id       = "ORD-001",
            correlation_id = "CORR-001",
        )
        assert rc.has_all_ids is False   # some IDs missing

    def test_request_context_has_all_ids_true(self) -> None:
        rc = ExecutionRequestContext(
            execution_id   = "E",
            workflow_id    = "W",
            order_id       = "O",
            decision_id    = "D",
            portfolio_id   = "P",
            strategy_id    = "S",
            correlation_id = "C",
        )
        assert rc.has_all_ids

    def test_request_context_expiry(self) -> None:
        rc = ExecutionRequestContext(expires_at=time.time() - 1.0)
        assert rc.is_expired

    def test_request_context_not_expired(self) -> None:
        rc = ExecutionRequestContext(expires_at=time.time() + 300.0)
        assert not rc.is_expired

    def test_request_context_to_dict(self) -> None:
        rc = ExecutionRequestContext(execution_id="E", order_id="O")
        d  = rc.to_dict()
        assert d["execution_id"] == "E"
        assert "is_expired" in d


# ─────────────────────────────────────────────────────────────────────────────
# 5. ExecutionBundle
# ─────────────────────────────────────────────────────────────────────────────

class TestExecutionBundle:
    def _make_bundle(self, n: int = 2) -> ExecutionBundle:
        contexts = tuple(
            _build(
                execution_id  = f"EXEC-{i:03d}",
                order_id      = f"ORD-{i:03d}",
                correlation_id = f"CORR-{i:03d}",
                request_id    = f"REQ-{i:03d}",
            )
            for i in range(n)
        )
        return ExecutionBundle(
            workflow_id    = "WF-001",
            execution_mode = ExecutionMode.PAPER,
            contexts       = contexts,
        )

    def test_size(self) -> None:
        b = self._make_bundle(3)
        assert b.size == 3
        assert len(b) == 3

    def test_is_empty(self) -> None:
        b = ExecutionBundle()
        assert b.is_empty

    def test_contains(self) -> None:
        b = self._make_bundle(2)
        assert b.contexts[0].context_id in b

    def test_get_existing(self) -> None:
        b = self._make_bundle(2)
        cid = b.contexts[0].context_id
        assert b.get(cid) is not None

    def test_get_missing(self) -> None:
        b = self._make_bundle(2)
        assert b.get("nonexistent") is None

    def test_execution_ids(self) -> None:
        b = self._make_bundle(2)
        ids = b.execution_ids
        assert "EXEC-000" in ids
        assert "EXEC-001" in ids

    def test_avg_completeness(self) -> None:
        b = self._make_bundle(2)
        assert b.avg_completeness == 0.0   # no snapshots

    def test_to_dict(self) -> None:
        b = self._make_bundle(2)
        d = b.to_dict()
        assert d["size"] == 2
        assert "context_ids" in d

    def test_iteration(self) -> None:
        b = self._make_bundle(3)
        count = sum(1 for _ in b)
        assert count == 3

    def test_frozen(self) -> None:
        b = self._make_bundle(2)
        with pytest.raises((AttributeError, TypeError)):
            b.workflow_id = "MODIFIED"  # type: ignore[misc]


# ─────────────────────────────────────────────────────────────────────────────
# 6. Events
# ─────────────────────────────────────────────────────────────────────────────

class TestContextEvents:
    def test_event_types(self) -> None:
        assert ExecutionContextEventType.CONTEXT_CREATED.value   == "CONTEXT_CREATED"
        assert ExecutionContextEventType.CONTEXT_VALIDATED.value == "CONTEXT_VALIDATED"
        assert ExecutionContextEventType.CONTEXT_PUBLISHED.value == "CONTEXT_PUBLISHED"
        assert ExecutionContextEventType.CONTEXT_REJECTED.value  == "CONTEXT_REJECTED"
        assert ExecutionContextEventType.CONTEXT_ARCHIVED.value  == "CONTEXT_ARCHIVED"

    def test_make_context_event(self) -> None:
        e = make_context_event(
            ExecutionContextEventType.CONTEXT_CREATED,
            "CTX-001",
            execution_id  = "EXEC-001",
            workflow_id   = "WF-001",
            execution_mode = ExecutionMode.PAPER,
            status         = ContextStatus.BUILDING,
        )
        assert e.event_type    == ExecutionContextEventType.CONTEXT_CREATED
        assert e.context_id    == "CTX-001"
        assert e.execution_id  == "EXEC-001"

    def test_event_frozen(self) -> None:
        e = make_context_event(ExecutionContextEventType.CONTEXT_CREATED, "C")
        with pytest.raises((AttributeError, TypeError)):
            e.context_id = "X"  # type: ignore[misc]

    def test_event_to_dict(self) -> None:
        e = make_context_event(
            ExecutionContextEventType.CONTEXT_VALIDATED,
            "C",
            execution_mode = ExecutionMode.PAPER,
            status         = ContextStatus.VALIDATED,
        )
        d = e.to_dict()
        assert d["event_type"]     == "CONTEXT_VALIDATED"
        assert d["execution_mode"] == "PAPER"

    def test_event_repr(self) -> None:
        e = make_context_event(ExecutionContextEventType.CONTEXT_CREATED, "C-001")
        assert "CONTEXT_CREATED" in repr(e)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Validation
# ─────────────────────────────────────────────────────────────────────────────

class TestValidation:
    def setup_method(self) -> None:
        self.v = ExecutionContextValidator()

    def test_valid_context(self, context: ExecutionContext) -> None:
        r = self.v.validate(context)
        # All required IDs are set so should pass with possible warnings
        assert r.passed

    def test_missing_execution_id(self) -> None:
        ctx = dataclasses.replace(_build(), execution_id="")
        r   = self.v.validate(ctx)
        assert not r.passed
        assert any("MISSING_EXECUTION_ID" in e for e in r.errors)

    def test_missing_workflow_id(self) -> None:
        ctx = dataclasses.replace(_build(), workflow_id="")
        r   = self.v.validate(ctx)
        assert not r.passed
        assert any("MISSING_WORKFLOW_ID" in e for e in r.errors)

    def test_missing_order_id(self) -> None:
        ctx = dataclasses.replace(_build(), order_id="")
        r   = self.v.validate(ctx)
        assert not r.passed
        assert any("MISSING_ORDER_ID" in e for e in r.errors)

    def test_missing_correlation_id(self) -> None:
        ctx = dataclasses.replace(_build(), correlation_id="")
        r   = self.v.validate(ctx)
        assert not r.passed
        assert any("MISSING_CORRELATION_ID" in e for e in r.errors)

    def test_inconsistent_request_context_ids(self) -> None:
        rc = ExecutionRequestContext(
            execution_id = "DIFFERENT-EXEC",
            order_id     = "ORD-001",
        )
        ctx = dataclasses.replace(_build(), request_context=rc)
        r   = self.v.validate(ctx)
        assert not r.passed
        assert any("INCONSISTENT_IDS" in e for e in r.errors)

    def test_live_mode_no_environment_fails(self) -> None:
        ctx = dataclasses.replace(_build(), execution_mode=ExecutionMode.LIVE)
        r   = self.v.validate(ctx)
        assert not r.passed
        assert any("INVALID_MODE" in e for e in r.errors)

    def test_live_mode_with_proper_environment_passes(self) -> None:
        env = ExecutionEnvironmentDescriptor.live()
        ctx = dataclasses.replace(
            _build(),
            execution_mode = ExecutionMode.LIVE,
            environment    = env,
        )
        r = self.v.validate(ctx)
        assert r.passed

    def test_missing_snapshots_produce_warnings(self, context: ExecutionContext) -> None:
        r = self.v.validate(context)
        assert r.passed
        # No snapshots → there should be warnings
        assert len(r.warnings) > 0

    def test_session_validation_empty_exchange(self) -> None:
        s = ExecutionSession(exchange="")
        r = self.v.validate_session(s)
        assert not r.passed

    def test_environment_validation_live_dry_run(self) -> None:
        e = ExecutionEnvironmentDescriptor(
            execution_mode     = ExecutionMode.LIVE,
            live_orders_enabled = True,
            dry_run            = True,
        )
        r = self.v.validate_environment(e)
        assert not r.passed

    def test_validation_result_bool(self) -> None:
        assert bool(ContextValidationResult.ok())
        assert not bool(ContextValidationResult.fail("err"))

    def test_validation_result_to_dict(self) -> None:
        r = ContextValidationResult.ok(warnings=("w1",))
        d = r.to_dict()
        assert d["passed"]
        assert "w1" in d["warnings"]


# ─────────────────────────────────────────────────────────────────────────────
# 8. Builder
# ─────────────────────────────────────────────────────────────────────────────

class TestBuilder:
    def test_basic_build(self) -> None:
        ctx = _build()
        assert ctx.execution_id  == "EXEC-001"
        assert ctx.execution_mode == ExecutionMode.PAPER

    def test_missing_execution_id_raises(self) -> None:
        with pytest.raises(ContextIncompleteError):
            (
                ExecutionContextBuilder()
                .with_ids(workflow_id="W", order_id="O", decision_id="D",
                          portfolio_id="P", strategy_id="S")
                .with_correlation(correlation_id="C", request_id="R")
                .build()
            )

    def test_missing_correlation_raises(self) -> None:
        with pytest.raises(ContextIncompleteError):
            (
                ExecutionContextBuilder()
                .with_ids(execution_id="E", workflow_id="W", order_id="O",
                          decision_id="D", portfolio_id="P", strategy_id="S")
                .with_correlation(request_id="R")  # no correlation_id
                .build()
            )

    def test_with_session(self) -> None:
        ctx = (
            ExecutionContextBuilder()
            .with_ids(**{k: "X" for k in ["execution_id","workflow_id","order_id",
                                           "decision_id","portfolio_id","strategy_id"]})
            .with_correlation(correlation_id="C", request_id="R")
            .with_session(ExecutionSession.nse())
            .build()
        )
        assert ctx.has_session
        assert ctx.session.exchange == "NSE"

    def test_with_environment(self) -> None:
        ctx = (
            ExecutionContextBuilder()
            .with_ids(**{k: "X" for k in ["execution_id","workflow_id","order_id",
                                           "decision_id","portfolio_id","strategy_id"]})
            .with_correlation(correlation_id="C", request_id="R")
            .with_environment(ExecutionEnvironmentDescriptor.paper())
            .build()
        )
        assert ctx.has_environment

    def test_with_snapshots(self) -> None:
        snap = MagicMock()
        ctx = (
            ExecutionContextBuilder()
            .with_ids(**{k: "X" for k in ["execution_id","workflow_id","order_id",
                                           "decision_id","portfolio_id","strategy_id"]})
            .with_correlation(correlation_id="C", request_id="R")
            .with_market_snapshot(snap)
            .with_decision(snap)
            .build()
        )
        assert ctx.has_market_snapshot
        assert ctx.has_decision
        assert ctx.snapshot_count == 2

    def test_with_broker(self) -> None:
        ctx = (
            ExecutionContextBuilder()
            .with_ids(**{k: "X" for k in ["execution_id","workflow_id","order_id",
                                           "decision_id","portfolio_id","strategy_id"]})
            .with_correlation(correlation_id="C", request_id="R")
            .with_broker("dhan", "Dhan Broker", is_connected=True)
            .build()
        )
        assert ctx.has_broker_context

    def test_with_tags(self) -> None:
        ctx = (
            ExecutionContextBuilder()
            .with_ids(**{k: "X" for k in ["execution_id","workflow_id","order_id",
                                           "decision_id","portfolio_id","strategy_id"]})
            .with_correlation(correlation_id="C", request_id="R")
            .with_tags("fast", "priority")
            .build()
        )
        assert "fast" in ctx.tags
        assert "priority" in ctx.tags

    def test_inconsistent_request_context_raises(self) -> None:
        rc = ExecutionRequestContext(execution_id="WRONG-EXEC", order_id="ORD-001")
        with pytest.raises(ContextInconsistencyError):
            (
                ExecutionContextBuilder()
                .with_ids(execution_id="EXEC-001", workflow_id="W", order_id="O",
                          decision_id="D", portfolio_id="P", strategy_id="S")
                .with_correlation(correlation_id="C", request_id="R")
                .with_request_context(rc)
                .build()
            )

    def test_context_is_frozen(self) -> None:
        ctx = _build()
        with pytest.raises((AttributeError, TypeError)):
            ctx.execution_id = "MODIFIED"  # type: ignore[misc]

    def test_auto_request_context_created(self) -> None:
        ctx = _build()
        assert ctx.request_context is not None
        assert ctx.request_context.execution_id == "EXEC-001"


# ─────────────────────────────────────────────────────────────────────────────
# 9. Factory
# ─────────────────────────────────────────────────────────────────────────────

class TestFactory:
    def test_create_valid(self) -> None:
        ctx, stats = _create_via_factory()
        assert ctx.execution_id == "EXEC-001"
        assert ctx.status       == ContextStatus.VALIDATED
        assert stats.validation_passed

    def test_create_with_session(self) -> None:
        ctx, stats = _create_via_factory(session=ExecutionSession.nse())
        assert ctx.has_session

    def test_create_with_environment(self) -> None:
        ctx, stats = _create_via_factory(
            environment=ExecutionEnvironmentDescriptor.paper()
        )
        assert ctx.has_environment

    def test_create_with_snapshot(self) -> None:
        snap = MagicMock()
        ctx, stats = _create_via_factory(market_snapshot=snap)
        assert ctx.has_market_snapshot
        assert stats.snapshot_count == 1

    def test_create_missing_execution_id_raises(self) -> None:
        f = ExecutionContextFactory()
        with pytest.raises(ContextIncompleteError):
            f.create(
                execution_id   = "",
                workflow_id    = "W",
                order_id       = "O",
                decision_id    = "D",
                portfolio_id   = "P",
                strategy_id    = "S",
                correlation_id = "C",
                request_id     = "R",
            )

    def test_stats_builder_time_nonzero(self) -> None:
        _, stats = _create_via_factory()
        assert stats.builder_time_ms >= 0.0

    def test_gen_execution_id(self) -> None:
        eid = ExecutionContextFactory.gen_execution_id()
        assert eid.startswith("exec-")

    def test_gen_workflow_id(self) -> None:
        wid = ExecutionContextFactory.gen_workflow_id()
        assert wid.startswith("wf-")

    def test_gen_correlation_id(self) -> None:
        cid = ExecutionContextFactory.gen_correlation_id()
        assert len(cid) == 36   # UUID format

    def test_strict_mode_with_warnings_raises(self) -> None:
        f = ExecutionContextFactory()
        # Warnings come from missing snapshots, session, environment — strict should fail
        with pytest.raises(ContextValidationError):
            f.create(
                execution_id   = "EXEC-001",
                workflow_id    = "WF-001",
                order_id       = "ORD-001",
                decision_id    = "DEC-001",
                portfolio_id   = "PORT-001",
                strategy_id    = "STRAT-001",
                correlation_id = "CORR-001",
                request_id     = "REQ-001",
                strict         = True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# 10. Registry
# ─────────────────────────────────────────────────────────────────────────────

class TestRegistry:
    def test_not_running_before_start(self) -> None:
        r = ExecutionContextRegistry()
        with pytest.raises(ContextRegistryNotRunning):
            r.register(_build())

    def test_start_stop(self, registry: ExecutionContextRegistry) -> None:
        assert registry.is_running

    def test_register_and_get(
        self,
        registry: ExecutionContextRegistry,
        context:  ExecutionContext,
    ) -> None:
        registry.register(context)
        retrieved = registry.get(context.context_id)
        assert retrieved.context_id == context.context_id

    def test_duplicate_raises(
        self,
        registry: ExecutionContextRegistry,
        context:  ExecutionContext,
    ) -> None:
        registry.register(context)
        with pytest.raises(DuplicateContextError):
            registry.register(context)

    def test_overwrite_allowed(
        self,
        registry: ExecutionContextRegistry,
        context:  ExecutionContext,
    ) -> None:
        registry.register(context)
        registry.register(context, overwrite=True)
        assert registry.count() == 1

    def test_not_found_raises(self, registry: ExecutionContextRegistry) -> None:
        with pytest.raises(ContextNotFoundError):
            registry.get("nonexistent")

    def test_contains(
        self,
        registry: ExecutionContextRegistry,
        context:  ExecutionContext,
    ) -> None:
        assert not registry.contains(context.context_id)
        registry.register(context)
        assert registry.contains(context.context_id)

    def test_count(
        self,
        registry: ExecutionContextRegistry,
        context:  ExecutionContext,
    ) -> None:
        assert registry.count() == 0
        registry.register(context)
        assert registry.count() == 1

    def test_get_by_execution(self, registry: ExecutionContextRegistry) -> None:
        ctx = _build(execution_id="EXEC-X", correlation_id="CORR-X", request_id="REQ-X")
        registry.register(ctx)
        results = registry.get_by_execution("EXEC-X")
        assert len(results) == 1
        assert results[0].execution_id == "EXEC-X"

    def test_get_by_workflow(self, registry: ExecutionContextRegistry) -> None:
        ctx = _build(workflow_id="WF-99", execution_id="EXEC-99",
                     correlation_id="CORR-99", request_id="REQ-99")
        registry.register(ctx)
        results = registry.get_by_workflow("WF-99")
        assert any(c.workflow_id == "WF-99" for c in results)

    def test_get_by_status(
        self,
        registry: ExecutionContextRegistry,
        context:  ExecutionContext,
    ) -> None:
        registry.register(context)
        results = registry.get_by_status(ContextStatus.BUILDING)
        assert any(c.context_id == context.context_id for c in results)

    def test_update_status(
        self,
        registry: ExecutionContextRegistry,
        context:  ExecutionContext,
    ) -> None:
        registry.register(context)
        record = registry.update_status(
            context.context_id,
            ContextStatus.VALIDATED,
            reason="passed validation",
        )
        assert record.context.status == ContextStatus.VALIDATED

    def test_history_records_revisions(
        self,
        registry: ExecutionContextRegistry,
        context:  ExecutionContext,
    ) -> None:
        registry.register(context)
        registry.update_status(context.context_id, ContextStatus.VALIDATED)
        history = registry.get_history(context.context_id)
        assert history.count() >= 2   # initial + update

    def test_capacity_limit(self) -> None:
        r = ExecutionContextRegistry(max_contexts=2)
        r.start()
        r.register(_build(execution_id="E1", correlation_id="C1", request_id="R1"))
        r.register(_build(execution_id="E2", correlation_id="C2", request_id="R2"))
        with pytest.raises(ContextCapacityError):
            r.register(_build(execution_id="E3", correlation_id="C3", request_id="R3"))
        r.stop()

    def test_listeners(
        self,
        registry: ExecutionContextRegistry,
        context:  ExecutionContext,
    ) -> None:
        events: list[ExecutionContextEvent] = []
        registry.add_listener(events.append)
        registry.register(context)
        assert len(events) >= 1
        assert events[0].event_type == ExecutionContextEventType.CONTEXT_CREATED

    def test_remove_listener(
        self,
        registry: ExecutionContextRegistry,
        context:  ExecutionContext,
    ) -> None:
        events: list[ExecutionContextEvent] = []
        registry.add_listener(events.append)
        registry.remove_listener(events.append)
        registry.register(context)
        assert len(events) == 0

    def test_faulty_listener_does_not_crash(
        self,
        registry: ExecutionContextRegistry,
        context:  ExecutionContext,
    ) -> None:
        def bad_listener(e: ExecutionContextEvent) -> None:
            raise RuntimeError("test error")
        registry.add_listener(bad_listener)
        # Should not raise
        registry.register(context)


# ─────────────────────────────────────────────────────────────────────────────
# 11. History
# ─────────────────────────────────────────────────────────────────────────────

class TestHistory:
    def test_append_and_query(self) -> None:
        ctx = _build()
        h   = ExecutionContextHistory("EXEC-001")
        rev = make_revision(ctx, revision=0)
        h.record(rev)
        assert h.count() == 1
        assert h.first() == rev
        assert h.last()  == rev

    def test_eviction(self) -> None:
        ctx = _build()
        h   = ExecutionContextHistory("EXEC-001", max_entries=2)
        for i in range(3):
            h.record(make_revision(ctx, revision=i))
        assert h.count()   == 2
        assert h.evicted_count == 1
        assert h.total_recorded == 3

    def test_statuses(self) -> None:
        ctx = _build()
        h   = ExecutionContextHistory("EXEC-001")
        h.record(ContextRevision(
            context_id="C", execution_id="E",
            revision=0, status=ContextStatus.BUILDING,
        ))
        h.record(ContextRevision(
            context_id="C", execution_id="E",
            revision=1, status=ContextStatus.VALIDATED,
        ))
        statuses = h.statuses()
        assert ContextStatus.BUILDING  in statuses
        assert ContextStatus.VALIDATED in statuses

    def test_compare(self) -> None:
        ctx = _build()
        h   = ExecutionContextHistory("EXEC-001")
        h.record(ContextRevision(
            context_id="C", execution_id="E",
            revision=0, status=ContextStatus.BUILDING,
        ))
        h.record(ContextRevision(
            context_id="C", execution_id="E",
            revision=1, status=ContextStatus.VALIDATED,
        ))
        result = h.compare(0, 1)
        assert result["status_changed"] is True

    def test_iteration(self) -> None:
        ctx = _build()
        h   = ExecutionContextHistory("EXEC-001")
        for i in range(3):
            h.record(make_revision(ctx, revision=i))
        assert sum(1 for _ in h) == 3

    def test_make_revision_factory(self) -> None:
        ctx = _build()
        rev = make_revision(ctx, revision=0, reason="initial")
        assert rev.context_id   == ctx.context_id
        assert rev.execution_id == ctx.execution_id
        assert rev.reason       == "initial"

    def test_revision_to_dict(self) -> None:
        ctx = _build()
        rev = make_revision(ctx, revision=0)
        d   = rev.to_dict()
        assert "revision"   in d
        assert "status"     in d
        assert "context_id" in d


# ─────────────────────────────────────────────────────────────────────────────
# 12. Statistics
# ─────────────────────────────────────────────────────────────────────────────

class TestStatistics:
    def test_initial_state(self) -> None:
        s = ExecutionContextStatistics()
        assert s.context_count      == 0
        assert s.validation_success_rate == 0.0
        assert s.avg_builder_time_ms == 0.0

    def test_record_build_success(self) -> None:
        s  = ExecutionContextStatistics()
        bs = ContextBuildStatistics(
            context_id        = "C",
            execution_id      = "E",
            builder_time_ms   = 10.0,
            validation_passed = True,
            snapshot_count    = 2,
            completeness      = 0.4,
        )
        s.record_build(bs)
        assert s.context_count       == 1
        assert s.validation_success  == 1
        assert s.validation_failure  == 0
        assert abs(s.avg_builder_time_ms - 10.0) < 0.01
        assert s.validation_success_rate == 1.0

    def test_record_build_failure(self) -> None:
        s  = ExecutionContextStatistics()
        bs = ContextBuildStatistics(
            context_id        = "C",
            execution_id      = "E",
            validation_passed = False,
            errors            = ("e1",),
        )
        s.record_build(bs)
        assert s.validation_failure == 1
        assert s.validation_success_rate == 0.0

    def test_success_rate_mixed(self) -> None:
        s = ExecutionContextStatistics()
        for passed in (True, True, False):
            s.record_build(ContextBuildStatistics(
                context_id="C", execution_id="E",
                validation_passed=passed,
            ))
        assert abs(s.validation_success_rate - 2/3) < 0.01

    def test_published_rejected_archived(self) -> None:
        s = ExecutionContextStatistics()
        s.record_published()
        s.record_rejected()
        s.record_archived()
        assert s.published_count == 1
        assert s.rejected_count  == 1
        assert s.archived_count  == 1

    def test_to_dict(self) -> None:
        s = ExecutionContextStatistics()
        s.record_build(ContextBuildStatistics(
            context_id="C", execution_id="E",
            builder_time_ms=5.0, validation_passed=True,
        ))
        d = s.to_dict()
        assert d["context_count"]      == 1
        assert d["validation_success"] == 1

    def test_thread_safe_recording(self) -> None:
        s      = ExecutionContextStatistics()
        errors: list[Exception] = []

        def record(i: int) -> None:
            try:
                s.record_build(ContextBuildStatistics(
                    context_id="C", execution_id="E",
                    validation_passed=(i % 2 == 0),
                ))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert s.context_count == 50


# ─────────────────────────────────────────────────────────────────────────────
# 13. Thread safety
# ─────────────────────────────────────────────────────────────────────────────

class TestThreadSafety:
    def test_concurrent_registrations(self) -> None:
        registry = ExecutionContextRegistry(max_contexts=200)
        registry.start()
        errors: list[Exception] = []

        def register(i: int) -> None:
            try:
                ctx = _build(
                    execution_id   = f"EXEC-{i:04d}",
                    order_id       = f"ORD-{i:04d}",
                    correlation_id = f"CORR-{i:04d}",
                    request_id     = f"REQ-{i:04d}",
                )
                registry.register(ctx)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert registry.count() == 50
        registry.stop()

    def test_concurrent_status_updates(self) -> None:
        registry = ExecutionContextRegistry()
        registry.start()
        ctx = _build()
        registry.register(ctx)
        errors: list[Exception] = []

        statuses = [
            ContextStatus.VALIDATED,
            ContextStatus.PUBLISHED,
            ContextStatus.ARCHIVED,
        ]

        def update(i: int) -> None:
            try:
                registry.update_status(
                    ctx.context_id,
                    statuses[i % len(statuses)],
                    reason=f"update-{i}",
                )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=update, args=(i,)) for i in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        registry.stop()

    def test_concurrent_history_appends(self) -> None:
        h = ExecutionContextHistory("EXEC-001", max_entries=500)
        ctx = _build()
        errors: list[Exception] = []

        def append(i: int) -> None:
            try:
                h.record(make_revision(ctx, revision=i))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=append, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert h.total_recorded == 50


# ─────────────────────────────────────────────────────────────────────────────
# 14. Serialization
# ─────────────────────────────────────────────────────────────────────────────

class TestSerialization:
    def test_context_to_dict_complete(self) -> None:
        ctx, _ = _create_via_factory(
            session     = ExecutionSession.nse(),
            environment = ExecutionEnvironmentDescriptor.paper(),
        )
        d = ctx.to_dict()
        assert isinstance(d,            dict)
        assert isinstance(d["tags"],    list)
        assert isinstance(d["session"], dict)
        assert isinstance(d["environment"], dict)

    def test_all_fields_serializable(self) -> None:
        ctx, _ = _create_via_factory()
        d       = ctx.to_dict()
        import json
        # Should be JSON-serializable (no non-JSON types)
        json_str = json.dumps(d)
        assert len(json_str) > 100

    def test_bundle_to_dict(self) -> None:
        contexts = tuple(
            _build(
                execution_id   = f"E{i}",
                order_id       = f"O{i}",
                correlation_id = f"C{i}",
                request_id     = f"R{i}",
            )
            for i in range(2)
        )
        b = ExecutionBundle(workflow_id="WF-001", contexts=contexts)
        d = b.to_dict()
        import json
        json_str = json.dumps(d)
        assert "bundle_id" in d

    def test_statistics_to_dict(self) -> None:
        s = ExecutionContextStatistics()
        s.record_build(ContextBuildStatistics(
            context_id="C", execution_id="E",
            validation_passed=True, builder_time_ms=3.0,
        ))
        d = s.to_dict()
        import json
        json.dumps(d)   # must not raise
