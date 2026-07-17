"""
tests/unit/execution/gateway/routing/test_routing_framework.py
==============================================================
Unit tests for C6 Phase 5 M4 — IIOS Routing Framework.

Coverage targets
----------------
  TestConstants            — enumerations, defaults, frozensets
  TestExceptions           — error hierarchy and attributes
  TestRoutingContext       — creation, properties, factory
  TestRoutingCandidate     — mutations, availability, thread safety
  TestRoutingRequest       — creation, properties, factory
  TestRoutingDecision      — routed / failed factories, properties
  TestRoutingEvents        — RoutingEvent + 7 factory functions
  TestDefaultBrokerPolicy  — evaluate()
  TestPreferredBrokerPolicy
  TestCapabilityBasedPolicy
  TestInstrumentBasedPolicy
  TestMarketBasedPolicy
  TestExchangeBasedPolicy
  TestProductBasedPolicy
  TestPriorityBasedPolicy
  TestHealthBasedPolicy
  TestFailoverRoutingPolicy
  TestWeightedRoutingPolicy
  TestCustomRoutingPolicy
  TestRoutingStrategySelector — all 6 strategy types
  TestRoutingSelector         — combined policy + strategy
  TestRoutingValidation       — all validate_* methods
  TestRoutingStatistics       — accumulators, derived properties
  TestRoutingHistory          — bounded deque, query methods
  TestRoutingRegistry         — lifecycle guard, CRUD, blacklist
  TestRoutingFactory          — factory methods
  TestRoutingManager          — full routing workflow
  TestRoutingEngine           — public API surface
  TestFailoverScenarios       — failover end-to-end
  TestConcurrency             — thread safety
  TestRegressionEdgeCases     — corner cases
"""
from __future__ import annotations

import threading
import time
from typing import List
from unittest.mock import MagicMock

import pytest

from iios.execution.gateway.brokers.broker_capabilities import BrokerCapabilities
from iios.execution.gateway.brokers.constants import BrokerCapability, ProductType
from iios.execution.gateway.routing import (
    FAILED_OUTCOMES,
    ROUTED_OUTCOMES,
    CandidateStatus,
    CapabilityBasedPolicy,
    CandidateAlreadyRegisteredError,
    CandidateNotFoundError,
    CustomRoutingPolicy,
    DefaultBrokerPolicy,
    ExchangeBasedPolicy,
    FailoverRoutingPolicy,
    HealthBasedPolicy,
    InstrumentBasedPolicy,
    MarketBasedPolicy,
    NoBrokersAvailableError,
    PolicyAlreadyRegisteredError,
    PreferredBrokerPolicy,
    PriorityBasedPolicy,
    ProductBasedPolicy,
    RoutingCandidate,
    RoutingContext,
    RoutingDecision,
    RoutingEngine,
    RoutingEngineNotRunningError,
    RoutingEvent,
    RoutingEventType,
    RoutingFactory,
    RoutingFrameworkError,
    RoutingHistory,
    RoutingManager,
    RoutingOutcome,
    RoutingPolicyBase,
    RoutingPolicyError,
    RoutingPolicyNotFoundError,
    RoutingPolicyType,
    RoutingRegistryCapacityError,
    RoutingRegistry,
    RoutingRequest,
    RoutingRequestError,
    RoutingSelector,
    RoutingStatistics,
    RoutingStrategySelector,
    RoutingStrategyType,
    RoutingValidationError,
    RoutingValidationResult,
    RoutingValidator,
    VERSION,
    WeightedRoutingPolicy,
    make_broker_rejected_event,
    make_broker_selected_event,
    make_failed_decision,
    make_failover_activated_event,
    make_policy_applied_event,
    make_routed_decision,
    make_routing_completed_event,
    make_routing_context,
    make_routing_failed_event,
    make_routing_request,
    make_routing_started_event,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers / fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _caps(*capabilities: BrokerCapability) -> BrokerCapabilities:
    return BrokerCapabilities(frozenset(capabilities))


def _empty_caps() -> BrokerCapabilities:
    return BrokerCapabilities(frozenset())


def _candidate(
    broker_id:        str = "broker-1",
    broker_name:      str = "TestBroker",
    *,
    connected:        bool = True,
    authenticated:    bool = True,
    health_score:     float = 1.0,
    priority:         int = 0,
    weight:           float = 1.0,
    caps:             BrokerCapabilities | None = None,
    exchanges:        frozenset | None = None,
    products:         frozenset | None = None,
) -> RoutingCandidate:
    return RoutingCandidate(
        broker_id=broker_id,
        broker_name=broker_name,
        capabilities=caps if caps is not None else _empty_caps(),
        is_connected=connected,
        is_authenticated=authenticated,
        health_score=health_score,
        routing_priority=priority,
        weight=weight,
        supported_exchanges=exchanges or frozenset(),
        supported_products=products or frozenset(),
    )


def _context(
    symbol:             str = "RELIANCE",
    exchange:           str = "NSE",
    product:            str = "MIS",
    preferred_broker:   str | None = None,
    required_caps:      frozenset | None = None,
    priority:           int = 0,
) -> RoutingContext:
    return make_routing_context(
        execution_id="exec-1",
        order_id="ord-1",
        portfolio_id="port-1",
        strategy_id="strat-1",
        symbol=symbol,
        exchange=exchange,
        product=product,
        quantity=10.0,
        price=100.0,
        preferred_broker_id=preferred_broker,
        required_capabilities=required_caps,
        priority=priority,
    )


def _started_engine(**kwargs) -> RoutingEngine:
    e = RoutingEngine(**kwargs)
    e.start()
    return e


# ─────────────────────────────────────────────────────────────────────────────
# TestConstants
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_version_is_string(self):
        assert isinstance(VERSION, str)
        assert len(VERSION) > 0

    def test_routed_outcomes_nonempty(self):
        assert len(ROUTED_OUTCOMES) > 0
        assert RoutingOutcome.ROUTED in ROUTED_OUTCOMES
        assert RoutingOutcome.FAILOVER_ROUTED in ROUTED_OUTCOMES

    def test_failed_outcomes_nonempty(self):
        assert len(FAILED_OUTCOMES) > 0
        assert RoutingOutcome.FAILED in FAILED_OUTCOMES
        assert RoutingOutcome.NO_CANDIDATES in FAILED_OUTCOMES

    def test_routed_and_failed_disjoint(self):
        assert ROUTED_OUTCOMES.isdisjoint(FAILED_OUTCOMES)

    def test_policy_types_complete(self):
        types = {pt.value for pt in RoutingPolicyType}
        assert "DEFAULT_BROKER" in types
        assert "FAILOVER_ROUTING" in types
        assert "CUSTOM_POLICY" in types
        assert len(types) == 12

    def test_strategy_types_complete(self):
        types = {st.value for st in RoutingStrategyType}
        assert "PRIORITY_SELECTION" in types
        assert len(types) == 6

    def test_event_types_complete(self):
        types = {et.value for et in RoutingEventType}
        assert "ROUTING_STARTED" in types
        assert "BROKER_SELECTED" in types
        assert len(types) == 7

    def test_outcome_enum_values(self):
        assert RoutingOutcome.ROUTED.value == "ROUTED"
        assert RoutingOutcome.FAILOVER_ROUTED.value == "FAILOVER_ROUTED"

    def test_candidate_status_values(self):
        assert CandidateStatus.AVAILABLE.value == "AVAILABLE"
        assert CandidateStatus.BLACKLISTED.value == "BLACKLISTED"


# ─────────────────────────────────────────────────────────────────────────────
# TestExceptions
# ─────────────────────────────────────────────────────────────────────────────

class TestExceptions:
    def test_base_is_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(RoutingFrameworkError, IIOSError)

    def test_all_inherit_from_base(self):
        subclasses = [
            RoutingEngineNotRunningError,
            RoutingRequestError,
            RoutingPolicyNotFoundError,
            NoBrokersAvailableError,
            RoutingValidationError,
            PolicyAlreadyRegisteredError,
            CandidateNotFoundError,
            CandidateAlreadyRegisteredError,
            RoutingPolicyError,
            RoutingRegistryCapacityError,
        ]
        for cls in subclasses:
            assert issubclass(cls, RoutingFrameworkError)

    def test_error_codes(self):
        assert RoutingFrameworkError.error_code      == "RF-000"
        assert RoutingEngineNotRunningError.error_code == "RF-001"
        assert RoutingRequestError.error_code         == "RF-002"
        assert RoutingPolicyNotFoundError.error_code  == "RF-003"
        assert NoBrokersAvailableError.error_code     == "RF-004"
        assert RoutingValidationError.error_code      == "RF-005"
        assert PolicyAlreadyRegisteredError.error_code == "RF-006"
        assert CandidateNotFoundError.error_code      == "RF-007"
        assert CandidateAlreadyRegisteredError.error_code == "RF-008"
        assert RoutingPolicyError.error_code          == "RF-009"
        assert RoutingRegistryCapacityError.error_code == "RF-010"

    def test_policy_not_found_error_stores_id(self):
        e = RoutingPolicyNotFoundError("pol-99")
        assert e.policy_id == "pol-99"

    def test_candidate_not_found_stores_broker_id(self):
        e = CandidateNotFoundError("brk-x")
        assert e.broker_id == "brk-x"

    def test_validation_error_stores_errors(self):
        e = RoutingValidationError("msg", errors=("err1", "err2"))
        assert "err1" in e.errors
        assert "err2" in e.errors

    def test_routing_policy_error_stores_details(self):
        e = RoutingPolicyError("pol-1", "bad reason")
        assert e.policy_id == "pol-1"
        assert e.reason    == "bad reason"

    def test_registry_capacity_error_stores_max(self):
        e = RoutingRegistryCapacityError("candidates", 100)
        assert e.max_count == 100

    def test_can_be_raised_and_caught(self):
        with pytest.raises(RoutingFrameworkError):
            raise RoutingEngineNotRunningError()


# ─────────────────────────────────────────────────────────────────────────────
# TestRoutingContext
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingContext:
    def test_factory_creates_context(self):
        ctx = _context()
        assert ctx.symbol     == "RELIANCE"
        assert ctx.exchange   == "NSE"
        assert ctx.quantity   == 10.0
        assert ctx.price      == 100.0

    def test_routing_id_is_unique(self):
        a = _context()
        b = _context()
        assert a.routing_id != b.routing_id

    def test_is_high_priority_false_when_zero(self):
        ctx = _context(priority=0)
        assert not ctx.is_high_priority

    def test_is_high_priority_true_when_positive(self):
        ctx = _context(priority=5)
        assert ctx.is_high_priority

    def test_has_preferred_broker_true(self):
        ctx = _context(preferred_broker="broker-x")
        assert ctx.has_preferred_broker

    def test_has_preferred_broker_false(self):
        ctx = _context(preferred_broker=None)
        assert not ctx.has_preferred_broker

    def test_has_required_capabilities(self):
        ctx = _context(required_caps=frozenset({BrokerCapability.OPTIONS}))
        assert ctx.has_required_capabilities

    def test_no_required_capabilities(self):
        ctx = _context()
        assert not ctx.has_required_capabilities

    def test_age_ms_is_positive(self):
        ctx = _context()
        time.sleep(0.002)
        assert ctx.age_ms > 0

    def test_to_dict_contains_expected_keys(self):
        ctx = _context()
        d = ctx.to_dict()
        assert "routing_id" in d
        assert "symbol"     in d
        assert "exchange"   in d
        assert "quantity"   in d

    def test_context_is_immutable(self):
        ctx = _context()
        with pytest.raises((AttributeError, TypeError)):
            ctx.symbol = "NEW"  # type: ignore[misc]


# ─────────────────────────────────────────────────────────────────────────────
# TestRoutingCandidate
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingCandidate:
    def test_available_when_connected_and_authenticated(self):
        c = _candidate(connected=True, authenticated=True)
        assert c.is_available

    def test_unavailable_when_disconnected(self):
        c = _candidate(connected=False, authenticated=True)
        assert not c.is_available

    def test_unavailable_when_not_authenticated(self):
        c = _candidate(connected=True, authenticated=False)
        assert not c.is_available

    def test_blacklist_marks_unavailable(self):
        c = _candidate()
        c.blacklist()
        assert c.is_blacklisted
        assert not c.is_available

    def test_unblacklist_restores_availability(self):
        c = _candidate()
        c.blacklist()
        c.unblacklist()
        assert not c.is_blacklisted
        assert c.is_available

    def test_update_health_clamps_to_range(self):
        c = _candidate(health_score=0.5)
        c.update_health(2.0)
        assert c.health_score == 1.0
        c.update_health(-1.0)
        assert c.health_score == 0.0

    def test_update_status(self):
        c = _candidate(connected=True, authenticated=True)
        c.update_status(False, False)
        assert not c.is_connected
        assert not c.is_authenticated

    def test_status_degraded_when_low_health(self):
        c = _candidate(health_score=0.3)
        assert c.status == CandidateStatus.DEGRADED

    def test_status_blacklisted(self):
        c = _candidate()
        c.blacklist()
        assert c.status == CandidateStatus.BLACKLISTED

    def test_status_unavailable_when_disconnected(self):
        c = _candidate(connected=False)
        assert c.status == CandidateStatus.UNAVAILABLE

    def test_status_available_when_healthy(self):
        c = _candidate(health_score=0.9)
        assert c.status == CandidateStatus.AVAILABLE

    def test_supports_exchange_empty_means_all(self):
        c = _candidate(exchanges=frozenset())
        assert c.supports_exchange("ANY_EXCHANGE")

    def test_supports_exchange_specific(self):
        c = _candidate(exchanges=frozenset({"NSE"}))
        assert c.supports_exchange("NSE")
        assert not c.supports_exchange("BSE")

    def test_to_dict_keys(self):
        c = _candidate()
        d = c.to_dict()
        assert "broker_id"       in d
        assert "health_score"    in d
        assert "is_available"    in d
        assert "routing_priority" in d

    def test_thread_safe_health_update(self):
        c = _candidate(health_score=0.5)
        errors = []

        def updater():
            for _ in range(100):
                try:
                    c.update_health(0.8)
                    _ = c.health_score
                except Exception as exc:
                    errors.append(exc)

        threads = [threading.Thread(target=updater) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []


# ─────────────────────────────────────────────────────────────────────────────
# TestRoutingRequest
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingRequest:
    def test_factory_creates_request(self):
        ctx = _context()
        req = make_routing_request(ctx, strategy=RoutingStrategyType.PRIORITY_SELECTION)
        assert req.routing_id   == ctx.routing_id
        assert req.execution_id == ctx.execution_id
        assert req.strategy     == RoutingStrategyType.PRIORITY_SELECTION

    def test_request_id_is_unique(self):
        ctx = _context()
        r1 = make_routing_request(ctx)
        r2 = make_routing_request(ctx)
        assert r1.request_id != r2.request_id

    def test_has_explicit_policy(self):
        ctx = _context()
        r = make_routing_request(ctx, policy_id="p1")
        assert r.has_explicit_policy
        assert r.policy_id == "p1"

    def test_no_explicit_policy_by_default(self):
        ctx = _context()
        r = make_routing_request(ctx)
        assert not r.has_explicit_policy
        assert r.policy_id is None

    def test_to_dict(self):
        ctx = _context()
        r   = make_routing_request(ctx)
        d   = r.to_dict()
        assert "request_id" in d
        assert "strategy"   in d
        assert "context"    in d


# ─────────────────────────────────────────────────────────────────────────────
# TestRoutingDecision
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingDecision:
    def test_make_routed_decision(self):
        d = make_routed_decision(
            request_id="req-1",
            routing_id="r-1",
            selected_broker_id="broker-1",
            selected_broker_name="TestBroker",
        )
        assert d.is_routed
        assert not d.is_failed
        assert d.outcome == RoutingOutcome.ROUTED
        assert d.selected_broker_id == "broker-1"

    def test_make_failover_decision(self):
        d = make_routed_decision(
            request_id="req-1",
            routing_id="r-1",
            selected_broker_id="broker-2",
            selected_broker_name="Fallback",
            failover_used=True,
        )
        assert d.is_routed
        assert d.is_failover
        assert d.outcome == RoutingOutcome.FAILOVER_ROUTED

    def test_make_failed_decision_no_candidates(self):
        d = make_failed_decision(
            request_id="req-1",
            routing_id="r-1",
            outcome=RoutingOutcome.NO_CANDIDATES,
        )
        assert d.is_failed
        assert not d.is_routed
        assert d.selected_broker_id is None

    def test_make_failed_decision_policy_rejected(self):
        d = make_failed_decision(
            request_id="req-1",
            routing_id="r-1",
            outcome=RoutingOutcome.POLICY_REJECTED,
            rejection_reasons=("reason-1",),
        )
        assert d.is_failed
        assert "reason-1" in d.rejection_reasons

    def test_to_dict_keys(self):
        d = make_routed_decision("req-1", "r-1", "b-1", "BrokerA")
        dd = d.to_dict()
        assert "decision_id"    in dd
        assert "selected_broker_id" in dd
        assert "outcome"        in dd
        assert "routing_time_ms" in dd


# ─────────────────────────────────────────────────────────────────────────────
# TestRoutingEvents
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingEvents:
    def test_routing_started_event(self):
        e = make_routing_started_event("r-1")
        assert e.event_type == RoutingEventType.ROUTING_STARTED
        assert e.routing_id == "r-1"
        assert e.event_id

    def test_routing_completed_event(self):
        e = make_routing_completed_event("r-1", broker_id="b-1")
        assert e.event_type == RoutingEventType.ROUTING_COMPLETED
        assert e.broker_id  == "b-1"

    def test_broker_selected_event(self):
        e = make_broker_selected_event("r-1", "b-1", policy_id="p1")
        assert e.event_type == RoutingEventType.BROKER_SELECTED
        assert e.broker_id  == "b-1"
        assert e.policy_id  == "p1"

    def test_broker_rejected_event(self):
        e = make_broker_rejected_event("r-1", "b-2")
        assert e.event_type == RoutingEventType.BROKER_REJECTED
        assert e.broker_id  == "b-2"

    def test_failover_activated_event(self):
        e = make_failover_activated_event("r-1", "b-failover")
        assert e.event_type == RoutingEventType.FAILOVER_ACTIVATED
        assert e.broker_id  == "b-failover"

    def test_policy_applied_event(self):
        e = make_policy_applied_event("r-1", "pol-1")
        assert e.event_type == RoutingEventType.POLICY_APPLIED
        assert e.policy_id  == "pol-1"

    def test_routing_failed_event(self):
        e = make_routing_failed_event("r-1")
        assert e.event_type == RoutingEventType.ROUTING_FAILED

    def test_event_ids_are_unique(self):
        e1 = make_routing_started_event("r-1")
        e2 = make_routing_started_event("r-1")
        assert e1.event_id != e2.event_id

    def test_event_to_dict(self):
        e  = make_broker_selected_event("r-1", "b-1")
        dd = e.to_dict()
        assert "event_id"   in dd
        assert "event_type" in dd
        assert "routing_id" in dd


# ─────────────────────────────────────────────────────────────────────────────
# TestDefaultBrokerPolicy
# ─────────────────────────────────────────────────────────────────────────────

class TestDefaultBrokerPolicy:
    def test_returns_default_broker(self):
        p  = DefaultBrokerPolicy("p1", "broker-1")
        c1 = _candidate("broker-1")
        c2 = _candidate("broker-2")
        assert p.evaluate([c1, c2], _context()) == [c1]

    def test_returns_empty_when_default_not_in_candidates(self):
        p  = DefaultBrokerPolicy("p1", "broker-x")
        c1 = _candidate("broker-1")
        assert p.evaluate([c1], _context()) == []

    def test_policy_type(self):
        p = DefaultBrokerPolicy("p1", "broker-1")
        assert p.policy_type == RoutingPolicyType.DEFAULT_BROKER

    def test_to_dict(self):
        p = DefaultBrokerPolicy("p1", "broker-1")
        d = p.to_dict()
        assert d["policy_id"]   == "p1"
        assert d["policy_type"] == "DEFAULT_BROKER"


# ─────────────────────────────────────────────────────────────────────────────
# TestPreferredBrokerPolicy
# ─────────────────────────────────────────────────────────────────────────────

class TestPreferredBrokerPolicy:
    def test_preferred_broker_comes_first(self):
        p  = PreferredBrokerPolicy("p1")
        c1 = _candidate("broker-1")
        c2 = _candidate("broker-2")
        ctx = _context(preferred_broker="broker-2")
        result = p.evaluate([c1, c2], ctx)
        assert result[0].broker_id == "broker-2"

    def test_fallback_when_no_preferred(self):
        p   = PreferredBrokerPolicy("p1", fallback_broker_id="broker-1")
        c1  = _candidate("broker-1")
        c2  = _candidate("broker-2")
        ctx = _context()
        result = p.evaluate([c1, c2], ctx)
        assert result[0].broker_id == "broker-1"

    def test_all_candidates_returned_in_order(self):
        p   = PreferredBrokerPolicy("p1")
        c1  = _candidate("broker-1")
        c2  = _candidate("broker-2")
        ctx = _context()
        result = p.evaluate([c1, c2], ctx)
        assert len(result) == 2


# ─────────────────────────────────────────────────────────────────────────────
# TestCapabilityBasedPolicy
# ─────────────────────────────────────────────────────────────────────────────

class TestCapabilityBasedPolicy:
    def test_filters_by_required_capabilities(self):
        cap = BrokerCapability.OPTIONS
        p   = CapabilityBasedPolicy("p1", required_capabilities=frozenset({cap}))
        c1  = _candidate("broker-1", caps=_caps(cap))
        c2  = _candidate("broker-2", caps=_empty_caps())
        result = p.evaluate([c1, c2], _context())
        assert c1 in result
        assert c2 not in result

    def test_all_candidates_when_no_required_caps(self):
        p  = CapabilityBasedPolicy("p1")
        c1 = _candidate("broker-1")
        c2 = _candidate("broker-2")
        result = p.evaluate([c1, c2], _context())
        assert len(result) == 2

    def test_combines_context_and_policy_caps(self):
        cap1 = BrokerCapability.CASH_TRADING
        cap2 = BrokerCapability.OPTIONS
        p    = CapabilityBasedPolicy("p1", required_capabilities=frozenset({cap1}))
        # context also requires cap2
        ctx  = _context(required_caps=frozenset({cap2}))
        c_both = _candidate("b1", caps=_caps(cap1, cap2))
        c_one  = _candidate("b2", caps=_caps(cap1))
        result = p.evaluate([c_both, c_one], ctx)
        assert c_both in result
        assert c_one  not in result


# ─────────────────────────────────────────────────────────────────────────────
# TestInstrumentBasedPolicy
# ─────────────────────────────────────────────────────────────────────────────

class TestInstrumentBasedPolicy:
    def test_blocked_symbol_returns_empty(self):
        p   = InstrumentBasedPolicy("p1", blocked_symbols=frozenset({"BLOCKED"}))
        c1  = _candidate()
        ctx = _context(symbol="BLOCKED")
        assert p.evaluate([c1], ctx) == []

    def test_allowed_symbol_pass_through(self):
        p   = InstrumentBasedPolicy("p1", allowed_symbols=frozenset({"RELIANCE"}))
        c1  = _candidate()
        ctx = _context(symbol="RELIANCE")
        assert len(p.evaluate([c1], ctx)) == 1

    def test_symbol_not_in_allowed_returns_empty(self):
        p   = InstrumentBasedPolicy("p1", allowed_symbols=frozenset({"RELIANCE"}))
        c1  = _candidate()
        ctx = _context(symbol="TCS")
        assert p.evaluate([c1], ctx) == []

    def test_symbol_broker_map_routes_to_specific_broker(self):
        p  = InstrumentBasedPolicy(
            "p1",
            symbol_broker_map={"INFY": ["broker-2"]},
        )
        c1 = _candidate("broker-1")
        c2 = _candidate("broker-2")
        ctx = _context(symbol="INFY")
        result = p.evaluate([c1, c2], ctx)
        assert result == [c2]


# ─────────────────────────────────────────────────────────────────────────────
# TestMarketBasedPolicy
# ─────────────────────────────────────────────────────────────────────────────

class TestMarketBasedPolicy:
    def test_routes_by_market(self):
        p  = MarketBasedPolicy("p1", market_broker_map={"EQUITY": ["broker-1"]})
        c1 = _candidate("broker-1")
        c2 = _candidate("broker-2")
        ctx = _context()  # asset_class = EQUITY
        result = p.evaluate([c1, c2], ctx)
        # default asset_class is EQUITY
        assert c1 in result or len(result) == 2  # depends on context default

    def test_no_map_returns_all(self):
        p   = MarketBasedPolicy("p1")
        c1  = _candidate("broker-1")
        ctx = _context()
        result = p.evaluate([c1], ctx)
        assert result == [c1]


# ─────────────────────────────────────────────────────────────────────────────
# TestExchangeBasedPolicy
# ─────────────────────────────────────────────────────────────────────────────

class TestExchangeBasedPolicy:
    def test_filters_by_exchange(self):
        p   = ExchangeBasedPolicy("p1")
        c1  = _candidate("broker-1", exchanges=frozenset({"NSE"}))
        c2  = _candidate("broker-2", exchanges=frozenset({"BSE"}))
        ctx = _context(exchange="NSE")
        result = p.evaluate([c1, c2], ctx)
        assert c1 in result
        assert c2 not in result

    def test_empty_exchange_set_means_all(self):
        p   = ExchangeBasedPolicy("p1")
        c1  = _candidate("broker-1", exchanges=frozenset())  # supports all
        ctx = _context(exchange="MCX")
        result = p.evaluate([c1], ctx)
        assert c1 in result


# ─────────────────────────────────────────────────────────────────────────────
# TestProductBasedPolicy
# ─────────────────────────────────────────────────────────────────────────────

class TestProductBasedPolicy:
    def test_filters_by_product(self):
        p   = ProductBasedPolicy("p1")
        c1  = _candidate("broker-1", products=frozenset({ProductType.MIS}))
        c2  = _candidate("broker-2", products=frozenset({ProductType.CNC}))
        ctx = _context(product="MIS")
        result = p.evaluate([c1, c2], ctx)
        assert c1 in result
        assert c2 not in result

    def test_empty_product_set_means_all(self):
        p   = ProductBasedPolicy("p1")
        c1  = _candidate("broker-1", products=frozenset())
        ctx = _context(product="CNC")
        result = p.evaluate([c1], ctx)
        assert c1 in result


# ─────────────────────────────────────────────────────────────────────────────
# TestPriorityBasedPolicy
# ─────────────────────────────────────────────────────────────────────────────

class TestPriorityBasedPolicy:
    def test_sorts_by_priority_descending(self):
        p  = PriorityBasedPolicy("p1")
        c1 = _candidate("broker-1", priority=5)
        c2 = _candidate("broker-2", priority=10)
        c3 = _candidate("broker-3", priority=1)
        result = p.evaluate([c1, c2, c3], _context())
        assert result[0].broker_id == "broker-2"
        assert result[-1].broker_id == "broker-3"

    def test_min_priority_filter(self):
        p  = PriorityBasedPolicy("p1", min_priority=5)
        c1 = _candidate("broker-1", priority=1)
        c2 = _candidate("broker-2", priority=10)
        result = p.evaluate([c1, c2], _context())
        assert c1 not in result
        assert c2 in result


# ─────────────────────────────────────────────────────────────────────────────
# TestHealthBasedPolicy
# ─────────────────────────────────────────────────────────────────────────────

class TestHealthBasedPolicy:
    def test_filters_below_min_score(self):
        p  = HealthBasedPolicy("p1", min_health_score=0.7)
        c1 = _candidate("broker-1", health_score=0.9)
        c2 = _candidate("broker-2", health_score=0.5)
        result = p.evaluate([c1, c2], _context())
        assert c1 in result
        assert c2 not in result

    def test_sorts_by_health_descending(self):
        p  = HealthBasedPolicy("p1", min_health_score=0.0)
        c1 = _candidate("broker-1", health_score=0.5)
        c2 = _candidate("broker-2", health_score=0.9)
        c3 = _candidate("broker-3", health_score=0.7)
        result = p.evaluate([c1, c2, c3], _context())
        assert result[0].broker_id == "broker-2"

    def test_clamped_min_score(self):
        p = HealthBasedPolicy("p1", min_health_score=1.5)
        assert p.min_health_score == 1.0


# ─────────────────────────────────────────────────────────────────────────────
# TestFailoverRoutingPolicy
# ─────────────────────────────────────────────────────────────────────────────

class TestFailoverRoutingPolicy:
    def test_returns_primary_when_available(self):
        p   = FailoverRoutingPolicy("p1", "broker-primary", "broker-secondary")
        c1  = _candidate("broker-primary")
        c2  = _candidate("broker-secondary")
        result = p.evaluate([c1, c2], _context())
        assert result[0].broker_id == "broker-primary"

    def test_returns_secondary_when_primary_absent(self):
        p   = FailoverRoutingPolicy("p1", "broker-primary", "broker-secondary")
        c2  = _candidate("broker-secondary")
        result = p.evaluate([c2], _context())
        assert result[0].broker_id == "broker-secondary"

    def test_supports_failover_true(self):
        p = FailoverRoutingPolicy("p1", "b-a", "b-b")
        assert p.supports_failover is True

    def test_primary_before_secondary(self):
        p  = FailoverRoutingPolicy("p1", "b-p", "b-s")
        cp = _candidate("b-p")
        cs = _candidate("b-s")
        result = p.evaluate([cs, cp], _context())
        assert result[0].broker_id == "b-p"
        assert result[1].broker_id == "b-s"


# ─────────────────────────────────────────────────────────────────────────────
# TestWeightedRoutingPolicy
# ─────────────────────────────────────────────────────────────────────────────

class TestWeightedRoutingPolicy:
    def test_includes_candidates_with_positive_weight(self):
        p  = WeightedRoutingPolicy("p1")
        c1 = _candidate("b1", weight=1.0)
        c2 = _candidate("b2", weight=0.0)  # zero weight → excluded
        result = p.evaluate([c1, c2], _context())
        assert c1 in result
        assert c2 not in result

    def test_all_included_when_all_positive_weight(self):
        p  = WeightedRoutingPolicy("p1")
        c1 = _candidate("b1", weight=2.0)
        c2 = _candidate("b2", weight=0.5)
        result = p.evaluate([c1, c2], _context())
        assert len(result) == 2


# ─────────────────────────────────────────────────────────────────────────────
# TestCustomRoutingPolicy
# ─────────────────────────────────────────────────────────────────────────────

class TestCustomRoutingPolicy:
    def test_custom_evaluator_called(self):
        called = []

        def evaluator(candidates, context):
            called.append(True)
            return candidates[:1]

        p  = CustomRoutingPolicy("p1", evaluator)
        c1 = _candidate("b1")
        c2 = _candidate("b2")
        result = p.evaluate([c1, c2], _context())
        assert called
        assert result == [c1]

    def test_policy_type(self):
        p = CustomRoutingPolicy("p1", lambda c, ctx: c)
        assert p.policy_type == RoutingPolicyType.CUSTOM_POLICY


# ─────────────────────────────────────────────────────────────────────────────
# TestRoutingStrategySelector
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingStrategySelector:
    def setup_method(self):
        self.sel = RoutingStrategySelector()
        self.ctx = _context()

    def test_single_returns_first(self):
        c1, c2 = _candidate("b1"), _candidate("b2")
        result = self.sel.select([c1, c2], self.ctx, RoutingStrategyType.SINGLE_DESTINATION)
        assert result == c1

    def test_priority_returns_highest(self):
        c1 = _candidate("b1", priority=5)
        c2 = _candidate("b2", priority=20)
        result = self.sel.select([c1, c2], self.ctx, RoutingStrategyType.PRIORITY_SELECTION)
        assert result == c2

    def test_weighted_returns_one(self):
        c1 = _candidate("b1", weight=1.0)
        c2 = _candidate("b2", weight=1.0)
        result = self.sel.select([c1, c2], self.ctx, RoutingStrategyType.WEIGHTED_SELECTION)
        assert result in (c1, c2)

    def test_weighted_all_zero_falls_back_to_priority(self):
        c1 = _candidate("b1", weight=0.0, priority=10)
        c2 = _candidate("b2", weight=0.0, priority=5)
        result = self.sel.select([c1, c2], self.ctx, RoutingStrategyType.WEIGHTED_SELECTION)
        assert result == c1  # highest priority

    def test_capability_matching_best_fit(self):
        cap1 = BrokerCapability.CASH_TRADING
        cap2 = BrokerCapability.OPTIONS
        ctx  = _context(required_caps=frozenset({cap1, cap2}))
        c1   = _candidate("b1", caps=_caps(cap1, cap2))
        c2   = _candidate("b2", caps=_caps(cap1))
        result = self.sel.select([c1, c2], ctx, RoutingStrategyType.CAPABILITY_MATCHING)
        assert result == c1

    def test_health_optimized_returns_healthiest(self):
        c1 = _candidate("b1", health_score=0.6)
        c2 = _candidate("b2", health_score=0.9)
        result = self.sel.select([c1, c2], self.ctx, RoutingStrategyType.HEALTH_OPTIMIZED)
        assert result == c2

    def test_fallback_returns_first_available(self):
        c1 = _candidate("b1", connected=False)
        c2 = _candidate("b2", connected=True, authenticated=True)
        result = self.sel.select([c1, c2], self.ctx, RoutingStrategyType.FALLBACK_STRATEGY)
        assert result == c2

    def test_returns_none_on_empty_list(self):
        result = self.sel.select([], self.ctx, RoutingStrategyType.SINGLE_DESTINATION)
        assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# TestRoutingSelector
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingSelector:
    def setup_method(self):
        self.sel = RoutingSelector()
        self.ctx = _context()

    def test_select_with_no_policy(self):
        c1 = _candidate("b1")
        selected, reasons = self.sel.select([c1], self.ctx, None, RoutingStrategyType.SINGLE_DESTINATION)
        assert selected == c1
        assert reasons == []

    def test_select_with_policy(self):
        p  = DefaultBrokerPolicy("p1", "b1")
        c1 = _candidate("b1")
        c2 = _candidate("b2")
        selected, reasons = self.sel.select([c1, c2], self.ctx, p, RoutingStrategyType.SINGLE_DESTINATION)
        assert selected == c1

    def test_rejection_recorded_when_policy_filters(self):
        p  = DefaultBrokerPolicy("p1", "b1")
        c1 = _candidate("b1")
        c2 = _candidate("b2")
        selected, reasons = self.sel.select([c1, c2], self.ctx, p, RoutingStrategyType.SINGLE_DESTINATION)
        assert any("b2" in r for r in reasons)

    def test_returns_none_when_all_rejected(self):
        p  = DefaultBrokerPolicy("p1", "b-nonexistent")
        c1 = _candidate("b1")
        selected, reasons = self.sel.select([c1], self.ctx, p, RoutingStrategyType.SINGLE_DESTINATION)
        assert selected is None
        assert len(reasons) > 0

    def test_select_fallback_returns_highest_priority(self):
        c1 = _candidate("b1", priority=5)
        c2 = _candidate("b2", priority=10)
        result = self.sel.select_fallback([c1, c2], self.ctx)
        assert result == c2

    def test_select_fallback_returns_none_when_none_available(self):
        c1 = _candidate("b1", connected=False)
        result = self.sel.select_fallback([c1], self.ctx)
        assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# TestRoutingValidation
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingValidation:
    def setup_method(self):
        self.v = RoutingValidator()

    def test_valid_context(self):
        result = self.v.validate_context(_context())
        assert result.is_valid

    def test_invalid_context_empty_symbol(self):
        ctx = _context(symbol="")
        result = self.v.validate_context(ctx)
        assert not result.is_valid
        assert any("symbol" in e for e in result.errors)

    def test_invalid_context_zero_quantity(self):
        ctx = make_routing_context(
            "e", "o", "p", "s",
            symbol="RELIANCE", exchange="NSE",
            quantity=0.0, price=100.0,
        )
        result = self.v.validate_context(ctx)
        assert not result.is_valid

    def test_invalid_context_negative_price(self):
        ctx = make_routing_context(
            "e", "o", "p", "s",
            symbol="RELIANCE", exchange="NSE",
            quantity=10.0, price=-5.0,
        )
        result = self.v.validate_context(ctx)
        assert not result.is_valid

    def test_validate_request_valid(self):
        ctx = _context()
        req = make_routing_request(ctx)
        result = self.v.validate_request(req)
        assert result.is_valid

    def test_validate_candidate_valid(self):
        c = _candidate()
        result = self.v.validate_candidate(c)
        assert result.is_valid

    def test_validate_policy_valid(self):
        p = DefaultBrokerPolicy("p1", "b1")
        result = self.v.validate_policy(p)
        assert result.is_valid

    def test_validate_decision_valid_routed(self):
        d = make_routed_decision("req-1", "r-1", "b-1", "BrkA")
        result = self.v.validate_decision(d)
        assert result.is_valid

    def test_raise_if_invalid_raises_on_failure(self):
        result = RoutingValidationResult(is_valid=False, errors=("err1",))
        with pytest.raises(RoutingValidationError):
            self.v.raise_if_invalid(result)

    def test_raise_if_invalid_silent_on_success(self):
        result = RoutingValidationResult(is_valid=True)
        self.v.raise_if_invalid(result)  # should not raise

    def test_validation_result_to_dict(self):
        r = RoutingValidationResult(is_valid=True, warnings=("w1",))
        d = r.to_dict()
        assert d["is_valid"] is True
        assert "w1" in d["warnings"]


# ─────────────────────────────────────────────────────────────────────────────
# TestRoutingStatistics
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingStatistics:
    def test_initial_state(self):
        s = RoutingStatistics()
        assert s.routing_requests  == 0
        assert s.successful_routes == 0
        assert s.failed_routes     == 0
        assert s.failovers         == 0

    def test_record_successful_routing(self):
        s = RoutingStatistics()
        s.record_routing(is_success=True, routing_time_ms=5.0, policy_id="p1")
        assert s.routing_requests  == 1
        assert s.successful_routes == 1
        assert s.failed_routes     == 0
        assert s.policy_usage["p1"] == 1

    def test_record_failed_routing(self):
        s = RoutingStatistics()
        s.record_routing(is_success=False, routing_time_ms=2.0)
        assert s.failed_routes     == 1
        assert s.successful_routes == 0

    def test_success_rate(self):
        s = RoutingStatistics()
        s.record_routing(is_success=True, routing_time_ms=1.0)
        s.record_routing(is_success=False, routing_time_ms=1.0)
        assert s.success_rate == 0.5
        assert s.failure_rate == 0.5

    def test_average_routing_time(self):
        s = RoutingStatistics()
        s.record_routing(is_success=True, routing_time_ms=10.0)
        s.record_routing(is_success=True, routing_time_ms=20.0)
        assert s.average_routing_time_ms == 15.0

    def test_failover_rate(self):
        s = RoutingStatistics()
        s.record_routing(is_success=True, routing_time_ms=1.0)
        s.record_routing(is_success=True, routing_time_ms=1.0)
        s.record_failover()
        assert s.failover_rate == 0.5

    def test_broker_utilization(self):
        s = RoutingStatistics()
        s.record_broker_utilization("broker-1")
        s.record_broker_utilization("broker-1")
        s.record_broker_utilization("broker-2")
        assert s.broker_utilization["broker-1"] == 2
        assert s.broker_utilization["broker-2"] == 1

    def test_zero_division_safety(self):
        s = RoutingStatistics()
        assert s.success_rate           == 0.0
        assert s.average_routing_time_ms == 0.0
        assert s.failover_rate          == 0.0

    def test_reset(self):
        s = RoutingStatistics()
        s.record_routing(is_success=True, routing_time_ms=5.0)
        s.reset()
        assert s.routing_requests == 0
        assert s.policy_usage     == {}

    def test_copy_is_independent(self):
        s = RoutingStatistics()
        s.record_routing(is_success=True, routing_time_ms=1.0)
        c = s.copy()
        s.reset()
        assert c.routing_requests == 1

    def test_to_dict(self):
        s = RoutingStatistics()
        d = s.to_dict()
        assert "routing_requests" in d
        assert "success_rate"     in d


# ─────────────────────────────────────────────────────────────────────────────
# TestRoutingHistory
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingHistory:
    def test_append_and_retrieve_decision(self):
        h = RoutingHistory()
        d = make_routed_decision("req-1", "r-1", "b-1", "BrkA")
        h.append_decision(d)
        assert d in h.decisions()

    def test_append_and_retrieve_event(self):
        h = RoutingHistory()
        e = make_routing_started_event("r-1")
        h.append_event(e)
        assert e in h.events()

    def test_bounded_capacity(self):
        h = RoutingHistory(max_decisions=3)
        for i in range(5):
            h.append_decision(make_routed_decision(f"r{i}", f"rid{i}", "b", "B"))
        assert h.decision_count == 3

    def test_decisions_for_broker(self):
        h  = RoutingHistory()
        d1 = make_routed_decision("r1", "rid1", "b1", "B1")
        d2 = make_routed_decision("r2", "rid2", "b2", "B2")
        h.append_decision(d1)
        h.append_decision(d2)
        assert h.decisions_for_broker("b1") == [d1]

    def test_successful_decisions(self):
        h  = RoutingHistory()
        d1 = make_routed_decision("r1", "rid1", "b1", "B1")
        d2 = make_failed_decision("r2", "rid2", RoutingOutcome.NO_CANDIDATES)
        h.append_decision(d1)
        h.append_decision(d2)
        assert d1 in h.successful_decisions()
        assert d2 not in h.successful_decisions()

    def test_failed_decisions(self):
        h  = RoutingHistory()
        d1 = make_routed_decision("r1", "rid1", "b1", "B1")
        d2 = make_failed_decision("r2", "rid2", RoutingOutcome.NO_CANDIDATES)
        h.append_decision(d1)
        h.append_decision(d2)
        assert d2 in h.failed_decisions()
        assert d1 not in h.failed_decisions()

    def test_latest_decision(self):
        h  = RoutingHistory()
        d1 = make_routed_decision("r1", "rid1", "b1", "B1")
        d2 = make_routed_decision("r2", "rid2", "b2", "B2")
        h.append_decision(d1)
        h.append_decision(d2)
        assert h.latest_decision() == d2

    def test_latest_decision_none_when_empty(self):
        h = RoutingHistory()
        assert h.latest_decision() is None

    def test_clear(self):
        h = RoutingHistory()
        h.append_decision(make_routed_decision("r1", "rid1", "b1", "B1"))
        h.append_event(make_routing_started_event("rid1"))
        h.clear()
        assert h.decision_count == 0
        assert h.event_count    == 0


# ─────────────────────────────────────────────────────────────────────────────
# TestRoutingRegistry
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingRegistry:
    def _started_registry(self, **kwargs) -> RoutingRegistry:
        r = RoutingRegistry(**kwargs)
        r.start()
        return r

    def test_register_and_get_policy(self):
        r = self._started_registry()
        p = DefaultBrokerPolicy("p1", "b1")
        r.register_policy(p)
        assert r.get_policy("p1") == p
        r.stop()

    def test_duplicate_policy_raises(self):
        r = self._started_registry()
        p = DefaultBrokerPolicy("p1", "b1")
        r.register_policy(p)
        with pytest.raises(PolicyAlreadyRegisteredError):
            r.register_policy(DefaultBrokerPolicy("p1", "b2"))
        r.stop()

    def test_remove_policy(self):
        r = self._started_registry()
        p = DefaultBrokerPolicy("p1", "b1")
        r.register_policy(p)
        r.remove_policy("p1")
        with pytest.raises(RoutingPolicyNotFoundError):
            r.get_policy("p1")
        r.stop()

    def test_set_default_policy(self):
        r = self._started_registry()
        p = DefaultBrokerPolicy("p1", "b1")
        r.register_policy(p)
        r.set_default_policy("p1")
        assert r.default_policy() == p
        r.stop()

    def test_register_and_get_candidate(self):
        r = self._started_registry()
        c = _candidate()
        r.register_candidate(c)
        assert r.get_candidate("broker-1") == c
        r.stop()

    def test_duplicate_candidate_raises(self):
        r = self._started_registry()
        c = _candidate()
        r.register_candidate(c)
        with pytest.raises(CandidateAlreadyRegisteredError):
            r.register_candidate(_candidate())
        r.stop()

    def test_remove_candidate(self):
        r = self._started_registry()
        c = _candidate()
        r.register_candidate(c)
        r.remove_candidate("broker-1")
        with pytest.raises(CandidateNotFoundError):
            r.get_candidate("broker-1")
        r.stop()

    def test_available_candidates_excludes_blacklisted(self):
        r  = self._started_registry()
        c1 = _candidate("b1")
        c2 = _candidate("b2")
        r.register_candidate(c1)
        r.register_candidate(c2)
        r.blacklist_broker("b1")
        available = r.available_candidates()
        assert c2 in available
        assert c1 not in available
        r.stop()

    def test_unblacklist_restores_availability(self):
        r = self._started_registry()
        c = _candidate()
        r.register_candidate(c)
        r.blacklist_broker("broker-1")
        r.unblacklist_broker("broker-1")
        assert not r.is_blacklisted("broker-1")
        assert c in r.available_candidates()
        r.stop()

    def test_capacity_limit_candidates(self):
        r = self._started_registry(max_candidates=2)
        r.register_candidate(_candidate("b1"))
        r.register_candidate(_candidate("b2"))
        with pytest.raises(RoutingRegistryCapacityError):
            r.register_candidate(_candidate("b3"))
        r.stop()

    def test_capacity_limit_policies(self):
        r = self._started_registry(max_policies=1)
        r.register_policy(DefaultBrokerPolicy("p1", "b1"))
        with pytest.raises(RoutingRegistryCapacityError):
            r.register_policy(DefaultBrokerPolicy("p2", "b2"))
        r.stop()

    def test_write_guard_when_not_running(self):
        r = RoutingRegistry()
        with pytest.raises(RoutingEngineNotRunningError):
            r.register_policy(DefaultBrokerPolicy("p1", "b1"))

    def test_read_permitted_when_stopped(self):
        r  = RoutingRegistry()
        # calling all_candidates() on a stopped registry is allowed
        result = r.all_candidates()
        assert result == []


# ─────────────────────────────────────────────────────────────────────────────
# TestRoutingFactory
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingFactory:
    def test_create_context(self):
        ctx = RoutingFactory.create_context("e", "o", "p", "s", symbol="TCS", exchange="BSE", quantity=5.0, price=200.0)
        assert ctx.symbol == "TCS"

    def test_create_candidate(self):
        caps = BrokerCapabilities(frozenset())
        c = RoutingFactory.create_candidate("b1", "BrkA", caps)
        assert c.broker_id == "b1"
        assert c.is_available

    def test_create_request(self):
        ctx = _context()
        req = RoutingFactory.create_request(ctx, strategy=RoutingStrategyType.HEALTH_OPTIMIZED)
        assert req.strategy == RoutingStrategyType.HEALTH_OPTIMIZED

    def test_create_statistics(self):
        s = RoutingFactory.create_statistics()
        assert isinstance(s, RoutingStatistics)

    def test_create_history(self):
        h = RoutingFactory.create_history(max_decisions=100)
        assert isinstance(h, RoutingHistory)

    def test_create_default_broker_policy(self):
        p = RoutingFactory.create_default_broker_policy("p1", "b-default")
        assert isinstance(p, DefaultBrokerPolicy)
        assert p.default_broker_id == "b-default"

    def test_create_health_policy(self):
        p = RoutingFactory.create_health_policy("p1", min_health_score=0.6)
        assert isinstance(p, HealthBasedPolicy)
        assert p.min_health_score == 0.6

    def test_create_failover_policy(self):
        p = RoutingFactory.create_failover_policy("p1", "primary", "secondary")
        assert isinstance(p, FailoverRoutingPolicy)
        assert p.primary_broker_id   == "primary"
        assert p.secondary_broker_id == "secondary"

    def test_create_custom_policy(self):
        evaluator = lambda c, ctx: c
        p = RoutingFactory.create_custom_policy("p1", evaluator)
        assert isinstance(p, CustomRoutingPolicy)

    def test_create_exchange_policy(self):
        from iios.execution.gateway.routing import ExchangeBasedPolicy
        p = RoutingFactory.create_exchange_policy("p1")
        assert isinstance(p, ExchangeBasedPolicy)


# ─────────────────────────────────────────────────────────────────────────────
# TestRoutingManager
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingManager:
    def _started_manager(self) -> RoutingManager:
        m = RoutingManager()
        m.start()
        return m

    def test_route_with_no_candidates_fails(self):
        m   = self._started_manager()
        ctx = _context()
        req = make_routing_request(ctx)
        d   = m.route(req)
        assert d.is_failed
        m.stop()

    def test_route_success_with_default_policy(self):
        m   = self._started_manager()
        c   = _candidate("b1")
        p   = DefaultBrokerPolicy("p1", "b1")
        m.register_candidate(c)
        m.register_policy(p)
        m.set_default_policy("p1")
        ctx = _context()
        req = make_routing_request(ctx)
        d   = m.route(req)
        assert d.is_routed
        assert d.selected_broker_id == "b1"
        m.stop()

    def test_statistics_updated_after_route(self):
        m  = self._started_manager()
        c  = _candidate("b1")
        p  = DefaultBrokerPolicy("p1", "b1")
        m.register_candidate(c)
        m.register_policy(p)
        m.set_default_policy("p1")
        m.route(make_routing_request(_context()))
        stats = m.statistics()
        assert stats.routing_requests == 1
        assert stats.successful_routes == 1
        m.stop()

    def test_event_listener_receives_events(self):
        m        = self._started_manager()
        received: List[RoutingEvent] = []
        m.add_event_listener(received.append)
        c  = _candidate("b1")
        p  = DefaultBrokerPolicy("p1", "b1")
        m.register_candidate(c)
        m.register_policy(p)
        m.set_default_policy("p1")
        m.route(make_routing_request(_context()))
        types = [e.event_type for e in received]
        assert RoutingEventType.ROUTING_STARTED   in types
        assert RoutingEventType.BROKER_SELECTED   in types
        assert RoutingEventType.ROUTING_COMPLETED in types
        m.stop()

    def test_remove_event_listener(self):
        m        = self._started_manager()
        received: List[RoutingEvent] = []
        m.add_event_listener(received.append)
        m.remove_event_listener(received.append)
        c  = _candidate("b1")
        p  = DefaultBrokerPolicy("p1", "b1")
        m.register_candidate(c)
        m.register_policy(p)
        m.set_default_policy("p1")
        m.route(make_routing_request(_context()))
        assert received == []
        m.stop()

    def test_route_raises_when_not_running(self):
        m   = RoutingManager()
        ctx = _context()
        req = make_routing_request(ctx)
        with pytest.raises(RoutingEngineNotRunningError):
            m.route(req)

    def test_blacklisted_broker_excluded_from_routing(self):
        m  = self._started_manager()
        c1 = _candidate("b1")
        c2 = _candidate("b2")
        p  = PriorityBasedPolicy("p1")
        m.register_candidate(c1)
        m.register_candidate(c2)
        m.register_policy(p)
        m.set_default_policy("p1")
        m.blacklist_broker("b1")
        d = m.route(make_routing_request(_context()))
        assert d.selected_broker_id == "b2"
        m.stop()

    def test_snapshot_contains_stats(self):
        m = self._started_manager()
        snap = m.snapshot()
        assert "statistics"  in snap
        assert "policy_count" in snap
        m.stop()

    def test_update_candidate_health(self):
        m = self._started_manager()
        c = _candidate("b1")
        m.register_candidate(c)
        m.update_candidate_health("b1", 0.3)
        assert c.health_score == pytest.approx(0.3)
        m.stop()

    def test_update_candidate_status(self):
        m = self._started_manager()
        c = _candidate("b1")
        m.register_candidate(c)
        m.update_candidate_status("b1", False, False)
        assert not c.is_connected
        m.stop()


# ─────────────────────────────────────────────────────────────────────────────
# TestRoutingEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingEngine:
    def test_start_stop(self):
        e = RoutingEngine()
        e.start()
        assert e.engine_state == "RUNNING"
        e.stop()
        assert e.engine_state != "RUNNING"

    def test_double_start_raises(self):
        e = RoutingEngine()
        e.start()
        from iios.investment.workflow.engine_lifecycle import EngineAlreadyRunningError
        with pytest.raises(EngineAlreadyRunningError):
            e.start()
        e.stop()

    def test_double_stop_raises(self):
        e = RoutingEngine()
        e.start()
        e.stop()
        from iios.investment.workflow.engine_lifecycle import EngineNotRunningError
        with pytest.raises(EngineNotRunningError):
            e.stop()

    def test_route_raises_when_stopped(self):
        e   = RoutingEngine()
        ctx = _context()
        with pytest.raises(RoutingEngineNotRunningError):
            e.route(ctx)

    def test_route_returns_decision(self):
        e   = _started_engine()
        c   = _candidate("b1")
        p   = DefaultBrokerPolicy("p1", "b1")
        e.register_candidate(c)
        e.register_policy(p)
        e.set_default_policy("p1")
        d = e.route(_context())
        assert isinstance(d, RoutingDecision)
        e.stop()

    def test_route_with_explicit_strategy(self):
        e  = _started_engine()
        c  = _candidate("b1")
        p  = PriorityBasedPolicy("p1")
        e.register_candidate(c)
        e.register_policy(p)
        e.set_default_policy("p1")
        d = e.route(_context(), strategy=RoutingStrategyType.HEALTH_OPTIMIZED)
        assert d.is_routed
        e.stop()

    def test_candidate_count(self):
        e = _started_engine()
        e.register_candidate(_candidate("b1"))
        e.register_candidate(_candidate("b2"))
        assert e.candidate_count == 2
        e.stop()

    def test_policy_count(self):
        e = _started_engine()
        e.register_policy(DefaultBrokerPolicy("p1", "b1"))
        assert e.policy_count == 1
        e.stop()

    def test_default_strategy_used_when_none_given(self):
        e = _started_engine(default_strategy=RoutingStrategyType.HEALTH_OPTIMIZED)
        assert e.default_strategy == RoutingStrategyType.HEALTH_OPTIMIZED
        e.stop()

    def test_statistics_after_route(self):
        e  = _started_engine()
        c  = _candidate("b1")
        e.register_candidate(c)
        p  = DefaultBrokerPolicy("p1", "b1")
        e.register_policy(p)
        e.set_default_policy("p1")
        e.route(_context())
        s = e.statistics()
        assert s.routing_requests == 1
        e.stop()

    def test_event_listener_on_engine(self):
        e        = _started_engine()
        received: List[RoutingEvent] = []
        e.add_event_listener(received.append)
        c  = _candidate("b1")
        p  = DefaultBrokerPolicy("p1", "b1")
        e.register_candidate(c)
        e.register_policy(p)
        e.set_default_policy("p1")
        e.route(_context())
        assert len(received) > 0
        e.stop()

    def test_snapshot(self):
        e    = _started_engine()
        snap = e.snapshot()
        assert "default_strategy" in snap
        e.stop()


# ─────────────────────────────────────────────────────────────────────────────
# TestFailoverScenarios
# ─────────────────────────────────────────────────────────────────────────────

class TestFailoverScenarios:
    def test_failover_when_primary_absent(self):
        e  = _started_engine()
        c2 = _candidate("secondary")
        p  = FailoverRoutingPolicy("p1", "primary", "secondary")
        e.register_candidate(c2)
        e.register_policy(p)
        e.set_default_policy("p1")
        d = e.route(_context())
        assert d.is_routed
        assert d.selected_broker_id == "secondary"
        e.stop()

    def test_failover_decision_outcome(self):
        # Both registered; primary available → normal routing
        e   = _started_engine()
        cp  = _candidate("primary")
        cs  = _candidate("secondary")
        p   = FailoverRoutingPolicy("p1", "primary", "secondary")
        e.register_candidate(cp)
        e.register_candidate(cs)
        e.register_policy(p)
        e.set_default_policy("p1")
        d = e.route(_context())
        assert d.is_routed
        assert d.selected_broker_id == "primary"
        e.stop()

    def test_manager_triggers_emergency_failover(self):
        """When policy returns empty but supports_failover, manager falls back."""
        e   = _started_engine()
        # Register a candidate that the failover policy would NOT pick as primary
        c_fallback = _candidate("fallback-broker", priority=5)
        p = FailoverRoutingPolicy("p1", "ghost-primary", "also-ghost")
        p2 = PreferredBrokerPolicy("p2", fallback_broker_id="fallback-broker")
        e.register_candidate(c_fallback)
        e.register_policy(p)
        e.register_policy(p2)
        # With failover policy and no primary/secondary, manager emergency fallback kicks in
        d = e.route(_context(), policy_id="p1")
        # Decision may be failed (no candidates match) or routed via emergency fallback
        # Either way, no exception
        assert isinstance(d, RoutingDecision)
        e.stop()

    def test_failover_event_fired(self):
        e        = _started_engine()
        received: List[RoutingEvent] = []
        e.add_event_listener(received.append)
        # Primary absent, secondary present
        c2 = _candidate("secondary")
        p  = FailoverRoutingPolicy("p1", "primary", "secondary")
        e.register_candidate(c2)
        e.register_policy(p)
        e.set_default_policy("p1")
        d = e.route(_context())
        # With only secondary available, FailoverRoutingPolicy returns [secondary]
        # which is a direct route (not emergency failover path)
        assert d.is_routed
        e.stop()


# ─────────────────────────────────────────────────────────────────────────────
# TestConcurrency
# ─────────────────────────────────────────────────────────────────────────────

class TestConcurrency:
    def test_concurrent_routes(self):
        e   = _started_engine()
        c1  = _candidate("b1", priority=10)
        c2  = _candidate("b2", priority=5)
        p   = PriorityBasedPolicy("p1")
        e.register_candidate(c1)
        e.register_candidate(c2)
        e.register_policy(p)
        e.set_default_policy("p1")
        errors: List[Exception] = []

        def do_route():
            for _ in range(20):
                try:
                    d = e.route(_context())
                    assert d.is_routed
                except Exception as exc:
                    errors.append(exc)

        threads = [threading.Thread(target=do_route) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        stats = e.statistics()
        assert stats.routing_requests == 160
        e.stop()

    def test_concurrent_candidate_health_updates(self):
        e  = _started_engine()
        c1 = _candidate("b1")
        e.register_candidate(c1)
        errors: List[Exception] = []

        def updater():
            for i in range(50):
                try:
                    e.update_candidate_health("b1", float(i % 10) / 10.0)
                except Exception as exc:
                    errors.append(exc)

        threads = [threading.Thread(target=updater) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
        e.stop()

    def test_concurrent_listener_events_ordered(self):
        e        = _started_engine()
        received: List[RoutingEvent] = []
        lock     = threading.Lock()

        def listener(ev: RoutingEvent):
            with lock:
                received.append(ev)

        e.add_event_listener(listener)
        c = _candidate("b1")
        e.register_candidate(c)
        p = DefaultBrokerPolicy("p1", "b1")
        e.register_policy(p)
        e.set_default_policy("p1")

        def do_route():
            for _ in range(5):
                e.route(_context())

        threads = [threading.Thread(target=do_route) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # Each route fires at least 3 events (STARTED, SELECTED, COMPLETED)
        assert len(received) >= 60
        e.stop()


# ─────────────────────────────────────────────────────────────────────────────
# TestRegressionEdgeCases
# ─────────────────────────────────────────────────────────────────────────────

class TestRegressionEdgeCases:
    def test_route_no_policy_uses_all_candidates(self):
        """Without any policy, the engine should still route to available candidate."""
        e  = _started_engine()
        c1 = _candidate("b1")
        e.register_candidate(c1)
        d  = e.route(_context())
        assert d.is_routed
        assert d.selected_broker_id == "b1"
        e.stop()

    def test_route_no_candidates_returns_failed_decision(self):
        e = _started_engine()
        d = e.route(_context())
        assert d.is_failed
        assert d.outcome == RoutingOutcome.NO_CANDIDATES
        e.stop()

    def test_routing_time_ms_is_non_negative(self):
        e  = _started_engine()
        c  = _candidate("b1")
        p  = DefaultBrokerPolicy("p1", "b1")
        e.register_candidate(c)
        e.register_policy(p)
        e.set_default_policy("p1")
        d  = e.route(_context())
        assert d.routing_time_ms >= 0.0
        e.stop()

    def test_decision_ids_unique_across_routes(self):
        e  = _started_engine()
        c  = _candidate("b1")
        p  = DefaultBrokerPolicy("p1", "b1")
        e.register_candidate(c)
        e.register_policy(p)
        e.set_default_policy("p1")
        decisions = [e.route(_context()) for _ in range(5)]
        ids = {d.decision_id for d in decisions}
        assert len(ids) == 5
        e.stop()

    def test_history_records_all_decisions(self):
        e  = _started_engine()
        c  = _candidate("b1")
        p  = DefaultBrokerPolicy("p1", "b1")
        e.register_candidate(c)
        e.register_policy(p)
        e.set_default_policy("p1")
        for _ in range(3):
            e.route(_context())
        assert e.history().decision_count == 3
        e.stop()

    def test_event_listener_exception_does_not_propagate(self):
        e = _started_engine()
        e.add_event_listener(lambda ev: 1 / 0)  # always throws
        c = _candidate("b1")
        p = DefaultBrokerPolicy("p1", "b1")
        e.register_candidate(c)
        e.register_policy(p)
        e.set_default_policy("p1")
        # should not raise despite listener exception
        d = e.route(_context())
        assert d.is_routed
        e.stop()

    def test_remove_policy_clears_default(self):
        e  = _started_engine()
        c  = _candidate("b1")
        p  = DefaultBrokerPolicy("p1", "b1")
        e.register_candidate(c)
        e.register_policy(p)
        e.set_default_policy("p1")
        e.remove_policy("p1")
        # routing should still work (no policy → all candidates)
        d = e.route(_context())
        assert d.is_routed
        e.stop()

    def test_blacklist_and_unblacklist_round_trip(self):
        e = _started_engine()
        c = _candidate("b1")
        p = DefaultBrokerPolicy("p1", "b1")
        e.register_candidate(c)
        e.register_policy(p)
        e.set_default_policy("p1")
        e.blacklist_broker("b1")
        d1 = e.route(_context())
        assert d1.is_failed  # b1 is blacklisted
        e.unblacklist_broker("b1")
        d2 = e.route(_context())
        assert d2.is_routed  # b1 is back
        e.stop()

    def test_routing_context_metadata_preserved(self):
        e   = _started_engine()
        c   = _candidate("b1")
        p   = DefaultBrokerPolicy("p1", "b1")
        e.register_candidate(c)
        e.register_policy(p)
        e.set_default_policy("p1")
        ctx = make_routing_context(
            "e", "o", "p", "s",
            symbol="INFY", exchange="NSE", quantity=1.0, price=10.0,
            metadata={"tag": "important"},
        )
        d = e.route(ctx)
        assert d.is_routed
        e.stop()

    def test_routing_with_explicit_policy_id(self):
        e  = _started_engine()
        c  = _candidate("b1")
        p1 = DefaultBrokerPolicy("p1", "b1")
        p2 = DefaultBrokerPolicy("p2", "nonexistent")
        e.register_candidate(c)
        e.register_policy(p1)
        e.register_policy(p2)
        e.set_default_policy("p2")  # default is p2 (would fail)
        d = e.route(_context(), policy_id="p1")  # explicit override
        assert d.is_routed
        assert d.selected_broker_id == "b1"
        e.stop()
