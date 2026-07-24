"""
tests/unit/integration/test_integration_engine_m2.py
-----------------------------------------------------
C15 M2 — Integration Engine test suite.

Covers all 23 source files in iios/integration/engine/.
Target: 95%+ coverage.
"""
from __future__ import annotations

import threading
import time
from typing import List

import pytest


# ════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════


def _make_engine(started: bool = True):
    from iios.integration.engine import (
        AdapterDescriptor, AdapterType,
        ConnectorDescriptor, ConnectorType,
        IntegrationEngine,
        ProtocolDescriptor, ProtocolType,
    )
    eng = IntegrationEngine()
    if started:
        eng.initialize()
        eng.register_connector(
            ConnectorDescriptor.create(ConnectorType.REST_API, "REST Connector")
        )
        eng.register_adapter(
            AdapterDescriptor.create(AdapterType.REST, ConnectorType.REST_API, "REST Adapter")
        )
        eng.register_protocol(
            ProtocolDescriptor.create(ProtocolType.HTTPS, "HTTPS Protocol")
        )
    return eng


def _make_request(connector_type=None, protocol_type=None):
    from iios.integration.engine import (
        ConnectorType, IntegrationRequest, ProtocolType,
    )
    return IntegrationRequest.create(
        connector_type or ConnectorType.REST_API,
        protocol_type=protocol_type or ProtocolType.HTTPS,
    )


def _make_manager(started: bool = True):
    from iios.integration.engine import IntegrationManager
    mgr = IntegrationManager()
    if started:
        mgr.start()
    return mgr


# ════════════════════════════════════════════════════════════════════════
# 1. Constants
# ════════════════════════════════════════════════════════════════════════


class TestConstants:
    def test_engine_state_count(self):
        from iios.integration.engine import IntegrationEngineState
        assert len(IntegrationEngineState) == 11

    def test_connector_type_count(self):
        from iios.integration.engine import ConnectorType
        assert len(ConnectorType) == 18

    def test_adapter_type_count(self):
        from iios.integration.engine import AdapterType
        assert len(AdapterType) == 17

    def test_protocol_type_count(self):
        from iios.integration.engine import ProtocolType
        assert len(ProtocolType) == 13

    def test_dispatch_mode_count(self):
        from iios.integration.engine import DispatchMode
        assert len(DispatchMode) == 7

    def test_event_type_count(self):
        from iios.integration.engine import IntegrationEngineEventType
        assert len(IntegrationEngineEventType) == 9

    def test_validation_check_count(self):
        from iios.integration.engine import EngineValidationCheck
        assert len(EngineValidationCheck) == 7

    def test_pipeline_stage_count(self):
        from iios.integration.engine import PipelineStage
        assert len(PipelineStage) == 10

    def test_pipeline_stage_order_length(self):
        from iios.integration.engine import PIPELINE_STAGE_ORDER
        assert len(PIPELINE_STAGE_ORDER) == 10

    def test_system_id(self):
        from iios.integration.engine import ENGINE_SYSTEM_ID
        assert "integration" in ENGINE_SYSTEM_ID

    def test_default_limits(self):
        from iios.integration.engine import (
            DEFAULT_MAX_CONNECTORS,
            DEFAULT_MAX_ADAPTERS,
            DEFAULT_MAX_PROTOCOLS,
            DEFAULT_QUEUE_SIZE,
        )
        assert DEFAULT_MAX_CONNECTORS  >= 100
        assert DEFAULT_MAX_ADAPTERS    >= 100
        assert DEFAULT_MAX_PROTOCOLS   >= 50
        assert DEFAULT_QUEUE_SIZE      >= 1_000


# ════════════════════════════════════════════════════════════════════════
# 2. Exceptions
# ════════════════════════════════════════════════════════════════════════


class TestExceptions:
    def test_base_ien_000(self):
        from iios.integration.engine import IntegrationEngineError
        exc = IntegrationEngineError("test")
        assert "IEN-000" in exc.error_code

    def test_not_ready_ien_001(self):
        from iios.integration.engine import IntegrationEngineNotReadyError
        exc = IntegrationEngineNotReadyError()
        assert "IEN-001" in exc.error_code

    def test_connector_not_found_ien_002(self):
        from iios.integration.engine import ConnectorNotFoundError
        exc = ConnectorNotFoundError("rest_api")
        assert exc.connector_id == "rest_api"
        assert "IEN-002" in exc.error_code

    def test_adapter_not_found_ien_003(self):
        from iios.integration.engine import AdapterNotFoundError
        exc = AdapterNotFoundError("rest")
        assert exc.adapter_id == "rest"
        assert "IEN-003" in exc.error_code

    def test_protocol_not_registered_ien_004(self):
        from iios.integration.engine import ProtocolNotRegisteredError
        exc = ProtocolNotRegisteredError("https")
        assert exc.protocol_type == "https"
        assert "IEN-004" in exc.error_code

    def test_request_validation_ien_005(self):
        from iios.integration.engine import IntegrationRequestValidationError
        exc = IntegrationRequestValidationError("bad", failed_checks=["connector_validity"])
        assert "connector_validity" in exc.failed_checks

    def test_dispatch_error_ien_006(self):
        from iios.integration.engine import IntegrationDispatchError
        exc = IntegrationDispatchError("dispatch failed", request_id="req-001")
        assert exc.request_id == "req-001"

    def test_session_error_ien_007(self):
        from iios.integration.engine import IntegrationSessionError
        exc = IntegrationSessionError("session error")
        assert "IEN-007" in exc.error_code

    def test_hierarchy(self):
        from iios.integration.engine import (
            IntegrationEngineError,
            ConnectorNotFoundError,
        )
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(ConnectorNotFoundError, IntegrationEngineError)
        assert issubclass(IntegrationEngineError, IIOSError)


# ════════════════════════════════════════════════════════════════════════
# 3. IntegrationRequest
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationRequest:
    def test_create(self):
        from iios.integration.engine import ConnectorType, IntegrationRequest
        req = IntegrationRequest.create(ConnectorType.REST_API, endpoint="https://x.com")
        assert req.connector_type == ConnectorType.REST_API
        assert req.endpoint       == "https://x.com"
        assert req.request_id.startswith("req-")

    def test_frozen(self):
        req = _make_request()
        with pytest.raises((AttributeError, TypeError)):
            req.endpoint = "changed"  # type: ignore

    def test_to_dict_from_dict(self):
        from iios.integration.engine import IntegrationRequest
        req  = _make_request()
        req2 = IntegrationRequest.from_dict(req.to_dict())
        assert req2.request_id    == req.request_id
        assert req2.connector_type == req.connector_type

    def test_correlation_and_trace_auto_generated(self):
        req = _make_request()
        assert req.correlation_id
        assert req.trace_id

    def test_priority_default(self):
        from iios.integration.engine import DEFAULT_PRIORITY
        req = _make_request()
        assert req.priority == DEFAULT_PRIORITY


# ════════════════════════════════════════════════════════════════════════
# 4. IntegrationResponse
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationResponse:
    def test_success_for(self):
        from iios.integration.engine import IntegrationResponseStatus
        req  = _make_request()
        resp = __import__("iios.integration.engine", fromlist=["IntegrationResponse"]).IntegrationResponse.success_for(
            req, "s-001", {"key": "val"}, 50.0
        )
        assert resp.is_success
        assert resp.status == IntegrationResponseStatus.SUCCESS

    def test_failure_for(self):
        req  = _make_request()
        from iios.integration.engine import IntegrationResponse
        resp = IntegrationResponse.failure_for(req, "s-001", "something broke", 10.0)
        assert resp.is_failure
        assert "something broke" in resp.error_message

    def test_frozen(self):
        req  = _make_request()
        from iios.integration.engine import IntegrationResponse
        resp = IntegrationResponse.success_for(req, "s-001")
        with pytest.raises((AttributeError, TypeError)):
            resp.session_id = "other"  # type: ignore

    def test_to_dict(self):
        req  = _make_request()
        from iios.integration.engine import IntegrationResponse
        resp = IntegrationResponse.success_for(req, "s-001")
        d    = resp.to_dict()
        assert "response_id" in d
        assert "status"      in d


# ════════════════════════════════════════════════════════════════════════
# 5. IntegrationEngineContext
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationContext:
    def test_create(self):
        from iios.integration.engine import IntegrationEngineContext
        req = _make_request()
        ctx = IntegrationEngineContext.create(req, "s-001")
        assert ctx.request_id  == req.request_id
        assert ctx.session_id  == "s-001"
        assert ctx.context_id.startswith("ectx-")

    def test_frozen(self):
        from iios.integration.engine import IntegrationEngineContext
        req = _make_request()
        ctx = IntegrationEngineContext.create(req, "s-001")
        with pytest.raises((AttributeError, TypeError)):
            ctx.session_id = "x"  # type: ignore

    def test_to_dict(self):
        from iios.integration.engine import IntegrationEngineContext
        req = _make_request()
        ctx = IntegrationEngineContext.create(req, "s-001")
        d   = ctx.to_dict()
        assert "context_id"  in d
        assert "engine_id"   in d


# ════════════════════════════════════════════════════════════════════════
# 6. Engine Lifecycle
# ════════════════════════════════════════════════════════════════════════


class TestEngineLifecycle:
    def test_initial_state_idle_after_initialize(self):
        from iios.integration.engine import IntegrationEngine, IntegrationEngineState
        eng = IntegrationEngine()
        eng.initialize()
        assert eng.state == IntegrationEngineState.IDLE

    def test_stop_transitions_to_stopped(self):
        from iios.integration.engine import IntegrationEngine, IntegrationEngineState
        eng = IntegrationEngine()
        eng.initialize()
        eng.stop()
        assert eng.state == IntegrationEngineState.STOPPED

    def test_dispatch_on_stopped_raises(self):
        from iios.integration.engine import IntegrationEngineNotReadyError
        eng = _make_engine()
        eng.stop()
        with pytest.raises(IntegrationEngineNotReadyError):
            eng.dispatch(_make_request())

    def test_configure_accepted(self):
        eng = _make_engine()
        eng.configure({"timeout": 30})   # should not raise

    def test_connect_accepted(self):
        eng = _make_engine()
        eng.connect()   # should not raise

    def test_disconnect_accepted(self):
        eng = _make_engine()
        eng.disconnect()   # should not raise

    def test_manager_start_stop(self):
        from iios.integration.engine import IntegrationManager
        mgr = IntegrationManager()
        mgr.start()
        assert mgr.is_started
        mgr.stop()
        assert not mgr.is_started

    def test_manager_double_start(self):
        from iios.integration.engine import IntegrationManager
        mgr = IntegrationManager()
        mgr.start()
        mgr.start()   # should not raise or error
        mgr.stop()


# ════════════════════════════════════════════════════════════════════════
# 7. Connector Management
# ════════════════════════════════════════════════════════════════════════


class TestConnectorManagement:
    def test_register_and_get(self):
        from iios.integration.engine import (
            ConnectorDescriptor, ConnectorManager, ConnectorType,
        )
        mgr  = ConnectorManager()
        desc = ConnectorDescriptor.create(ConnectorType.KAFKA, "Kafka Connector")
        mgr.register(desc)
        assert mgr.get(desc.connector_id) is desc

    def test_first_by_type(self):
        from iios.integration.engine import (
            ConnectorDescriptor, ConnectorManager, ConnectorType,
        )
        mgr  = ConnectorManager()
        desc = ConnectorDescriptor.create(ConnectorType.WEBSOCKET, "WS")
        mgr.register(desc)
        found = mgr.first_by_type(ConnectorType.WEBSOCKET)
        assert found is desc

    def test_supports(self):
        from iios.integration.engine import (
            ConnectorDescriptor, ConnectorManager, ConnectorType,
        )
        mgr  = ConnectorManager()
        desc = ConnectorDescriptor.create(ConnectorType.DATABASE, "DB")
        mgr.register(desc)
        assert mgr.supports(ConnectorType.DATABASE)
        assert not mgr.supports(ConnectorType.GRPC)

    def test_deregister(self):
        from iios.integration.engine import (
            ConnectorDescriptor, ConnectorManager, ConnectorType,
        )
        mgr  = ConnectorManager()
        desc = ConnectorDescriptor.create(ConnectorType.GRPC, "gRPC")
        mgr.register(desc)
        assert mgr.deregister(desc.connector_id)
        assert mgr.get(desc.connector_id) is None

    def test_capacity_error(self):
        from iios.integration.engine import (
            ConnectorDescriptor, ConnectorManager, ConnectorType,
            ConnectorRegistrationError,
        )
        mgr = ConnectorManager(max_connectors=2)
        mgr.register(ConnectorDescriptor.create(ConnectorType.REST_API, "R1"))
        mgr.register(ConnectorDescriptor.create(ConnectorType.GRPC, "R2"))
        with pytest.raises(ConnectorRegistrationError):
            mgr.register(ConnectorDescriptor.create(ConnectorType.KAFKA, "R3"))

    def test_get_or_raise(self):
        from iios.integration.engine import (
            ConnectorManager, ConnectorNotFoundError,
        )
        mgr = ConnectorManager()
        with pytest.raises(ConnectorNotFoundError):
            mgr.get_or_raise("nonexistent")

    def test_descriptor_frozen(self):
        from iios.integration.engine import ConnectorDescriptor, ConnectorType
        desc = ConnectorDescriptor.create(ConnectorType.REST_API, "R")
        with pytest.raises((AttributeError, TypeError)):
            desc.name = "X"  # type: ignore

    def test_descriptor_to_dict(self):
        from iios.integration.engine import ConnectorDescriptor, ConnectorType
        desc = ConnectorDescriptor.create(ConnectorType.KAFKA, "K", capabilities=["publish"])
        d    = desc.to_dict()
        assert d["connector_type"] == "kafka"
        assert "publish" in d["capabilities"]

    def test_count_and_clear(self):
        from iios.integration.engine import (
            ConnectorDescriptor, ConnectorManager, ConnectorType,
        )
        mgr = ConnectorManager()
        mgr.register(ConnectorDescriptor.create(ConnectorType.REST_API, "R"))
        assert mgr.count() == 1
        mgr.clear()
        assert mgr.count() == 0


# ════════════════════════════════════════════════════════════════════════
# 8. Adapter Management
# ════════════════════════════════════════════════════════════════════════


class TestAdapterManagement:
    def test_register_and_for_connector(self):
        from iios.integration.engine import (
            AdapterDescriptor, AdapterManager, AdapterType, ConnectorType,
        )
        mgr  = AdapterManager()
        desc = AdapterDescriptor.create(AdapterType.REST, ConnectorType.REST_API, "REST Adapter")
        mgr.register(desc)
        found = mgr.first_for_connector(ConnectorType.REST_API)
        assert found is desc

    def test_by_type(self):
        from iios.integration.engine import (
            AdapterDescriptor, AdapterManager, AdapterType, ConnectorType,
        )
        mgr  = AdapterManager()
        desc = AdapterDescriptor.create(AdapterType.KAFKA, ConnectorType.KAFKA, "Kafka Adapter")
        mgr.register(desc)
        by_type = mgr.by_type(AdapterType.KAFKA)
        assert desc in by_type

    def test_deregister(self):
        from iios.integration.engine import (
            AdapterDescriptor, AdapterManager, AdapterType, ConnectorType,
        )
        mgr  = AdapterManager()
        desc = AdapterDescriptor.create(AdapterType.REST, ConnectorType.REST_API, "R")
        mgr.register(desc)
        assert mgr.deregister(desc.adapter_id)
        assert mgr.get(desc.adapter_id) is None

    def test_supports_connector(self):
        from iios.integration.engine import (
            AdapterDescriptor, AdapterManager, AdapterType, ConnectorType,
        )
        mgr  = AdapterManager()
        mgr.register(
            AdapterDescriptor.create(AdapterType.GRPC, ConnectorType.GRPC, "gRPC Adapter")
        )
        assert mgr.supports_connector(ConnectorType.GRPC)
        assert not mgr.supports_connector(ConnectorType.KAFKA)

    def test_get_or_raise(self):
        from iios.integration.engine import AdapterManager, AdapterNotFoundError
        mgr = AdapterManager()
        with pytest.raises(AdapterNotFoundError):
            mgr.get_or_raise("nonexistent")

    def test_descriptor_frozen(self):
        from iios.integration.engine import AdapterDescriptor, AdapterType, ConnectorType
        desc = AdapterDescriptor.create(AdapterType.REST, ConnectorType.REST_API, "R")
        with pytest.raises((AttributeError, TypeError)):
            desc.name = "X"  # type: ignore

    def test_count_clear(self):
        from iios.integration.engine import (
            AdapterDescriptor, AdapterManager, AdapterType, ConnectorType,
        )
        mgr = AdapterManager()
        mgr.register(
            AdapterDescriptor.create(AdapterType.REST, ConnectorType.REST_API, "R")
        )
        assert mgr.count() == 1
        mgr.clear()
        assert mgr.count() == 0


# ════════════════════════════════════════════════════════════════════════
# 9. Protocol Validation
# ════════════════════════════════════════════════════════════════════════


class TestProtocolValidation:
    def test_register_and_lookup(self):
        from iios.integration.engine import (
            ProtocolDescriptor, ProtocolRegistry, ProtocolType,
        )
        reg  = ProtocolRegistry()
        desc = ProtocolDescriptor.create(ProtocolType.HTTPS, "HTTPS")
        reg.register(desc)
        assert reg.is_registered(ProtocolType.HTTPS)

    def test_first_by_type(self):
        from iios.integration.engine import (
            ProtocolDescriptor, ProtocolRegistry, ProtocolType,
        )
        reg  = ProtocolRegistry()
        desc = ProtocolDescriptor.create(ProtocolType.GRPC, "gRPC Protocol")
        reg.register(desc)
        found = reg.first_by_type(ProtocolType.GRPC)
        assert found is desc

    def test_supports_connector(self):
        from iios.integration.engine import (
            ConnectorType, ProtocolDescriptor, ProtocolRegistry, ProtocolType,
        )
        reg  = ProtocolRegistry()
        desc = ProtocolDescriptor.create(
            ProtocolType.AMQP, "AMQP",
            supported_connector_types=[ConnectorType.RABBITMQ],
        )
        reg.register(desc)
        assert reg.supports_connector(ProtocolType.AMQP, ConnectorType.RABBITMQ)
        assert not reg.supports_connector(ProtocolType.AMQP, ConnectorType.KAFKA)

    def test_protocol_supports_all_when_empty(self):
        from iios.integration.engine import (
            ConnectorType, ProtocolDescriptor, ProtocolType,
        )
        desc = ProtocolDescriptor.create(ProtocolType.INTERNAL, "Internal")
        # No supported_connector_types → supports all
        assert desc.supports_connector(ConnectorType.REST_API)
        assert desc.supports_connector(ConnectorType.KAFKA)

    def test_deregister(self):
        from iios.integration.engine import (
            ProtocolDescriptor, ProtocolRegistry, ProtocolType,
        )
        reg  = ProtocolRegistry()
        desc = ProtocolDescriptor.create(ProtocolType.JDBC, "JDBC")
        reg.register(desc)
        assert reg.deregister(desc.protocol_id)
        assert not reg.is_registered(ProtocolType.JDBC)

    def test_descriptor_frozen(self):
        from iios.integration.engine import ProtocolDescriptor, ProtocolType
        desc = ProtocolDescriptor.create(ProtocolType.HTTP, "HTTP")
        with pytest.raises((AttributeError, TypeError)):
            desc.name = "X"  # type: ignore

    def test_descriptor_to_dict(self):
        from iios.integration.engine import ProtocolDescriptor, ProtocolType, ConnectorType
        desc = ProtocolDescriptor.create(
            ProtocolType.HTTPS, "HTTPS",
            supported_connector_types=[ConnectorType.REST_API],
        )
        d = desc.to_dict()
        assert "rest_api" in d["supported_connector_types"]


# ════════════════════════════════════════════════════════════════════════
# 10. IntegrationEngineRegistry (unified facade)
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationRegistry:
    def test_summary(self):
        from iios.integration.engine import (
            AdapterDescriptor, AdapterType,
            ConnectorDescriptor, ConnectorType,
            IntegrationEngineRegistry,
            ProtocolDescriptor, ProtocolType,
        )
        reg = IntegrationEngineRegistry()
        reg.register_connector(
            ConnectorDescriptor.create(ConnectorType.REST_API, "R")
        )
        reg.register_adapter(
            AdapterDescriptor.create(AdapterType.REST, ConnectorType.REST_API, "A")
        )
        reg.register_protocol(
            ProtocolDescriptor.create(ProtocolType.HTTPS, "P")
        )
        s = reg.summary()
        assert s["connector_count"] == 1
        assert s["adapter_count"]   == 1
        assert s["protocol_count"]  == 1

    def test_has_methods(self):
        from iios.integration.engine import (
            ConnectorDescriptor, ConnectorType,
            IntegrationEngineRegistry,
        )
        reg = IntegrationEngineRegistry()
        assert not reg.has_connector(ConnectorType.KAFKA)
        reg.register_connector(
            ConnectorDescriptor.create(ConnectorType.KAFKA, "K")
        )
        assert reg.has_connector(ConnectorType.KAFKA)

    def test_get_connector_none_when_not_registered(self):
        from iios.integration.engine import IntegrationEngineRegistry, ConnectorType
        reg = IntegrationEngineRegistry()
        assert reg.get_connector(ConnectorType.REST_API) is None

    def test_clear(self):
        from iios.integration.engine import (
            ConnectorDescriptor, ConnectorType,
            IntegrationEngineRegistry,
        )
        reg = IntegrationEngineRegistry()
        reg.register_connector(
            ConnectorDescriptor.create(ConnectorType.REST_API, "R")
        )
        reg.clear()
        assert reg.summary()["connector_count"] == 0


# ════════════════════════════════════════════════════════════════════════
# 11. Workflow Orchestration (dispatch)
# ════════════════════════════════════════════════════════════════════════


class TestWorkflowOrchestration:
    def test_successful_dispatch(self):
        eng  = _make_engine()
        req  = _make_request()
        resp = eng.dispatch(req)
        assert resp.is_success
        assert resp.request_id == req.request_id

    def test_response_has_session_id(self):
        eng  = _make_engine()
        req  = _make_request()
        resp = eng.dispatch(req)
        assert resp.session_id

    def test_response_has_latency(self):
        eng  = _make_engine()
        req  = _make_request()
        resp = eng.dispatch(req)
        assert resp.latency_ms >= 0

    def test_dispatch_without_connector_returns_failure(self):
        from iios.integration.engine import IntegrationEngine, ConnectorType
        eng = IntegrationEngine()
        eng.initialize()
        # No connectors/adapters/protocols registered
        req  = _make_request(ConnectorType.KAFKA)
        resp = eng.dispatch(req)
        assert resp.is_failure

    def test_dispatch_batch(self):
        eng  = _make_engine()
        reqs = [_make_request() for _ in range(5)]
        responses = eng.dispatch_batch(reqs)
        assert len(responses) == 5
        assert all(r.is_success for r in responses)

    def test_query_cached_response(self):
        eng  = _make_engine()
        req  = _make_request()
        resp = eng.dispatch(req)
        cached = eng.query(req.request_id)
        assert cached is resp

    def test_query_unknown_request_returns_none(self):
        eng = _make_engine()
        assert eng.query("nonexistent-req-id") is None

    def test_stats_increment_after_dispatch(self):
        eng  = _make_engine()
        eng.dispatch(_make_request())
        r = eng.stats.report()
        assert r.integration_sessions  >= 1
        assert r.connectors_loaded     >= 1
        assert r.adapters_loaded       >= 1

    def test_history_records_request_and_response(self):
        eng  = _make_engine()
        req  = _make_request()
        eng.dispatch(req)
        assert eng.history.request_count()  >= 1
        assert eng.history.response_count() >= 1

    def test_manager_submit_request(self):
        mgr  = _make_manager(started=False)
        from iios.integration.engine import (
            AdapterDescriptor, AdapterType,
            ConnectorDescriptor, ConnectorType,
            ProtocolDescriptor, ProtocolType,
        )
        mgr.start()
        mgr.register_connector(
            ConnectorDescriptor.create(ConnectorType.REST_API, "R")
        )
        mgr.register_adapter(
            AdapterDescriptor.create(AdapterType.REST, ConnectorType.REST_API, "A")
        )
        mgr.register_protocol(
            ProtocolDescriptor.create(ProtocolType.HTTPS, "P")
        )
        req  = _make_request()
        resp = mgr.submit_request(req)
        assert resp.is_success
        mgr.stop()


# ════════════════════════════════════════════════════════════════════════
# 12. Scheduler
# ════════════════════════════════════════════════════════════════════════


class TestScheduler:
    def test_submit_and_dequeue(self):
        from iios.integration.engine import IntegrationScheduler, SchedulerMode
        sched = IntegrationScheduler()
        req   = _make_request()
        job_id = sched.submit(req, mode=SchedulerMode.IMMEDIATE, priority=5)
        job    = sched.next()
        assert job is not None
        assert job.job_id    == job_id
        assert job.request.request_id == req.request_id

    def test_priority_ordering(self):
        from iios.integration.engine import IntegrationScheduler, SchedulerMode
        sched = IntegrationScheduler()
        r_low  = _make_request()
        r_high = _make_request()
        sched.submit(r_low,  mode=SchedulerMode.PRIORITY, priority=9)
        sched.submit(r_high, mode=SchedulerMode.PRIORITY, priority=1)
        job = sched.next()
        assert job.request.request_id == r_high.request_id  # priority 1 wins

    def test_cancel_skips_job(self):
        from iios.integration.engine import IntegrationScheduler
        sched  = IntegrationScheduler()
        req    = _make_request()
        job_id = sched.submit(req, priority=5)
        sched.cancel(job_id)
        job = sched.next()
        assert job is None   # cancelled job is skipped

    def test_queue_size(self):
        from iios.integration.engine import IntegrationScheduler
        sched = IntegrationScheduler()
        for _ in range(3):
            sched.submit(_make_request())
        assert sched.queue_size() == 3

    def test_peek(self):
        from iios.integration.engine import IntegrationScheduler
        sched = IntegrationScheduler()
        req   = _make_request()
        sched.submit(req)
        peeked = sched.peek()
        assert peeked is not None
        # peek doesn't remove
        assert sched.queue_size() == 1

    def test_clear(self):
        from iios.integration.engine import IntegrationScheduler
        sched = IntegrationScheduler()
        sched.submit(_make_request())
        sched.clear()
        assert sched.queue_size() == 0
        assert sched.next() is None

    def test_process_scheduled_via_engine(self):
        eng = _make_engine()
        eng.schedule(_make_request())
        resp = eng.process_scheduled()
        assert resp is not None
        assert resp.is_success

    def test_process_scheduled_empty_returns_none(self):
        eng = _make_engine()
        assert eng.process_scheduled() is None

    def test_scheduled_job_to_dict(self):
        from iios.integration.engine import IntegrationScheduler, SchedulerMode
        sched  = IntegrationScheduler()
        job_id = sched.submit(_make_request(), mode=SchedulerMode.BATCH)
        job    = sched.next()
        d      = job.to_dict()
        assert d["job_id"] == job_id
        assert d["mode"]   == "batch"

    def test_all_scheduler_modes(self):
        from iios.integration.engine import IntegrationScheduler, SchedulerMode
        sched = IntegrationScheduler()
        for mode in SchedulerMode:
            jid = sched.submit(_make_request(), mode=mode)
            job = sched.next()
            assert job.mode == mode


# ════════════════════════════════════════════════════════════════════════
# 13. Validation (7 checks)
# ════════════════════════════════════════════════════════════════════════


class TestValidation:
    def _registry_with_all(self):
        from iios.integration.engine import (
            AdapterDescriptor, AdapterType,
            ConnectorDescriptor, ConnectorType,
            IntegrationEngineRegistry,
            ProtocolDescriptor, ProtocolType,
        )
        reg = IntegrationEngineRegistry()
        reg.register_connector(ConnectorDescriptor.create(ConnectorType.REST_API, "R"))
        reg.register_adapter(AdapterDescriptor.create(AdapterType.REST, ConnectorType.REST_API, "A"))
        reg.register_protocol(ProtocolDescriptor.create(ProtocolType.HTTPS, "P"))
        return reg

    def test_all_checks_pass(self):
        from iios.integration.engine import IntegrationEngineValidator
        v    = IntegrationEngineValidator()
        reg  = self._registry_with_all()
        req  = _make_request()
        rpt  = v.validate(req, reg)
        assert rpt.passed
        assert rpt.failed_checks == []

    def test_connector_validity_fails(self):
        from iios.integration.engine import (
            IntegrationEngineValidator, IntegrationEngineRegistry,
            ConnectorType, EngineValidationCheck,
        )
        v   = IntegrationEngineValidator()
        reg = IntegrationEngineRegistry()
        # No connector registered
        req = _make_request(ConnectorType.GRPC)
        rpt = v.validate(req, reg)
        assert not rpt.passed
        assert EngineValidationCheck.CONNECTOR_VALIDITY.value in rpt.failed_checks

    def test_adapter_compatibility_fails(self):
        from iios.integration.engine import (
            IntegrationEngineValidator,
            IntegrationEngineRegistry,
            ConnectorDescriptor, ConnectorType,
            EngineValidationCheck,
            ProtocolDescriptor, ProtocolType,
        )
        v = IntegrationEngineValidator()
        reg = IntegrationEngineRegistry()
        reg.register_connector(ConnectorDescriptor.create(ConnectorType.REST_API, "R"))
        reg.register_protocol(ProtocolDescriptor.create(ProtocolType.HTTPS, "P"))
        # No adapter
        req = _make_request()
        rpt = v.validate(req, reg)
        assert EngineValidationCheck.ADAPTER_COMPATIBILITY.value in rpt.failed_checks

    def test_protocol_compatibility_fails(self):
        from iios.integration.engine import (
            IntegrationEngineValidator,
            IntegrationEngineRegistry,
            ConnectorDescriptor, ConnectorType,
            AdapterDescriptor, AdapterType,
            EngineValidationCheck,
        )
        v = IntegrationEngineValidator()
        reg = IntegrationEngineRegistry()
        reg.register_connector(ConnectorDescriptor.create(ConnectorType.REST_API, "R"))
        reg.register_adapter(AdapterDescriptor.create(AdapterType.REST, ConnectorType.REST_API, "A"))
        # No protocol
        req = _make_request()
        rpt = v.validate(req, reg)
        assert EngineValidationCheck.PROTOCOL_COMPATIBILITY.value in rpt.failed_checks

    def test_lifecycle_consistency_priority_out_of_range(self):
        from iios.integration.engine import (
            IntegrationEngineValidator, IntegrationRequest, ConnectorType,
            EngineValidationCheck,
        )
        v   = IntegrationEngineValidator()
        reg = self._registry_with_all()
        req = IntegrationRequest.create(ConnectorType.REST_API, priority=99)
        rpt = v.validate(req, reg)
        assert not rpt.passed
        assert EngineValidationCheck.LIFECYCLE_CONSISTENCY.value in rpt.failed_checks

    def test_validation_report_to_dict(self):
        from iios.integration.engine import IntegrationEngineValidator
        v   = IntegrationEngineValidator()
        reg = self._registry_with_all()
        req = _make_request()
        rpt = v.validate(req, reg)
        d   = rpt.to_dict()
        assert "passed"   in d
        assert "results"  in d

    def test_engine_validate_method(self):
        from iios.integration.engine import IntegrationEngineState
        eng = _make_engine()
        req = _make_request()
        rpt = eng.validate(req)
        assert rpt.passed
        # engine returns to IDLE after validate
        assert eng.state == IntegrationEngineState.IDLE


# ════════════════════════════════════════════════════════════════════════
# 14. Statistics (9 counters)
# ════════════════════════════════════════════════════════════════════════


class TestStatistics:
    def test_all_nine_counters(self):
        from iios.integration.engine import IntegrationEngineStatistics
        stats = IntegrationEngineStatistics()
        stats.record_session()
        stats.record_connector_loaded()
        stats.record_adapter_loaded()
        stats.record_message_routed()
        stats.record_api_request()
        stats.record_event_processed()
        stats.record_response_time(100.0)
        stats.record_processing_time(90.0)
        stats.record_availability_tick(True)

        r = stats.report()
        assert r.integration_sessions       == 1
        assert r.connectors_loaded          == 1
        assert r.adapters_loaded            == 1
        assert r.messages_routed            == 1
        assert r.api_requests               == 1
        assert r.events_processed           == 1
        assert r.average_response_time_ms   == 100.0
        assert r.average_processing_time_ms == 90.0
        assert r.integration_availability   == 1.0

    def test_availability_degraded(self):
        from iios.integration.engine import IntegrationEngineStatistics
        stats = IntegrationEngineStatistics()
        stats.record_availability_tick(True)
        stats.record_availability_tick(False)
        r = stats.report()
        assert r.integration_availability == 0.5

    def test_reset(self):
        from iios.integration.engine import IntegrationEngineStatistics
        stats = IntegrationEngineStatistics()
        stats.record_session()
        stats.reset()
        r = stats.report()
        assert r.integration_sessions == 0

    def test_report_to_dict(self):
        from iios.integration.engine import IntegrationEngineStatistics
        stats = IntegrationEngineStatistics()
        d = stats.report().to_dict()
        assert "integration_sessions"       in d
        assert "integration_availability"   in d
        assert "average_response_time_ms"   in d

    def test_no_responses_avg_is_zero(self):
        from iios.integration.engine import IntegrationEngineStatistics
        stats = IntegrationEngineStatistics()
        r = stats.report()
        assert r.average_response_time_ms   == 0.0
        assert r.average_processing_time_ms == 0.0

    def test_availability_defaults_one_when_no_ticks(self):
        from iios.integration.engine import IntegrationEngineStatistics
        stats = IntegrationEngineStatistics()
        r = stats.report()
        assert r.integration_availability == 1.0


# ════════════════════════════════════════════════════════════════════════
# 15. History
# ════════════════════════════════════════════════════════════════════════


class TestHistory:
    def test_record_and_retrieve_request(self):
        from iios.integration.engine import IntegrationEngineHistory
        h   = IntegrationEngineHistory()
        req = _make_request()
        h.record_request(req)
        assert h.get_request(req.request_id) is req

    def test_record_and_retrieve_response(self):
        from iios.integration.engine import IntegrationEngineHistory, IntegrationResponse
        h    = IntegrationEngineHistory()
        req  = _make_request()
        resp = IntegrationResponse.success_for(req, "s-001")
        h.record_response(resp)
        assert h.get_response(resp.response_id) is resp

    def test_by_session(self):
        from iios.integration.engine import IntegrationEngineHistory, IntegrationResponse
        h    = IntegrationEngineHistory()
        req  = _make_request()
        resp = IntegrationResponse.success_for(req, "s-xyz")
        h.record_response(resp)
        found = h.by_session("s-xyz")
        assert resp in found

    def test_recent_requests(self):
        from iios.integration.engine import IntegrationEngineHistory
        h = IntegrationEngineHistory()
        for _ in range(30):
            h.record_request(_make_request())
        recent = h.recent_requests(n=10)
        assert len(recent) == 10

    def test_bounded(self):
        from iios.integration.engine import IntegrationEngineHistory
        h = IntegrationEngineHistory(max_history=3)
        for _ in range(5):
            h.record_request(_make_request())
        assert h.request_count() == 3

    def test_response_for_request(self):
        from iios.integration.engine import IntegrationEngineHistory, IntegrationResponse
        h    = IntegrationEngineHistory()
        req  = _make_request()
        resp = IntegrationResponse.success_for(req, "s-001")
        h.record_response(resp)
        found = h.response_for_request(req.request_id)
        assert found is resp

    def test_clear(self):
        from iios.integration.engine import IntegrationEngineHistory
        h = IntegrationEngineHistory()
        h.record_request(_make_request())
        h.clear()
        assert h.request_count()  == 0
        assert h.response_count() == 0


# ════════════════════════════════════════════════════════════════════════
# 16. Events (9 event types)
# ════════════════════════════════════════════════════════════════════════


class TestEvents:
    def test_event_create(self):
        from iios.integration.engine import (
            IntegrationEngineEvent, IntegrationEngineEventType,
        )
        evt = IntegrationEngineEvent.create(
            IntegrationEngineEventType.INTEGRATION_INITIALIZED,
            "eng-001", "req-001", "s-001",
        )
        assert evt.event_id.startswith("evnt-")
        assert evt.engine_id  == "eng-001"

    def test_event_frozen(self):
        from iios.integration.engine import (
            IntegrationEngineEvent, IntegrationEngineEventType,
        )
        evt = IntegrationEngineEvent.create(
            IntegrationEngineEventType.CONNECTOR_LOADED,
            "eng-001", "req-001", "s-001",
        )
        with pytest.raises((AttributeError, TypeError)):
            evt.session_id = "x"  # type: ignore

    def test_all_9_events_emittable(self):
        from iios.integration.engine import (
            IntegrationEngineEventBus, IntegrationEngineEventType,
        )
        bus      = IntegrationEngineEventBus()
        received = []
        bus.add_listener(received.append)
        for evt_type in IntegrationEngineEventType:
            bus.emit(evt_type, "eng", "req", "sess")
        assert len(received) == 9

    def test_listener_exception_suppressed(self):
        from iios.integration.engine import (
            IntegrationEngineEventBus, IntegrationEngineEventType,
        )
        bus = IntegrationEngineEventBus()
        bus.add_listener(lambda e: 1 / 0)
        # Must not raise
        bus.emit(IntegrationEngineEventType.INTEGRATION_FAILED, "e", "r", "s")

    def test_remove_listener(self):
        from iios.integration.engine import (
            IntegrationEngineEventBus, IntegrationEngineEventType,
        )
        received = []
        bus      = IntegrationEngineEventBus()
        fn       = received.append
        bus.add_listener(fn)
        bus.remove_listener(fn)
        bus.emit(IntegrationEngineEventType.INTEGRATION_COMPLETED, "e", "r", "s")
        assert len(received) == 0

    def test_listener_count(self):
        from iios.integration.engine import IntegrationEngineEventBus
        bus = IntegrationEngineEventBus()
        assert bus.listener_count() == 0
        bus.add_listener(lambda e: None)
        assert bus.listener_count() == 1

    def test_dispatch_emits_events(self):
        from iios.integration.engine import IntegrationEngineEventType
        eng      = _make_engine()
        received = []
        eng.event_bus.add_listener(received.append)
        eng.dispatch(_make_request())
        event_types = {e.event_type for e in received}
        assert IntegrationEngineEventType.INTEGRATION_COMPLETED in event_types

    def test_event_to_dict(self):
        from iios.integration.engine import (
            IntegrationEngineEvent, IntegrationEngineEventType,
        )
        evt = IntegrationEngineEvent.create(
            IntegrationEngineEventType.INTEGRATION_PUBLISHED,
            "e", "r", "s", {"key": "val"}
        )
        d = evt.to_dict()
        assert "event_type"  in d
        assert d["payload"] == {"key": "val"}


# ════════════════════════════════════════════════════════════════════════
# 17. Pipeline
# ════════════════════════════════════════════════════════════════════════


class TestPipeline:
    def test_pipeline_executes_all_stages(self):
        from iios.integration.engine import (
            IntegrationEngineContext, IntegrationPipeline, PIPELINE_STAGE_ORDER,
        )
        pipeline = IntegrationPipeline()
        req      = _make_request()
        ctx      = IntegrationEngineContext.create(req, "s-001")
        execution = pipeline.execute(req, ctx)
        assert execution.success
        assert len(execution.completed_stages) == len(PIPELINE_STAGE_ORDER)

    def test_execution_tracking(self):
        from iios.integration.engine import (
            IntegrationEngineContext, IntegrationPipeline,
        )
        pipeline  = IntegrationPipeline()
        req       = _make_request()
        ctx       = IntegrationEngineContext.create(req, "s-001")
        execution = pipeline.execute(req, ctx)
        assert execution.execution_id.startswith("pipe-")
        assert execution.completed_at is not None

    def test_execution_to_dict(self):
        from iios.integration.engine import (
            IntegrationEngineContext, IntegrationPipeline,
        )
        pipeline  = IntegrationPipeline()
        req       = _make_request()
        ctx       = IntegrationEngineContext.create(req, "s-001")
        execution = pipeline.execute(req, ctx)
        d         = execution.to_dict()
        assert "execution_id"     in d
        assert "completed_stages" in d
        assert "success"          in d


# ════════════════════════════════════════════════════════════════════════
# 18. Dispatcher
# ════════════════════════════════════════════════════════════════════════


class TestDispatcher:
    def test_dispatch_single(self):
        from iios.integration.engine import (
            IntegrationDispatcher, IntegrationEngineContext,
        )
        d   = IntegrationDispatcher()
        req = _make_request()
        ctx = IntegrationEngineContext.create(req, "s-001")
        ex  = d.dispatch(req, ctx)
        assert ex.success

    def test_dispatch_batch(self):
        from iios.integration.engine import (
            IntegrationDispatcher, IntegrationEngineContext,
        )
        d    = IntegrationDispatcher()
        reqs = [_make_request() for _ in range(3)]
        ctxs = [IntegrationEngineContext.create(r, f"s-{i}") for i, r in enumerate(reqs)]
        exs  = d.dispatch_batch(reqs, ctxs)
        assert len(exs) == 3
        assert all(e.success for e in exs)


# ════════════════════════════════════════════════════════════════════════
# 19. Health and Status
# ════════════════════════════════════════════════════════════════════════


class TestHealthAndStatus:
    def test_health_healthy(self):
        eng = _make_engine()
        h   = eng.health()
        assert h.status == "healthy"

    def test_health_degraded_no_connectors(self):
        from iios.integration.engine import IntegrationEngine
        eng = IntegrationEngine()
        eng.initialize()
        h = eng.health()
        assert h.status in ("degraded", "unhealthy")

    def test_health_stopped(self):
        from iios.integration.engine import IntegrationEngineState
        eng = _make_engine()
        eng.stop()
        h = eng.health()
        assert h.status == "unhealthy"

    def test_health_to_dict(self):
        eng = _make_engine()
        d   = eng.health().to_dict()
        assert "status"      in d
        assert "uptime_seconds" in d

    def test_status_snapshot(self):
        from iios.integration.engine import IntegrationEngineState
        eng = _make_engine()
        s   = eng.status()
        assert s.state == IntegrationEngineState.IDLE
        assert s.connector_count >= 1

    def test_status_to_dict(self):
        eng = _make_engine()
        d   = eng.status().to_dict()
        assert "engine_id" in d
        assert "state"     in d

    def test_monitor_returns_health(self):
        from iios.integration.engine import EngineHealthReport
        eng = _make_engine()
        h   = eng.monitor()
        assert isinstance(h, EngineHealthReport)


# ════════════════════════════════════════════════════════════════════════
# 20. Factory
# ════════════════════════════════════════════════════════════════════════


class TestFactory:
    def test_create_request(self):
        from iios.integration.engine import ConnectorType, IntegrationEngineFactory
        f   = IntegrationEngineFactory()
        req = f.create_request(ConnectorType.KAFKA)
        assert req.connector_type == ConnectorType.KAFKA

    def test_create_context(self):
        from iios.integration.engine import IntegrationEngineFactory
        f   = IntegrationEngineFactory()
        req = _make_request()
        ctx = f.create_context(req, "s-001")
        assert ctx.session_id == "s-001"

    def test_create_success_response(self):
        from iios.integration.engine import IntegrationEngineFactory
        f    = IntegrationEngineFactory()
        req  = _make_request()
        resp = f.create_success_response(req, "s-001", {"k": "v"}, 42.0)
        assert resp.is_success
        assert resp.latency_ms == 42.0

    def test_create_failure_response(self):
        from iios.integration.engine import IntegrationEngineFactory
        f    = IntegrationEngineFactory()
        req  = _make_request()
        resp = f.create_failure_response(req, "s-001", "something broke")
        assert resp.is_failure

    def test_create_connector_descriptor(self):
        from iios.integration.engine import ConnectorType, IntegrationEngineFactory
        f    = IntegrationEngineFactory()
        desc = f.create_connector_descriptor(ConnectorType.WEBSOCKET, "WS Conn")
        assert desc.connector_type == ConnectorType.WEBSOCKET

    def test_create_adapter_descriptor(self):
        from iios.integration.engine import (
            AdapterType, ConnectorType, IntegrationEngineFactory,
        )
        f    = IntegrationEngineFactory()
        desc = f.create_adapter_descriptor(AdapterType.KAFKA, ConnectorType.KAFKA, "Kafka Adapter")
        assert desc.adapter_type == AdapterType.KAFKA

    def test_create_protocol_descriptor(self):
        from iios.integration.engine import IntegrationEngineFactory, ProtocolType
        f    = IntegrationEngineFactory()
        desc = f.create_protocol_descriptor(ProtocolType.AMQP, "AMQP Protocol")
        assert desc.protocol_type == ProtocolType.AMQP


# ════════════════════════════════════════════════════════════════════════
# 21. Session Manager
# ════════════════════════════════════════════════════════════════════════


class TestSessionManager:
    def test_create_session(self):
        from iios.integration.engine import IntegrationSessionManager
        sm  = IntegrationSessionManager()
        sid = sm.create_session("wf-test")
        assert sid
        assert sm.active_count() == 1

    def test_create_and_initialize(self):
        from iios.integration.engine import IntegrationSessionManager
        sm  = IntegrationSessionManager()
        sid = sm.create_and_initialize("wf-test")
        assert sm.get_session(sid) is not None

    def test_fail_session_doesnt_raise(self):
        from iios.integration.engine import IntegrationSessionManager
        sm  = IntegrationSessionManager()
        sid = sm.create_session("wf-test")
        sm.fail_session(sid, reason="test failure")   # should not raise

    def test_archive_decrements_active(self):
        from iios.integration.engine import IntegrationSessionManager
        sm  = IntegrationSessionManager()
        sid = sm.create_and_initialize("wf-x")
        sm.complete_session(sid)
        sm.archive_session(sid)
        assert sm.active_count() == 0


# ════════════════════════════════════════════════════════════════════════
# 22. Concurrency
# ════════════════════════════════════════════════════════════════════════


class TestConcurrency:
    def test_concurrent_dispatch(self):
        eng     = _make_engine()
        results = []
        errors  = []

        def dispatch():
            try:
                resp = eng.dispatch(_make_request())
                results.append(resp)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=dispatch) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors  == []
        assert len(results) == 20
        assert all(r.is_success for r in results)

    def test_concurrent_connector_registration(self):
        from iios.integration.engine import (
            ConnectorDescriptor, ConnectorManager, ConnectorType,
        )
        mgr    = ConnectorManager(max_connectors=100)
        errors = []

        def register(i: int):
            try:
                types = list(ConnectorType)
                ct    = types[i % len(types)]
                mgr.register(ConnectorDescriptor.create(ct, f"conn-{i}"))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=register, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []

    def test_concurrent_statistics(self):
        from iios.integration.engine import IntegrationEngineStatistics
        stats = IntegrationEngineStatistics()

        def increment():
            for _ in range(200):
                stats.record_session()

        threads = [threading.Thread(target=increment) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert stats.report().integration_sessions == 2000

    def test_concurrent_scheduler_submit(self):
        from iios.integration.engine import IntegrationScheduler
        sched  = IntegrationScheduler(max_queue=10_000)
        errors = []

        def submit():
            try:
                for _ in range(100):
                    sched.submit(_make_request())
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=submit) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert sched.queue_size() == 1000


# ════════════════════════════════════════════════════════════════════════
# 23. Stress Testing
# ════════════════════════════════════════════════════════════════════════


class TestStressTesting:
    def test_dispatch_1000_requests(self):
        eng      = _make_engine()
        requests = [_make_request() for _ in range(1000)]
        for req in requests:
            resp = eng.dispatch(req)
            assert resp.is_success

        r = eng.stats.report()
        assert r.integration_sessions >= 1000

    def test_scheduler_1000_submissions(self):
        from iios.integration.engine import IntegrationScheduler
        sched = IntegrationScheduler(max_queue=10_000)
        for i in range(1000):
            sched.submit(_make_request(), priority=i % 10)
        assert sched.queue_size() == 1000
        dequeued = 0
        while sched.next() is not None:
            dequeued += 1
        assert dequeued == 1000

    def test_history_bounded_under_load(self):
        from iios.integration.engine import IntegrationEngineHistory
        h = IntegrationEngineHistory(max_history=100)
        for _ in range(500):
            h.record_request(_make_request())
        assert h.request_count() == 100   # bounded

    def test_event_bus_high_throughput(self):
        from iios.integration.engine import (
            IntegrationEngineEventBus, IntegrationEngineEventType,
        )
        bus      = IntegrationEngineEventBus()
        received = []
        bus.add_listener(received.append)
        for _ in range(500):
            bus.emit(
                IntegrationEngineEventType.INTEGRATION_DISPATCHED,
                "eng", "req", "sess"
            )
        assert len(received) == 500


# ════════════════════════════════════════════════════════════════════════
# 24. Regression
# ════════════════════════════════════════════════════════════════════════


class TestRegression:
    def test_engine_module_importable(self):
        import iios.integration.engine as m
        assert hasattr(m, "IntegrationEngine")
        assert hasattr(m, "IntegrationManager")

    def test_lifecycle_module_still_importable(self):
        import iios.integration.lifecycle as m
        assert hasattr(m, "IntegrationLifecycle")

    def test_knowledge_modules_importable(self):
        import iios.knowledge
        assert iios.knowledge is not None

    def test_supervisor_importable(self):
        import iios.supervisor
        assert iios.supervisor is not None

    def test_all_exports_present(self):
        from iios.integration.engine import __all__
        import iios.integration.engine as m
        for name in __all__:
            assert hasattr(m, name), f"Missing export: {name!r}"

    def test_no_protocol_specific_code_imported(self):
        """Engine must not import any vendor/protocol clients."""
        import iios.integration.engine.integration_engine as mod
        src = __import__("inspect").getsource(mod)
        for forbidden in ("requests.get", "httpx", "aiohttp", "kafka", "pika"):
            assert forbidden not in src, f"Forbidden import found: {forbidden!r}"

    def test_session_manager_uses_m1_lifecycle(self):
        from iios.integration.engine import IntegrationSessionManager
        from iios.integration.lifecycle import IntegrationLifecycle
        sm = IntegrationSessionManager()
        assert isinstance(sm.lifecycle, IntegrationLifecycle)
