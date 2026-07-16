"""tests/unit/execution/orders/test_order_router.py
==================================================
Comprehensive test suite for C6 Phase 2 M3 — Order Router.

Coverage targets: 95%+

Test classes
------------
TestConstants              — enum completeness
TestExceptions             — hierarchy, fields, codes
TestBrokerCapabilities     — frozen dataclass helpers
TestRoutingContext          — context helpers, expiry
TestRoutingRequest          — request helpers, build_context
TestRoutingCandidate        — score accumulation, discard
TestRoutingRules            — each built-in rule factory
TestRoutingPolicies         — all 7 named policies
TestRoutingStrategy         — rank + select
TestRoutingDecision         — frozen, to_dict
TestRoutingResult           — aggregate result helpers
TestRoutingEvents           — all 5 event factories
TestRoutingStatistics       — thread-safe counters
TestRoutingHistory          — bounded deque, iterators
TestRoutingValidator        — all validation paths
TestRoutingRegistry         — lifecycle, register, lookup
TestRoutingFactory          — success/rejected/result
TestOrderRouter             — full routing pipeline
TestOrderRouterConcurrency  — 100-thread stress test
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any

import pytest

from iios.execution.oms.order_router.constants import (
    BrokerCapability,
    CandidateScoreField,
    ExecutionMode,
    RoutingEventType,
    RoutingPolicyType,
    RoutingStatus,
    RoutingValidationCode,
    TERMINAL_ROUTING_STATUSES,
    DEFAULT_MAX_HISTORY,
    ROUTER_SYSTEM_ID,
    VERSION,
)
from iios.execution.oms.order_router.exceptions import (
    DuplicateRoutingError,
    NoCandidatesError,
    OrderRouterError,
    RouterCapacityError,
    RouterNotRunning,
    RoutingExpiredError,
    RoutingPolicyError,
    RoutingRejectedError,
    RoutingRequestError,
    RoutingStrategyError,
    RoutingValidationError,
)
from iios.execution.oms.order_router.routing_candidate import RoutingCandidate
from iios.execution.oms.order_router.routing_context import BrokerCapabilities, RoutingContext
from iios.execution.oms.order_router.routing_decision import RoutingDecision
from iios.execution.oms.order_router.routing_events import (
    RoutingEvent,
    make_candidate_evaluated,
    make_route_selected,
    make_routing_completed,
    make_routing_rejected,
    make_routing_started,
)
from iios.execution.oms.order_router.routing_factory import RoutingFactory
from iios.execution.oms.order_router.routing_history import RoutingHistory
from iios.execution.oms.order_router.routing_policy import (
    RoutingPolicy,
    get_policy,
    make_backtest_policy,
    make_capability_policy,
    make_default_policy,
    make_exchange_policy,
    make_paper_trading_policy,
    make_priority_policy,
    make_recovery_policy,
)
from iios.execution.oms.order_router.routing_registry import RoutingRegistry
from iios.execution.oms.order_router.routing_request import RoutingRequest
from iios.execution.oms.order_router.routing_result import RoutingResult
from iios.execution.oms.order_router.routing_rule import (
    RoutingRule,
    make_availability_rule,
    make_capability_rule,
    make_exchange_rule,
    make_execution_mode_rule,
    make_order_type_rule,
    make_priority_rule,
)
from iios.execution.oms.order_router.routing_statistics import RoutingStatistics
from iios.execution.oms.order_router.routing_strategy import RoutingStrategy
from iios.execution.oms.order_router.routing_validation import RoutingValidator
from iios.execution.oms.order_router.order_router import OrderRouter


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _caps(
    broker_id:   str = "BROKER_A",
    available:   bool = True,
    exchanges:   frozenset[str] = frozenset({"NSE", "BSE"}),
    caps:        frozenset[BrokerCapability] = frozenset({
        BrokerCapability.EQUITY,
        BrokerCapability.LIMIT_ORDER,
        BrokerCapability.MARKET_ORDER,
        BrokerCapability.INTRADAY,
    }),
    order_types: frozenset[str] = frozenset({"LIMIT", "MARKET"}),
    modes:       frozenset[ExecutionMode] = frozenset({
        ExecutionMode.LIVE,
        ExecutionMode.PAPER,
    }),
    priority: int = 0,
) -> BrokerCapabilities:
    return BrokerCapabilities(
        broker_id=broker_id,
        is_available=available,
        supported_exchanges=exchanges,
        supported_capabilities=caps,
        supported_order_types=order_types,
        supported_execution_modes=modes,
        priority=priority,
    )


def _request(
    order_id:    str = "",
    instrument:  str = "RELIANCE",
    exchange:    str = "NSE",
    order_type:  str = "LIMIT",
    policy:      RoutingPolicyType = RoutingPolicyType.DEFAULT,
    mode:        ExecutionMode = ExecutionMode.LIVE,
    ttl:         float = 60.0,
    caps:        list[BrokerCapabilities] | None = None,
) -> RoutingRequest:
    return RoutingRequest(
        order_id           = order_id or str(uuid.uuid4()),
        instrument         = instrument,
        exchange           = exchange,
        order_type         = order_type,
        side               = "BUY",
        product_type       = "INTRADAY",
        execution_mode     = mode,
        policy_type        = policy,
        ttl_sec            = ttl,
        broker_capabilities = caps or [],
    )


@pytest.fixture()
def registry():
    r = RoutingRegistry()
    r.start()
    yield r
    if r.lifecycle_state().value == "RUNNING":
        r.stop()


@pytest.fixture()
def router(registry):
    r = OrderRouter(registry=registry)
    r.start()
    yield r
    if r.lifecycle_state().value == "RUNNING":
        r.stop()


@pytest.fixture()
def broker_a():
    return _caps("BROKER_A", priority=10)


@pytest.fixture()
def broker_b():
    return _caps(
        "BROKER_B",
        priority=5,
        exchanges=frozenset({"BSE"}),
        caps=frozenset({BrokerCapability.EQUITY, BrokerCapability.LIMIT_ORDER}),
        order_types=frozenset({"LIMIT"}),
    )


# ─────────────────────────────────────────────────────────────────────────────
# TestConstants
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_routing_policy_type_values(self):
        values = {p.value for p in RoutingPolicyType}
        assert "DEFAULT" in values
        assert "PRIORITY" in values
        assert "CAPABILITY" in values
        assert "EXCHANGE" in values
        assert "PAPER_TRADE" in values
        assert "BACKTEST" in values
        assert "RECOVERY" in values

    def test_execution_mode_values(self):
        assert ExecutionMode.LIVE.value == "LIVE"
        assert ExecutionMode.PAPER.value == "PAPER"
        assert ExecutionMode.BACKTEST.value == "BACKTEST"

    def test_broker_capability_includes_options(self):
        assert BrokerCapability.OPTIONS in BrokerCapability.__members__.values()

    def test_terminal_routing_statuses(self):
        assert RoutingStatus.SELECTED in TERMINAL_ROUTING_STATUSES
        assert RoutingStatus.REJECTED in TERMINAL_ROUTING_STATUSES
        assert RoutingStatus.PENDING not in TERMINAL_ROUTING_STATUSES

    def test_validation_codes(self):
        assert RoutingValidationCode.MISSING_ORDER_ID.value == "MISSING_ORDER_ID"
        assert RoutingValidationCode.NO_CANDIDATES.value == "NO_CANDIDATES"

    def test_event_types(self):
        assert RoutingEventType.ROUTING_STARTED.value == "ROUTING_STARTED"
        assert RoutingEventType.ROUTING_COMPLETED.value == "ROUTING_COMPLETED"

    def test_candidate_score_fields(self):
        assert CandidateScoreField.PRIORITY in CandidateScoreField.__members__.values()


# ─────────────────────────────────────────────────────────────────────────────
# TestExceptions
# ─────────────────────────────────────────────────────────────────────────────

class TestExceptions:
    def test_base_inherits_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(OrderRouterError, IIOSError)

    def test_all_subclass_base(self):
        subs = [
            RoutingRequestError, RoutingRejectedError, NoCandidatesError,
            RouterCapacityError, RouterNotRunning, RoutingValidationError,
            RoutingPolicyError, RoutingStrategyError, RoutingExpiredError,
            DuplicateRoutingError,
        ]
        for exc_cls in subs:
            assert issubclass(exc_cls, OrderRouterError)

    def test_routing_rejected_fields(self):
        exc = RoutingRejectedError("ORD-1", "no_broker")
        assert exc.order_id == "ORD-1"
        assert exc.reason == "no_broker"
        assert "OR-002" in exc.code

    def test_no_candidates_fields(self):
        exc = NoCandidatesError("ORD-2")
        assert exc.order_id == "ORD-2"
        assert "OR-003" in exc.code

    def test_routing_expired_fields(self):
        exc = RoutingExpiredError("ORD-3")
        assert exc.order_id == "ORD-3"
        assert "OR-009" in exc.code

    def test_duplicate_routing_fields(self):
        exc = DuplicateRoutingError("ORD-4")
        assert exc.order_id == "ORD-4"
        assert "OR-010" in exc.code

    def test_validation_error_errors_tuple(self):
        exc = RoutingValidationError("bad", errors=("E1", "E2"))
        assert exc.errors == ("E1", "E2")

    def test_default_codes(self):
        assert OrderRouterError.DEFAULT_CODE      == "OR-000"
        assert RoutingRequestError.DEFAULT_CODE   == "OR-001"
        assert RoutingRejectedError.DEFAULT_CODE  == "OR-002"
        assert NoCandidatesError.DEFAULT_CODE     == "OR-003"
        assert RouterCapacityError.DEFAULT_CODE   == "OR-004"
        assert RouterNotRunning.DEFAULT_CODE      == "OR-005"
        assert RoutingValidationError.DEFAULT_CODE == "OR-006"
        assert RoutingPolicyError.DEFAULT_CODE    == "OR-007"
        assert RoutingStrategyError.DEFAULT_CODE  == "OR-008"
        assert RoutingExpiredError.DEFAULT_CODE   == "OR-009"
        assert DuplicateRoutingError.DEFAULT_CODE == "OR-010"


# ─────────────────────────────────────────────────────────────────────────────
# TestBrokerCapabilities
# ─────────────────────────────────────────────────────────────────────────────

class TestBrokerCapabilities:
    def test_is_frozen(self):
        cap = _caps()
        with pytest.raises((AttributeError, TypeError)):
            cap.broker_id = "CHANGED"  # type: ignore[misc]

    def test_supports_capability(self):
        cap = _caps(caps=frozenset({BrokerCapability.EQUITY, BrokerCapability.OPTIONS}))
        assert cap.supports_capability(BrokerCapability.EQUITY)
        assert not cap.supports_capability(BrokerCapability.FUTURES)

    def test_supports_exchange_empty_means_all(self):
        cap = _caps(exchanges=frozenset())
        assert cap.supports_exchange("ANY_EXCHANGE")

    def test_supports_exchange_specific(self):
        cap = _caps(exchanges=frozenset({"NSE"}))
        assert cap.supports_exchange("NSE")
        assert not cap.supports_exchange("BSE")

    def test_supports_order_type_empty_means_all(self):
        cap = _caps(order_types=frozenset())
        assert cap.supports_order_type("ANYTHING")

    def test_supports_order_type_specific(self):
        cap = _caps(order_types=frozenset({"LIMIT"}))
        assert cap.supports_order_type("LIMIT")
        assert not cap.supports_order_type("MARKET")

    def test_supports_execution_mode_empty_means_all(self):
        cap = _caps(modes=frozenset())
        assert cap.supports_execution_mode(ExecutionMode.BACKTEST)

    def test_to_dict_keys(self):
        d = _caps().to_dict()
        assert "broker_id" in d
        assert "is_available" in d
        assert "priority" in d


# ─────────────────────────────────────────────────────────────────────────────
# TestRoutingContext
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingContext:
    def test_is_frozen(self):
        ctx = RoutingContext(order_id="ORD-1")
        with pytest.raises((AttributeError, TypeError)):
            ctx.order_id = "CHANGED"  # type: ignore[misc]

    def test_not_expired_when_fresh(self):
        ctx = RoutingContext(order_id="ORD-1", ttl_sec=60.0)
        assert not ctx.is_expired

    def test_expired_when_past_ttl(self):
        ctx = RoutingContext(order_id="ORD-1", created_at=time.time() - 120, ttl_sec=60.0)
        assert ctx.is_expired

    def test_is_paper(self):
        ctx = RoutingContext(execution_mode=ExecutionMode.PAPER)
        assert ctx.is_paper

    def test_is_backtest(self):
        ctx = RoutingContext(execution_mode=ExecutionMode.BACKTEST)
        assert ctx.is_backtest

    def test_to_dict_keys(self):
        ctx = RoutingContext(order_id="ORD-1")
        d = ctx.to_dict()
        assert "context_id" in d
        assert "order_id" in d
        assert "is_expired" in d


# ─────────────────────────────────────────────────────────────────────────────
# TestRoutingRequest
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingRequest:
    def test_default_request_id_is_uuid(self):
        req = _request()
        uuid.UUID(req.request_id)  # must not raise

    def test_not_expired_when_fresh(self):
        req = _request(ttl=60.0)
        assert not req.is_expired

    def test_expired_when_past_ttl(self):
        req = _request(ttl=0.001)
        time.sleep(0.002)
        assert req.is_expired

    def test_build_context_copies_fields(self):
        req = _request(order_id="ORD-5", exchange="BSE", order_type="MARKET")
        ctx = req.build_context()
        assert ctx.order_id == "ORD-5"
        assert ctx.exchange == "BSE"
        assert ctx.order_type == "MARKET"

    def test_to_dict_keys(self):
        d = _request().to_dict()
        assert "request_id" in d
        assert "order_id" in d
        assert "is_expired" in d


# ─────────────────────────────────────────────────────────────────────────────
# TestRoutingCandidate
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingCandidate:
    def test_default_is_eligible(self):
        c = RoutingCandidate(broker_id="BRK", exchange="NSE")
        assert c.is_eligible
        assert c.score == 0.0

    def test_add_score_accumulates(self):
        c = RoutingCandidate(broker_id="BRK", exchange="NSE")
        c.add_score(CandidateScoreField.PRIORITY, 5.0)
        c.add_score(CandidateScoreField.AVAILABILITY, 3.0)
        assert c.score == pytest.approx(8.0)
        assert len(c.score_breakdown) == 2

    def test_add_score_same_field_accumulates(self):
        c = RoutingCandidate(broker_id="BRK", exchange="NSE")
        c.add_score(CandidateScoreField.PRIORITY, 2.0)
        c.add_score(CandidateScoreField.PRIORITY, 3.0)
        assert c.score_breakdown[CandidateScoreField.PRIORITY] == pytest.approx(5.0)

    def test_discard_clears_score(self):
        c = RoutingCandidate(broker_id="BRK", exchange="NSE")
        c.add_score(CandidateScoreField.PRIORITY, 10.0)
        c.discard("test_reason")
        assert not c.is_eligible
        assert c.score == 0.0
        assert c.discard_reason == "test_reason"
        assert len(c.score_breakdown) == 0

    def test_to_dict_keys(self):
        c = RoutingCandidate(broker_id="BRK", exchange="NSE")
        d = c.to_dict()
        assert "broker_id" in d
        assert "score" in d
        assert "is_eligible" in d


# ─────────────────────────────────────────────────────────────────────────────
# TestRoutingRules
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingRules:
    def _ctx(self, exchange="NSE", order_type="LIMIT", mode=ExecutionMode.LIVE):
        return RoutingContext(order_id="ORD-R", exchange=exchange,
                              order_type=order_type, execution_mode=mode)

    def _candidate(self, cap: BrokerCapabilities) -> RoutingCandidate:
        return RoutingCandidate(broker_id=cap.broker_id, exchange="NSE", capabilities=cap)

    def test_availability_rule_awards_score(self):
        rule = make_availability_rule(weight=10.0)
        cap  = _caps(available=True)
        c    = self._candidate(cap)
        rule.evaluate(c, self._ctx())
        assert c.is_eligible
        assert c.score > 0

    def test_availability_rule_discards_unavailable(self):
        rule = make_availability_rule()
        cap  = _caps(available=False)
        c    = self._candidate(cap)
        rule.evaluate(c, self._ctx())
        assert not c.is_eligible

    def test_priority_rule_scores_proportional(self):
        rule  = make_priority_rule(weight=2.0)
        cap_h = _caps("BRK_H", priority=5)
        cap_l = _caps("BRK_L", priority=1)
        c_h   = self._candidate(cap_h)
        c_l   = self._candidate(cap_l)
        rule.evaluate(c_h, self._ctx())
        rule.evaluate(c_l, self._ctx())
        assert c_h.score > c_l.score

    def test_capability_rule_discards_missing(self):
        required = frozenset({BrokerCapability.OPTIONS})
        rule = make_capability_rule(required)
        cap  = _caps(caps=frozenset({BrokerCapability.EQUITY}))
        c    = self._candidate(cap)
        rule.evaluate(c, self._ctx())
        assert not c.is_eligible
        assert "OPTIONS" in c.discard_reason

    def test_capability_rule_awards_when_supported(self):
        required = frozenset({BrokerCapability.EQUITY})
        rule = make_capability_rule(required)
        cap  = _caps(caps=frozenset({BrokerCapability.EQUITY}))
        c    = self._candidate(cap)
        rule.evaluate(c, self._ctx())
        assert c.is_eligible
        assert c.score > 0

    def test_exchange_rule_discards_unsupported(self):
        rule = make_exchange_rule()
        cap  = _caps(exchanges=frozenset({"BSE"}))
        c    = RoutingCandidate(broker_id=cap.broker_id, exchange="NSE", capabilities=cap)
        ctx  = self._ctx(exchange="NSE")
        rule.evaluate(c, ctx)
        assert not c.is_eligible

    def test_exchange_rule_awards_match(self):
        rule = make_exchange_rule()
        cap  = _caps(exchanges=frozenset({"NSE"}))
        c    = self._candidate(cap)
        rule.evaluate(c, self._ctx(exchange="NSE"))
        assert c.is_eligible
        assert c.score > 0

    def test_order_type_rule_discards_unsupported(self):
        rule = make_order_type_rule()
        cap  = _caps(order_types=frozenset({"LIMIT"}))
        c    = self._candidate(cap)
        rule.evaluate(c, self._ctx(order_type="STOP"))
        assert not c.is_eligible

    def test_execution_mode_rule_discards_if_mode_missing(self):
        rule = make_execution_mode_rule()
        cap  = _caps(modes=frozenset({ExecutionMode.LIVE}))
        c    = self._candidate(cap)
        ctx  = RoutingContext(order_id="ORD-M", execution_mode=ExecutionMode.PAPER)
        rule.evaluate(c, ctx)
        assert not c.is_eligible

    def test_rule_skips_already_discarded(self):
        rule = make_availability_rule()
        cap  = _caps(available=True)
        c    = self._candidate(cap)
        c.discard("pre_discarded")
        rule.evaluate(c, self._ctx())
        assert not c.is_eligible  # still ineligible

    def test_inactive_rule_is_noop(self):
        rule = make_availability_rule()
        rule.is_active = False
        cap  = _caps(available=False)
        c    = self._candidate(cap)
        rule.evaluate(c, self._ctx())
        assert c.is_eligible  # rule was inactive, nothing changed

    def test_rule_to_dict_keys(self):
        rule = make_availability_rule()
        d = rule.to_dict()
        assert "rule_id" in d
        assert "is_hard" in d


# ─────────────────────────────────────────────────────────────────────────────
# TestRoutingPolicies
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingPolicies:
    def _candidate(self, cap: BrokerCapabilities) -> RoutingCandidate:
        return RoutingCandidate(broker_id=cap.broker_id, exchange="NSE", capabilities=cap)

    def _ctx(self, policy=RoutingPolicyType.DEFAULT, mode=ExecutionMode.LIVE):
        return RoutingContext(
            order_id="ORD-P", exchange="NSE", order_type="LIMIT",
            policy_type=policy, execution_mode=mode,
        )

    def test_default_policy_type(self):
        p = make_default_policy()
        assert p.policy_type == RoutingPolicyType.DEFAULT

    def test_priority_policy_type(self):
        p = make_priority_policy()
        assert p.policy_type == RoutingPolicyType.PRIORITY

    def test_capability_policy_type(self):
        p = make_capability_policy()
        assert p.policy_type == RoutingPolicyType.CAPABILITY

    def test_exchange_policy_type(self):
        p = make_exchange_policy()
        assert p.policy_type == RoutingPolicyType.EXCHANGE

    def test_paper_trading_policy_type(self):
        p = make_paper_trading_policy()
        assert p.policy_type == RoutingPolicyType.PAPER_TRADE

    def test_backtest_policy_type(self):
        p = make_backtest_policy()
        assert p.policy_type == RoutingPolicyType.BACKTEST

    def test_recovery_policy_type(self):
        p = make_recovery_policy()
        assert p.policy_type == RoutingPolicyType.RECOVERY

    def test_default_policy_selects_available_broker(self):
        policy = make_default_policy()
        cap    = _caps("BRK", available=True)
        c      = self._candidate(cap)
        policy.apply([c], self._ctx())
        assert c.is_eligible

    def test_default_policy_discards_unavailable(self):
        policy = make_default_policy()
        cap    = _caps("BRK", available=False)
        c      = self._candidate(cap)
        policy.apply([c], self._ctx())
        assert not c.is_eligible

    def test_priority_policy_higher_priority_wins(self):
        policy = make_priority_policy()
        cap_h  = _caps("H", priority=10)
        cap_l  = _caps("L", priority=1)
        ch, cl = self._candidate(cap_h), self._candidate(cap_l)
        policy.apply([ch, cl], self._ctx())
        assert ch.score > cl.score

    def test_paper_trading_policy_discards_live_only_broker(self):
        policy = make_paper_trading_policy()
        cap    = _caps(modes=frozenset({ExecutionMode.LIVE}))
        c      = self._candidate(cap)
        ctx    = self._ctx(mode=ExecutionMode.PAPER)
        policy.apply([c], ctx)
        assert not c.is_eligible

    def test_backtest_policy_discards_non_backtest_broker(self):
        policy = make_backtest_policy()
        cap    = _caps(modes=frozenset({ExecutionMode.LIVE}))
        c      = self._candidate(cap)
        ctx    = RoutingContext(order_id="ORD-BT", execution_mode=ExecutionMode.BACKTEST)
        policy.apply([c], ctx)
        assert not c.is_eligible

    def test_recovery_policy_accepts_any_available(self):
        policy = make_recovery_policy()
        cap    = _caps(available=True)
        c      = self._candidate(cap)
        policy.apply([c], self._ctx())
        assert c.is_eligible

    def test_inactive_policy_is_noop(self):
        policy = make_default_policy()
        policy.is_active = False
        cap = _caps(available=False)
        c   = self._candidate(cap)
        policy.apply([c], self._ctx())
        assert c.is_eligible  # policy did nothing

    def test_get_policy_returns_all_types(self):
        for pt in RoutingPolicyType:
            p = get_policy(pt)
            assert isinstance(p, RoutingPolicy)
            assert p.policy_type == pt

    def test_policy_to_dict_keys(self):
        p = make_default_policy()
        d = p.to_dict()
        assert "policy_type" in d
        assert "rules" in d

    def test_policy_eligible_filters(self):
        policy = make_default_policy()
        cap_ok = _caps("OK", available=True)
        cap_no = _caps("NO", available=False)
        candidates = [
            RoutingCandidate(broker_id="OK", exchange="NSE", capabilities=cap_ok),
            RoutingCandidate(broker_id="NO", exchange="NSE", capabilities=cap_no),
        ]
        policy.apply(candidates, self._ctx())
        eligible = policy.eligible(candidates)
        assert len(eligible) == 1
        assert eligible[0].broker_id == "OK"


# ─────────────────────────────────────────────────────────────────────────────
# TestRoutingStrategy
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingStrategy:
    def _ctx(self):
        return RoutingContext(order_id="ORD-S")

    def test_rank_empty_returns_empty(self):
        s = RoutingStrategy()
        assert s.rank([], self._ctx()) == []

    def test_rank_sorts_by_score_descending(self):
        s  = RoutingStrategy()
        c1 = RoutingCandidate(broker_id="A", exchange="NSE")
        c2 = RoutingCandidate(broker_id="B", exchange="NSE")
        c1.add_score(CandidateScoreField.PRIORITY, 10.0)
        c2.add_score(CandidateScoreField.PRIORITY, 5.0)
        ranked = s.rank([c2, c1], self._ctx())
        assert ranked[0].broker_id == "A"

    def test_rank_tiebreak_by_priority(self):
        s    = RoutingStrategy()
        cap_h = _caps("H", priority=5)
        cap_l = _caps("L", priority=1)
        c1 = RoutingCandidate(broker_id="H", exchange="NSE", capabilities=cap_h)
        c2 = RoutingCandidate(broker_id="L", exchange="NSE", capabilities=cap_l)
        c1.add_score(CandidateScoreField.AVAILABILITY, 10.0)
        c2.add_score(CandidateScoreField.AVAILABILITY, 10.0)
        ranked = s.rank([c2, c1], self._ctx())
        assert ranked[0].broker_id == "H"

    def test_rank_excludes_ineligible(self):
        s  = RoutingStrategy()
        c1 = RoutingCandidate(broker_id="A", exchange="NSE")
        c2 = RoutingCandidate(broker_id="B", exchange="NSE")
        c1.discard("bad")
        ranked = s.rank([c1, c2], self._ctx())
        assert all(c.is_eligible for c in ranked)
        assert len(ranked) == 1

    def test_select_returns_best(self):
        s  = RoutingStrategy()
        c1 = RoutingCandidate(broker_id="A", exchange="NSE")
        c2 = RoutingCandidate(broker_id="B", exchange="NSE")
        c1.add_score(CandidateScoreField.PRIORITY, 20.0)
        c2.add_score(CandidateScoreField.PRIORITY, 5.0)
        best = s.select([c1, c2], self._ctx())
        assert best.broker_id == "A"

    def test_select_raises_when_no_eligible(self):
        s = RoutingStrategy()
        c = RoutingCandidate(broker_id="A", exchange="NSE")
        c.discard("bad")
        with pytest.raises(NoCandidatesError):
            s.select([c], self._ctx())

    def test_select_raises_on_empty_list(self):
        s = RoutingStrategy()
        with pytest.raises(NoCandidatesError):
            s.select([], self._ctx())

    def test_to_dict(self):
        d = RoutingStrategy().to_dict()
        assert "strategy_id" in d


# ─────────────────────────────────────────────────────────────────────────────
# TestRoutingDecision
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingDecision:
    def test_is_frozen(self):
        d = RoutingDecision(order_id="ORD-1", succeeded=True)
        with pytest.raises((AttributeError, TypeError)):
            d.succeeded = False  # type: ignore[misc]

    def test_defaults(self):
        d = RoutingDecision()
        assert not d.succeeded
        assert d.selected_broker_id == ""
        assert d.rejection_reason == ""

    def test_success_decision(self):
        d = RoutingDecision(
            order_id="ORD-1",
            selected_broker_id="BRK",
            selected_exchange="NSE",
            succeeded=True,
            score=15.0,
        )
        assert d.succeeded
        assert d.selected_broker_id == "BRK"

    def test_to_dict_contains_required_keys(self):
        d = RoutingDecision(order_id="ORD-1", succeeded=True)
        dd = d.to_dict()
        for k in ("decision_id", "order_id", "succeeded", "score",
                  "routing_time_ms", "candidates_evaluated"):
            assert k in dd


# ─────────────────────────────────────────────────────────────────────────────
# TestRoutingResult
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingResult:
    def _success_result(self) -> RoutingResult:
        dec = RoutingDecision(
            order_id="ORD-1", selected_broker_id="BRK",
            selected_exchange="NSE", succeeded=True,
        )
        c_ok = RoutingCandidate(broker_id="BRK", exchange="NSE")
        c_bad = RoutingCandidate(broker_id="BAD", exchange="NSE")
        c_bad.discard("bad")
        return RoutingResult(
            decision=dec, request_id="REQ-1", order_id="ORD-1",
            policy_type="DEFAULT", elapsed_ms=1.5,
            candidates=(c_ok, c_bad),
        )

    def test_succeeded_delegates_to_decision(self):
        r = self._success_result()
        assert r.succeeded

    def test_selected_broker_id_property(self):
        r = self._success_result()
        assert r.selected_broker_id == "BRK"

    def test_eligible_candidates(self):
        r = self._success_result()
        assert len(r.eligible_candidates()) == 1

    def test_discarded_candidates(self):
        r = self._success_result()
        assert len(r.discarded_candidates()) == 1

    def test_to_dict_keys(self):
        r = self._success_result()
        d = r.to_dict()
        for k in ("result_id", "order_id", "succeeded", "candidates"):
            assert k in d


# ─────────────────────────────────────────────────────────────────────────────
# TestRoutingEvents
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingEvents:
    def test_routing_started(self):
        e = make_routing_started("ORD-1", "REQ-1", "DEFAULT")
        assert e.event_type == RoutingEventType.ROUTING_STARTED
        assert e.order_id   == "ORD-1"
        assert "DEFAULT" in str(e.metadata)

    def test_candidate_evaluated(self):
        e = make_candidate_evaluated("ORD-1", "REQ-1", "BRK", 5.0, True, "")
        assert e.event_type == RoutingEventType.CANDIDATE_EVALUATED
        assert e.metadata["broker_id"] == "BRK"

    def test_route_selected(self):
        e = make_route_selected("ORD-1", "REQ-1", "DEC-1", "BRK", "NSE", 10.0)
        assert e.event_type == RoutingEventType.ROUTE_SELECTED
        assert e.metadata["exchange"] == "NSE"

    def test_routing_rejected(self):
        e = make_routing_rejected("ORD-1", "REQ-1", "no_candidates")
        assert e.event_type == RoutingEventType.ROUTING_REJECTED
        assert e.metadata["reason"] == "no_candidates"

    def test_routing_completed_success(self):
        e = make_routing_completed("ORD-1", "REQ-1", True, 2.5, 3)
        assert e.event_type == RoutingEventType.ROUTING_COMPLETED
        assert e.metadata["succeeded"] is True

    def test_routing_completed_failure(self):
        e = make_routing_completed("ORD-1", "REQ-1", False, 1.0, 0)
        assert e.metadata["succeeded"] is False

    def test_events_are_frozen(self):
        e = make_routing_started("ORD-1", "REQ-1")
        with pytest.raises((AttributeError, TypeError)):
            e.order_id = "CHANGED"  # type: ignore[misc]

    def test_event_to_dict_keys(self):
        e = make_routing_started("ORD-1", "REQ-1")
        d = e.to_dict()
        assert "event_id" in d
        assert "event_type" in d

    def test_each_event_has_unique_id(self):
        ids = {
            make_routing_started("ORD-1", "REQ-1").event_id,
            make_routing_started("ORD-1", "REQ-1").event_id,
        }
        assert len(ids) == 2


# ─────────────────────────────────────────────────────────────────────────────
# TestRoutingStatistics
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingStatistics:
    def test_initial_zeros(self):
        s = RoutingStatistics()
        assert s.total_requests == 0
        assert s.successful == 0
        assert s.rejected == 0
        assert s.avg_routing_time_ms == 0.0

    def test_record_request_increments(self):
        s = RoutingStatistics()
        s.record_request()
        s.record_request()
        assert s.total_requests == 2

    def test_record_success(self):
        s = RoutingStatistics()
        s.record_success(5.0, policy="DEFAULT", broker_id="BRK")
        assert s.successful == 1
        assert s.avg_routing_time_ms == pytest.approx(5.0)
        assert s.policy_usage() == {"DEFAULT": 1}
        assert s.broker_distribution() == {"BRK": 1}

    def test_record_rejection(self):
        s = RoutingStatistics()
        s.record_rejection(3.0)
        assert s.rejected == 1

    def test_record_failure(self):
        s = RoutingStatistics()
        s.record_failure()
        assert s.failed == 1

    def test_record_expiry(self):
        s = RoutingStatistics()
        s.record_expiry()
        assert s.expired == 1

    def test_min_max_time(self):
        s = RoutingStatistics()
        s.record_success(10.0, policy="P")
        s.record_success(2.0, policy="P")
        s.record_success(5.0, policy="P")
        assert s.min_routing_time_ms == pytest.approx(2.0)
        assert s.max_routing_time_ms == pytest.approx(10.0)

    def test_reset_clears_all(self):
        s = RoutingStatistics()
        s.record_request()
        s.record_success(1.0, policy="P", broker_id="B")
        s.reset()
        assert s.total_requests == 0
        assert s.successful == 0
        assert s.policy_usage() == {}

    def test_to_dict_keys(self):
        d = RoutingStatistics().to_dict()
        for k in ("total_requests", "successful", "rejected",
                  "avg_routing_time_ms", "policy_usage", "broker_distribution"):
            assert k in d

    def test_thread_safe_concurrent_increments(self):
        s = RoutingStatistics()
        threads = [threading.Thread(target=s.record_request) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert s.total_requests == 100


# ─────────────────────────────────────────────────────────────────────────────
# TestRoutingHistory
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingHistory:
    def _result(self, order_id: str = "ORD-H", succeeded: bool = True) -> RoutingResult:
        dec = RoutingDecision(
            order_id=order_id, succeeded=succeeded,
            selected_broker_id="BRK" if succeeded else "",
        )
        return RoutingResult(decision=dec, order_id=order_id)

    def test_initial_empty(self):
        h = RoutingHistory(max_size=10)
        assert h.size == 0
        assert h.total == 0

    def test_append_increments_size(self):
        h = RoutingHistory(max_size=10)
        h.append(self._result())
        assert h.size == 1
        assert h.total == 1

    def test_bounded_eviction(self):
        h = RoutingHistory(max_size=3)
        for i in range(5):
            h.append(self._result(f"ORD-{i}"))
        assert h.size == 3
        assert h.total == 5
        assert h.evicted == 2

    def test_latest_returns_last_n(self):
        h = RoutingHistory(max_size=10)
        for i in range(5):
            h.append(self._result(f"ORD-{i}"))
        last = h.latest(3)
        assert len(last) == 3

    def test_for_order_filters(self):
        h = RoutingHistory(max_size=10)
        h.append(self._result("ORD-A"))
        h.append(self._result("ORD-B"))
        h.append(self._result("ORD-A"))
        assert len(h.for_order("ORD-A")) == 2
        assert len(h.for_order("ORD-B")) == 1

    def test_successful_filter(self):
        h = RoutingHistory(max_size=10)
        h.append(self._result("A", succeeded=True))
        h.append(self._result("B", succeeded=False))
        assert len(h.successful()) == 1
        assert len(h.rejected()) == 1

    def test_for_broker_filters(self):
        h = RoutingHistory(max_size=10)
        h.append(self._result("A", succeeded=True))  # BRK
        dec2 = RoutingDecision(order_id="B", succeeded=True, selected_broker_id="OTHER")
        h.append(RoutingResult(decision=dec2, order_id="B"))
        assert len(h.for_broker("BRK")) == 1
        assert len(h.for_broker("OTHER")) == 1

    def test_len_dunder(self):
        h = RoutingHistory(max_size=10)
        h.append(self._result())
        assert len(h) == 1

    def test_iter(self):
        h = RoutingHistory(max_size=10)
        h.append(self._result("A"))
        h.append(self._result("B"))
        ids = [r.order_id for r in h]
        assert "A" in ids
        assert "B" in ids

    def test_clear(self):
        h = RoutingHistory(max_size=10)
        h.append(self._result())
        h.clear()
        assert h.size == 0

    def test_invalid_max_size_raises(self):
        with pytest.raises(ValueError):
            RoutingHistory(max_size=0)

    def test_to_dict_keys(self):
        d = RoutingHistory().to_dict()
        assert "max_size" in d
        assert "total" in d

    def test_concurrent_appends(self):
        h = RoutingHistory(max_size=200)
        def _append(i):
            h.append(self._result(f"ORD-{i}"))
        threads = [threading.Thread(target=_append, args=(i,)) for i in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert h.total == 100


# ─────────────────────────────────────────────────────────────────────────────
# TestRoutingValidator
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingValidator:
    def test_valid_request_passes(self):
        v = RoutingValidator()
        v.validate(_request())  # must not raise

    def test_missing_order_id_raises(self):
        v = RoutingValidator()
        req = _request()
        req.order_id = ""
        with pytest.raises(RoutingValidationError) as exc:
            v.validate(req)
        assert "MISSING_ORDER_ID" in str(exc.value.errors)

    def test_whitespace_order_id_raises(self):
        v = RoutingValidator()
        req = _request()
        req.order_id = "   "
        with pytest.raises(RoutingValidationError):
            v.validate(req)

    def test_expired_request_raises(self):
        v = RoutingValidator()
        req = _request(ttl=0.001)
        time.sleep(0.005)
        with pytest.raises(RoutingValidationError) as exc:
            v.validate(req)
        assert "REQUEST_EXPIRED" in str(exc.value.errors)

    def test_validate_capabilities_empty_exchanges_passes(self):
        v = RoutingValidator()
        cap = _caps(exchanges=frozenset())
        errors = v.validate_capabilities(cap, _request(exchange="NSE"))
        assert errors == []

    def test_validate_capabilities_exchange_mismatch(self):
        v = RoutingValidator()
        cap = _caps(exchanges=frozenset({"BSE"}))
        req = _request(exchange="NSE")
        errors = v.validate_capabilities(cap, req)
        assert RoutingValidationCode.EXCHANGE_UNSUPPORTED.value in errors

    def test_validate_capabilities_unavailable_broker(self):
        v = RoutingValidator()
        cap = _caps(available=False)
        errors = v.validate_capabilities(cap, _request())
        assert RoutingValidationCode.BROKER_UNAVAILABLE.value in errors

    def test_validate_broker_available_true(self):
        v = RoutingValidator()
        assert v.validate_broker_available(_caps(available=True))

    def test_validate_broker_available_false(self):
        v = RoutingValidator()
        assert not v.validate_broker_available(_caps(available=False))

    def test_validate_exchange_supported(self):
        v   = RoutingValidator()
        cap = _caps(exchanges=frozenset({"NSE"}))
        assert v.validate_exchange_supported(cap, "NSE")
        assert not v.validate_exchange_supported(cap, "MCX")

    def test_validate_order_type_compatible(self):
        v   = RoutingValidator()
        cap = _caps(order_types=frozenset({"LIMIT"}))
        assert v.validate_order_type_compatible(cap, "LIMIT")
        assert not v.validate_order_type_compatible(cap, "MARKET")

    def test_validate_execution_mode(self):
        v   = RoutingValidator()
        cap = _caps(modes=frozenset({ExecutionMode.LIVE}))
        assert v.validate_execution_mode(cap, ExecutionMode.LIVE)
        assert not v.validate_execution_mode(cap, ExecutionMode.PAPER)


# ─────────────────────────────────────────────────────────────────────────────
# TestRoutingRegistry
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingRegistry:
    def test_start_stop_lifecycle(self):
        r = RoutingRegistry()
        r.start()
        assert r.lifecycle_state().value == "running"
        r.stop()
        assert r.lifecycle_state().value != "running"

    def test_register_and_get(self, registry):
        cap = _caps("MY_BRK")
        registry.register(cap)
        assert registry.get("MY_BRK") is cap

    def test_register_overwrites(self, registry):
        cap1 = _caps("BRK", available=True)
        cap2 = _caps("BRK", available=False)
        registry.register(cap1)
        registry.register(cap2)
        assert registry.get("BRK").is_available is False

    def test_unregister(self, registry):
        registry.register(_caps("DEL_BRK"))
        removed = registry.unregister("DEL_BRK")
        assert removed
        assert registry.get("DEL_BRK") is None

    def test_unregister_missing_returns_false(self, registry):
        assert not registry.unregister("GHOST")

    def test_all_returns_all(self, registry):
        registry.register(_caps("A"))
        registry.register(_caps("B"))
        ids = {b.broker_id for b in registry.all()}
        assert "A" in ids
        assert "B" in ids

    def test_available_filters_unavailable(self, registry):
        registry.register(_caps("OK", available=True))
        registry.register(_caps("BAD", available=False))
        avail = registry.available()
        avail_ids = {b.broker_id for b in avail}
        assert "OK" in avail_ids
        assert "BAD" not in avail_ids

    def test_contains(self, registry):
        registry.register(_caps("YES"))
        assert registry.contains("YES")
        assert not registry.contains("NO")

    def test_capacity_raises(self):
        r = RoutingRegistry(max_brokers=2)
        r.start()
        r.register(_caps("A"))
        r.register(_caps("B"))
        with pytest.raises(RouterCapacityError):
            r.register(_caps("C"))
        r.stop()

    def test_empty_broker_id_raises(self, registry):
        with pytest.raises(ValueError):
            registry.register(_caps(broker_id=""))

    def test_operations_require_running(self):
        r = RoutingRegistry()
        cap = _caps("X")
        with pytest.raises(RouterNotRunning):
            r.register(cap)
        with pytest.raises(RouterNotRunning):
            r.get("X")

    def test_to_dict(self, registry):
        registry.register(_caps("Z"))
        d = registry.to_dict()
        assert "Z" in d["broker_ids"]


# ─────────────────────────────────────────────────────────────────────────────
# TestRoutingFactory
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingFactory:
    def test_make_success_decision(self):
        f = RoutingFactory()
        d = f.make_success_decision(
            order_id="ORD-1", broker_id="BRK", exchange="NSE",
            policy_applied="DEFAULT", score=15.0, candidates_total=3,
            routing_time_ms=2.5, request_id="REQ-1",
        )
        assert d.succeeded
        assert d.selected_broker_id == "BRK"
        assert d.selected_exchange  == "NSE"
        assert d.score == pytest.approx(15.0)

    def test_make_rejected_decision(self):
        f = RoutingFactory()
        d = f.make_rejected_decision(
            order_id="ORD-1", reason="no_candidates", policy_applied="DEFAULT",
            candidates_total=0, routing_time_ms=1.0, request_id="REQ-1",
        )
        assert not d.succeeded
        assert d.rejection_reason == "no_candidates"
        assert d.selected_broker_id == ""

    def test_make_result(self):
        f   = RoutingFactory()
        dec = RoutingDecision(order_id="ORD-1", succeeded=True)
        c   = RoutingCandidate(broker_id="BRK", exchange="NSE")
        r   = f.make_result(
            decision=dec, request_id="REQ-1", order_id="ORD-1",
            policy_type="DEFAULT", elapsed_ms=2.0, candidates=[c],
        )
        assert r.order_id == "ORD-1"
        assert len(r.candidates) == 1


# ─────────────────────────────────────────────────────────────────────────────
# TestOrderRouter
# ─────────────────────────────────────────────────────────────────────────────

class TestOrderRouter:
    def test_requires_start(self):
        r = OrderRouter()
        with pytest.raises(RouterNotRunning):
            r.route(_request())

    def test_start_starts_registry_too(self):
        from iios.investment.workflow.engine_lifecycle import EngineState
        r = OrderRouter()
        r.start()
        assert r.lifecycle_state() == EngineState.RUNNING
        r.stop()

    def test_route_success(self, router, broker_a):
        router.register_broker(broker_a)
        req = _request(order_id="ORD-R1", caps=[broker_a])
        dec = router.route(req)
        assert dec.succeeded
        assert dec.selected_broker_id == "BROKER_A"

    def test_route_rejected_when_no_candidates(self, router):
        req = _request(order_id="ORD-NO")
        dec = router.route(req)
        assert not dec.succeeded
        assert dec.rejection_reason == "no_eligible_candidates"

    def test_route_rejected_when_unavailable(self, router):
        cap = _caps("GONE", available=False)
        router.register_broker(cap)
        req = _request(caps=[cap])
        dec = router.route(req)
        assert not dec.succeeded

    def test_route_exchange_mismatch_rejected(self, router):
        cap = _caps("BRK", exchanges=frozenset({"BSE"}))
        req = _request(exchange="NSE", caps=[cap])
        dec = router.route(req)
        assert not dec.succeeded

    def test_route_invalid_order_id_raises(self, router):
        req = _request()
        req.order_id = ""
        with pytest.raises(RoutingValidationError):
            router.route(req)

    def test_route_expired_request_raises(self, router, broker_a):
        router.register_broker(broker_a)
        req = _request(ttl=0.001)
        time.sleep(0.005)
        with pytest.raises((RoutingValidationError, RoutingExpiredError)):
            router.route(req)

    def test_register_and_unregister_broker(self, router, broker_a):
        router.register_broker(broker_a)
        assert router.get_broker("BROKER_A") is not None
        removed = router.unregister_broker("BROKER_A")
        assert removed
        assert router.get_broker("BROKER_A") is None

    def test_list_brokers(self, router, broker_a, broker_b):
        router.register_broker(broker_a)
        router.register_broker(broker_b)
        ids = {b.broker_id for b in router.list_brokers()}
        assert "BROKER_A" in ids
        assert "BROKER_B" in ids

    def test_events_emitted_on_success(self, router, broker_a):
        router.clear_events()
        router.register_broker(broker_a)
        router.route(_request(caps=[broker_a]))
        ev_types = [e.event_type for e in router.events()]
        assert RoutingEventType.ROUTING_STARTED   in ev_types
        assert RoutingEventType.ROUTING_COMPLETED in ev_types
        assert RoutingEventType.ROUTE_SELECTED    in ev_types

    def test_events_emitted_on_rejection(self, router):
        router.clear_events()
        router.route(_request(order_id="ORD-REJ"))
        ev_types = [e.event_type for e in router.events()]
        assert RoutingEventType.ROUTING_REJECTED  in ev_types
        assert RoutingEventType.ROUTING_COMPLETED in ev_types

    def test_statistics_updated_on_success(self, router, broker_a):
        router.register_broker(broker_a)
        router.route(_request(caps=[broker_a]))
        s = router.statistics()
        assert s.successful >= 1

    def test_statistics_updated_on_rejection(self, router):
        router.route(_request(order_id="ORD-STAT"))
        s = router.statistics()
        assert s.rejected >= 1

    def test_history_updated_after_route(self, router, broker_a):
        router.register_broker(broker_a)
        req = _request(caps=[broker_a])
        router.route(req)
        assert router.history().total >= 1

    def test_priority_policy_picks_higher_priority(self, router):
        cap_h = _caps("BRK_H", priority=10)
        cap_l = _caps("BRK_L", priority=1)
        router.register_broker(cap_h)
        router.register_broker(cap_l)
        req = _request(policy=RoutingPolicyType.PRIORITY, caps=[cap_h, cap_l])
        dec = router.route(req)
        assert dec.succeeded
        assert dec.selected_broker_id == "BRK_H"

    def test_paper_trading_policy(self, router):
        cap_paper = _caps(
            "PAPER_BRK",
            modes=frozenset({ExecutionMode.PAPER, ExecutionMode.LIVE}),
        )
        cap_live = _caps(
            "LIVE_ONLY",
            modes=frozenset({ExecutionMode.LIVE}),
        )
        req = _request(
            policy=RoutingPolicyType.PAPER_TRADE,
            mode=ExecutionMode.PAPER,
            caps=[cap_paper, cap_live],
        )
        dec = router.route(req)
        assert dec.succeeded
        assert dec.selected_broker_id == "PAPER_BRK"

    def test_backtest_policy(self, router):
        cap_bt = _caps(
            "BT_BRK",
            modes=frozenset({ExecutionMode.BACKTEST}),
        )
        req = _request(
            policy=RoutingPolicyType.BACKTEST,
            mode=ExecutionMode.BACKTEST,
            caps=[cap_bt],
        )
        dec = router.route(req)
        assert dec.succeeded
        assert dec.selected_broker_id == "BT_BRK"

    def test_recovery_policy(self, router, broker_a):
        req = _request(policy=RoutingPolicyType.RECOVERY, caps=[broker_a])
        dec = router.route(req)
        assert dec.succeeded

    def test_snapshot_keys(self, router):
        d = router.snapshot()
        assert "system_id" in d
        assert "statistics" in d
        assert "history" in d
        assert "registry" in d

    def test_clear_events(self, router, broker_a):
        router.register_broker(broker_a)
        router.route(_request(caps=[broker_a]))
        router.clear_events()
        assert router.events() == []

    def test_route_uses_registry_when_no_caps_in_request(self, router, broker_a):
        router.register_broker(broker_a)
        req = _request()  # no broker_capabilities in request
        dec = router.route(req)
        assert dec.succeeded
        assert dec.selected_broker_id == "BROKER_A"

    def test_route_uses_candidate_broker_ids_filter(self, router, broker_a, broker_b):
        router.register_broker(broker_a)
        router.register_broker(broker_b)
        req = _request(exchange="NSE")
        req.candidate_broker_ids = ["BROKER_A"]
        dec = router.route(req)
        assert dec.succeeded
        assert dec.selected_broker_id == "BROKER_A"


# ─────────────────────────────────────────────────────────────────────────────
# TestOrderRouterConcurrency
# ─────────────────────────────────────────────────────────────────────────────

class TestOrderRouterConcurrency:
    def test_concurrent_route_100_threads(self, router, broker_a):
        """100 threads each route one order — no exceptions, counts match."""
        router.register_broker(broker_a)
        errors:   list[Exception] = []
        results:  list[RoutingDecision] = []
        lock = threading.Lock()

        def _route():
            try:
                dec = router.route(_request(caps=[broker_a]))
                with lock:
                    results.append(dec)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=_route) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Unexpected errors: {errors}"
        assert len(results) == 100
        assert all(r.succeeded for r in results)

    def test_concurrent_registry_operations(self, router):
        """50 threads register + route simultaneously."""
        errors: list[Exception] = []
        lock = threading.Lock()

        def _work(i: int):
            try:
                cap = _caps(f"BRK_{i}", priority=i)
                router.register_broker(cap)
                dec = router.route(_request(caps=[cap]))
                assert dec.succeeded
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=_work, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Unexpected errors: {errors}"

    def test_statistics_correct_under_concurrency(self, router, broker_a):
        router.register_broker(broker_a)
        n = 50

        def _route():
            router.route(_request(caps=[broker_a]))

        threads = [threading.Thread(target=_route) for _ in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        stats = router.statistics()
        assert stats.successful == n

    def test_history_size_bounded_under_concurrency(self):
        r = OrderRouter(max_history=20)
        r.start()
        cap = _caps("BRK")
        r.register_broker(cap)

        def _route():
            r.route(_request(caps=[cap]))

        threads = [threading.Thread(target=_route) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert r.history().size <= 20
        r.stop()
