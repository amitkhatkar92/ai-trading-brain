"""
test_integration_services_m4.py
================================
C15 M4 — Integration Services Framework

Comprehensive test suite. Targets 95%+ coverage across all 48 source files.

Groups:
  A — Constants & exceptions
  B — Core data objects (Request / Response / Context)
  C — Registry & management
  D — Adapter & protocol engines
  E — API clients (HTTP, REST, GraphQL, gRPC, WebSocket)
  F — API Gateway engine
  G — Messaging adapters (Kafka, RabbitMQ, Redis Streams)
  H — Messaging / streaming engines (MessageBus, EventBus, Stream, Queue)
  I — Specialized connectors (Webhook, Database, FileTransfer, Notification)
  J — Security (Auth, Authz, Credentials, Secrets, Certs)
  K — Resilience (Retry, Failover, RateLimit, Timeout, Pool)
  L — Observability (Validator, Statistics, History, Events)
  M — Factory
  N — Central engine (IntegrationServicesEngine)
  O — Concurrency & stress
  P — Regression (no circular imports, no vendor code)
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, List

import pytest

import iios.integration.services as svc
from iios.integration.services.constants import (
    AdapterProtocol,
    AuthScheme,
    ConnectionState,
    ConnectorOperation,
    HealthStatus,
    MessageDeliveryMode,
    RetryStrategy,
    ServiceEventType,
    ServiceType,
    ServiceValidationCheck,
    StreamMode,
    TransportType,
)
from iios.integration.services.connector_context import ConnectorContext
from iios.integration.services.connector_request import ConnectorRequest
from iios.integration.services.connector_response import ConnectorResponse


# ════════════════════════════════════════════════════════════════════════
# A — Constants & Exceptions
# ════════════════════════════════════════════════════════════════════════


class TestConstants:
    def test_service_type_count(self):
        assert len(ServiceType) == 22

    def test_connector_operation_count(self):
        assert len(ConnectorOperation) == 11

    def test_connection_state_values(self):
        values = {e.value for e in ConnectionState}
        assert "idle" in values
        assert "connected" in values
        assert "failed" in values

    def test_retry_strategy_includes_fibonacci(self):
        strategies = {e.value for e in RetryStrategy}
        assert "fibonacci" in strategies
        assert "immediate" in strategies
        assert "exponential_backoff" in strategies

    def test_auth_scheme_count(self):
        assert len(AuthScheme) >= 7

    def test_health_status_values(self):
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"

    def test_message_delivery_mode_values(self):
        assert MessageDeliveryMode.AT_MOST_ONCE.value   == "at_most_once"
        assert MessageDeliveryMode.AT_LEAST_ONCE.value  == "at_least_once"
        assert MessageDeliveryMode.EXACTLY_ONCE.value   == "exactly_once"

    def test_stream_mode_values(self):
        assert StreamMode.PUSH.value          == "push"
        assert StreamMode.PULL.value          == "pull"
        assert StreamMode.BIDIRECTIONAL.value == "bidirectional"

    def test_service_event_type_count(self):
        assert len(ServiceEventType) == 10

    def test_service_validation_check_count(self):
        assert len(ServiceValidationCheck) == 6

    def test_constants_defaults(self):
        from iios.integration.services.constants import (
            DEFAULT_TIMEOUT_MS, DEFAULT_RETRY_COUNT, DEFAULT_POOL_SIZE,
            DEFAULT_POOL_MAX, FIBONACCI_DELAYS_MS, WORKFLOW_STAGES,
        )
        assert DEFAULT_TIMEOUT_MS    == 30_000
        assert DEFAULT_RETRY_COUNT   == 3
        assert DEFAULT_POOL_SIZE     >= 1
        assert DEFAULT_POOL_MAX      >= DEFAULT_POOL_SIZE
        assert len(FIBONACCI_DELAYS_MS) >= 5
        assert len(WORKFLOW_STAGES)  == 10


class TestExceptions:
    def test_integration_service_error(self):
        exc = svc.IntegrationServiceError("test error")
        assert "ISF" in str(exc.code)

    def test_connector_not_found_error(self):
        exc = svc.ConnectorNotFoundError("rest-api")
        assert "rest-api" in str(exc)

    def test_service_not_ready_error(self):
        exc = svc.ServiceNotReadyError()
        assert "not ready" in str(exc).lower()

    def test_rate_limit_exceeded(self):
        exc = svc.RateLimitExceeded()
        assert exc is not None

    def test_service_timeout_error(self):
        exc = svc.ServiceTimeoutError(timeout_ms=5000)
        assert exc.timeout_ms == 5000


# ════════════════════════════════════════════════════════════════════════
# B — Core data objects
# ════════════════════════════════════════════════════════════════════════


class TestConnectorRequest:
    def _make_request(self, **kwargs) -> ConnectorRequest:
        defaults = dict(
            approved_request_id = "test-apr-001",
            service_type        = ServiceType.REST_API,
            endpoint            = "https://api.example.com",
        )
        defaults.update(kwargs)
        return ConnectorRequest.create(**defaults)

    def test_create_basic(self):
        req = self._make_request()
        assert req.request_id  # non-empty UUID
        assert req.service_type == ServiceType.REST_API
        assert req.timeout_ms   == 30_000

    def test_immutable(self):
        req = self._make_request()
        with pytest.raises((TypeError, AttributeError)):
            req.endpoint = "changed"  # type: ignore[misc]

    def test_payload_defaults_empty(self):
        req = self._make_request()
        assert req.payload == {}

    def test_custom_timeout(self):
        req = self._make_request(timeout_ms=5_000)
        assert req.timeout_ms == 5_000

    def test_auth_scheme_default_none(self):
        req = self._make_request()
        assert req.auth_scheme == AuthScheme.NONE

    def test_created_at_set(self):
        req = self._make_request()
        assert req.created_at


class TestConnectorResponse:
    def test_success_factory(self):
        resp = ConnectorResponse.success(
            "req-001", data={"rows": [1, 2, 3]}, latency_ms=12.5
        )
        assert resp.status.value == "success"
        assert resp.latency_ms   == 12.5
        assert resp.data["rows"] == [1, 2, 3]

    def test_failure_factory(self):
        resp = ConnectorResponse.failure("req-002", error_message="timeout")
        assert resp.status.value  == "failure"
        assert resp.error_message == "timeout"

    def test_immutable(self):
        resp = ConnectorResponse.success("r1")
        with pytest.raises((TypeError, AttributeError)):
            resp.status = None  # type: ignore[misc]

    def test_response_id_unique(self):
        r1 = ConnectorResponse.success("req-A")
        r2 = ConnectorResponse.success("req-B")
        assert r1.response_id != r2.response_id


class TestConnectorContext:
    def test_create(self):
        ctx = ConnectorContext.create(
            request_id   = "req-001",
            session_id   = "sess-001",
            service_type = ServiceType.KAFKA,
        )
        assert ctx.context_id.startswith("sctx-")
        assert ctx.service_type == ServiceType.KAFKA

    def test_to_dict(self):
        ctx = ConnectorContext.create(
            request_id="r1", session_id="s1", service_type=ServiceType.REST_API
        )
        d = ctx.to_dict()
        assert "context_id" in d
        assert "service_type" in d

    def test_immutable(self):
        ctx = ConnectorContext.create(
            request_id="r1", session_id="s1", service_type=ServiceType.REST_API
        )
        with pytest.raises((TypeError, AttributeError)):
            ctx.session_id = "changed"  # type: ignore[misc]


# ════════════════════════════════════════════════════════════════════════
# C — Registry & management
# ════════════════════════════════════════════════════════════════════════


class TestConnectorRegistry:
    def _make_descriptor(self, svc_type=ServiceType.REST_API, name="test"):
        from iios.integration.services.connector_registry import ConnectorDescriptor
        return ConnectorDescriptor.create(
            name         = name,
            service_type = svc_type,
        )

    def test_register_and_retrieve(self):
        from iios.integration.services.connector_registry import ConnectorRegistry
        reg = ConnectorRegistry()
        desc = self._make_descriptor()
        reg.register(desc)
        found = reg.first_by_type(ServiceType.REST_API)
        assert found is not None

    def test_count(self):
        from iios.integration.services.connector_registry import ConnectorRegistry
        reg = ConnectorRegistry()
        for _ in range(3):
            reg.register(self._make_descriptor())
        assert reg.count() >= 3

    def test_supports_type(self):
        from iios.integration.services.connector_registry import ConnectorRegistry
        reg = ConnectorRegistry()
        reg.register(self._make_descriptor(ServiceType.KAFKA))
        assert reg.supports_type(ServiceType.KAFKA)
        assert not reg.supports_type(ServiceType.GRPC)


class TestAdapterRegistry:
    def _make_adapter_desc(self):
        from iios.integration.services.adapter_registry import AdapterDescriptor
        return AdapterDescriptor.create(
            name         = "test-adapter",
            protocol     = AdapterProtocol.REST,
            service_type = ServiceType.REST_API,
        )

    def test_register_and_find(self):
        from iios.integration.services.adapter_registry import AdapterRegistry
        reg = AdapterRegistry()
        desc = self._make_adapter_desc()
        reg.register(desc)
        found = reg.first_for_service(ServiceType.REST_API)
        assert found is not None

    def test_missing_returns_none(self):
        from iios.integration.services.adapter_registry import AdapterRegistry
        reg = AdapterRegistry()
        assert reg.first_for_service(ServiceType.GRPC) is None


# ════════════════════════════════════════════════════════════════════════
# E — API clients
# ════════════════════════════════════════════════════════════════════════


class TestHttpClient:
    def test_get(self):
        from iios.integration.services.http_client import SimulatedHttpClient
        c = SimulatedHttpClient()
        result = c.get("https://example.com")
        assert result["status_code"] == 200
        assert result["simulated"] is True

    def test_post(self):
        from iios.integration.services.http_client import SimulatedHttpClient
        c = SimulatedHttpClient()
        result = c.post("https://example.com", payload={"key": "val"})
        assert result["method"] == "POST"

    def test_put(self):
        from iios.integration.services.http_client import SimulatedHttpClient
        c = SimulatedHttpClient()
        result = c.put("https://example.com", payload={"k": "v"})
        assert result["method"] == "PUT"

    def test_delete(self):
        from iios.integration.services.http_client import SimulatedHttpClient
        c = SimulatedHttpClient()
        result = c.delete("https://example.com")
        assert result["method"] == "DELETE"

    def test_health_check(self):
        from iios.integration.services.http_client import SimulatedHttpClient
        assert SimulatedHttpClient().health_check() is True

    def test_execute_integration(self):
        from iios.integration.services.http_client import SimulatedHttpClient
        c   = SimulatedHttpClient()
        req = ConnectorRequest.create(
            approved_request_id = "x",
            service_type        = ServiceType.HTTP,
            endpoint            = "https://api.example.com",
        )
        resp = c.execute(req, operation="post")
        assert resp.status.value == "success"


class TestRestClient:
    def test_call(self):
        from iios.integration.services.rest_client import SimulatedRestClient
        c = SimulatedRestClient()
        r = c.call("GET", "https://api.example.com")
        assert r["status_code"] == 200

    def test_execute(self):
        from iios.integration.services.rest_client import SimulatedRestClient
        c   = SimulatedRestClient()
        req = ConnectorRequest.create(
            approved_request_id = "rest-x",
            service_type        = ServiceType.REST_API,
            endpoint            = "https://api.example.com",
        )
        resp = c.execute(req)
        assert resp.status.value == "success"


class TestGraphqlClient:
    def test_query(self):
        from iios.integration.services.graphql_client import SimulatedGraphqlClient
        c = SimulatedGraphqlClient()
        r = c.query("https://gql.example.com", "{ users { id } }")
        assert r["simulated"] is True

    def test_mutate(self):
        from iios.integration.services.graphql_client import SimulatedGraphqlClient
        c = SimulatedGraphqlClient()
        r = c.mutate("https://gql.example.com", "mutation { createUser(name: \"x\") { id } }")
        assert r["simulated"] is True

    def test_health_check(self):
        from iios.integration.services.graphql_client import SimulatedGraphqlClient
        assert SimulatedGraphqlClient().health_check() is True


class TestGrpcClient:
    def test_unary(self):
        from iios.integration.services.grpc_client import SimulatedGrpcClient
        c = SimulatedGrpcClient()
        r = c.unary("orders.OrderService", "GetOrder", {"id": 1})
        assert r["simulated"] is True

    def test_server_stream(self):
        from iios.integration.services.grpc_client import SimulatedGrpcClient
        c = SimulatedGrpcClient()
        msgs = c.server_stream("stream.StreamService", "Watch", {})
        assert isinstance(msgs, list)
        assert len(msgs) >= 1

    def test_health_check(self):
        from iios.integration.services.grpc_client import SimulatedGrpcClient
        assert SimulatedGrpcClient().health_check() is True


class TestWebSocketClient:
    def test_connect_send_receive_close(self):
        from iios.integration.services.websocket_client import SimulatedWebSocketClient
        c = SimulatedWebSocketClient()
        c.connect("wss://stream.example.com")
        c.send('{"subscribe": "NIFTY"}')
        raw = c.receive()
        assert "simulated" in raw
        c.close()

    def test_health_check(self):
        from iios.integration.services.websocket_client import SimulatedWebSocketClient
        assert SimulatedWebSocketClient().health_check() is True


# ════════════════════════════════════════════════════════════════════════
# F — API Gateway
# ════════════════════════════════════════════════════════════════════════


class TestApiGatewayEngine:
    def _req(self, svc_type=ServiceType.REST_API):
        return ConnectorRequest.create(
            approved_request_id = "gw-test",
            service_type        = svc_type,
            endpoint            = "https://api.example.com",
        )

    def test_route_rest(self):
        gw = svc.ApiGatewayEngine()
        resp = gw.route(self._req(ServiceType.REST_API))
        assert resp.status.value == "success"

    def test_route_graphql(self):
        gw = svc.ApiGatewayEngine()
        resp = gw.route(self._req(ServiceType.GRAPHQL))
        assert resp.status.value == "success"

    def test_route_grpc(self):
        gw = svc.ApiGatewayEngine()
        resp = gw.route(self._req(ServiceType.GRPC))
        assert resp.status.value == "success"

    def test_route_websocket(self):
        gw = svc.ApiGatewayEngine()
        resp = gw.route(self._req(ServiceType.WEBSOCKET))
        assert resp.status.value == "success"

    def test_requests_routed_counter(self):
        gw = svc.ApiGatewayEngine()
        gw.route(self._req())
        gw.route(self._req())
        assert gw.requests_routed == 2

    def test_health_check(self):
        assert svc.ApiGatewayEngine().health_check() is True


# ════════════════════════════════════════════════════════════════════════
# G — Messaging adapters
# ════════════════════════════════════════════════════════════════════════


class TestKafkaAdapter:
    def test_produce(self):
        adapter = svc.SimulatedKafkaAdapter()
        msg = adapter.produce("test-topic", {"key": "val"})
        assert msg.topic == "test-topic"
        assert msg.offset >= 1

    def test_consume(self):
        adapter = svc.SimulatedKafkaAdapter()
        msgs = adapter.consume("test-topic", "test-group")
        assert isinstance(msgs, list)

    def test_health_check(self):
        assert svc.SimulatedKafkaAdapter().health_check() is True

    def test_execute_produce(self):
        adapter = svc.SimulatedKafkaAdapter()
        req = ConnectorRequest.create(
            approved_request_id = "k-test",
            service_type        = ServiceType.KAFKA,
            endpoint            = "kafka://test-topic",
            connector_config    = {"kafka_topic": "test-topic", "kafka_operation": "produce"},
        )
        resp = adapter.execute(req)
        assert resp.status.value == "success"

    def test_execute_consume(self):
        adapter = svc.SimulatedKafkaAdapter()
        req = ConnectorRequest.create(
            approved_request_id = "k-cons",
            service_type        = ServiceType.KAFKA,
            endpoint            = "kafka://test-topic",
            connector_config    = {
                "kafka_topic": "test-topic", "kafka_operation": "consume",
                "kafka_group_id": "g1",
            },
        )
        resp = adapter.execute(req)
        assert resp.status.value == "success"
        assert "messages" in resp.data


class TestRabbitMQAdapter:
    def test_publish(self):
        adapter = svc.SimulatedRabbitMQAdapter()
        msg = adapter.publish("signals", "trade.buy", {"symbol": "NIFTY"})
        assert msg.exchange == "signals"
        assert msg.delivery_tag >= 1

    def test_consume(self):
        adapter = svc.SimulatedRabbitMQAdapter()
        msgs = adapter.consume("signals-queue")
        assert isinstance(msgs, list)

    def test_execute_publish(self):
        adapter = svc.SimulatedRabbitMQAdapter()
        req = ConnectorRequest.create(
            approved_request_id = "rmq-test",
            service_type        = ServiceType.RABBITMQ,
            endpoint            = "amqp://signals/trade.buy",
            connector_config    = {
                "rmq_operation": "publish",
                "rmq_exchange":  "signals",
                "rmq_routing_key": "trade.buy",
            },
        )
        resp = adapter.execute(req)
        assert resp.status.value == "success"


class TestRedisStreamAdapter:
    def test_xadd(self):
        adapter = svc.SimulatedRedisStreamAdapter()
        entry = adapter.xadd("iios:trades", {"symbol": "NIFTY"})
        assert entry.stream_key == "iios:trades"
        assert entry.entry_id.startswith("0-")

    def test_xread(self):
        adapter = svc.SimulatedRedisStreamAdapter()
        entries = adapter.xread("iios:trades", "my-group", "consumer-1")
        assert isinstance(entries, list)

    def test_execute_xadd(self):
        adapter = svc.SimulatedRedisStreamAdapter()
        req = ConnectorRequest.create(
            approved_request_id = "redis-test",
            service_type        = ServiceType.REDIS_STREAM,
            endpoint            = "redis://localhost:6379",
            payload             = {"event": "trade"},
            connector_config    = {
                "redis_operation":  "xadd",
                "redis_stream_key": "iios:stream",
            },
        )
        resp = adapter.execute(req)
        assert resp.status.value == "success"


# ════════════════════════════════════════════════════════════════════════
# H — Messaging / streaming engines
# ════════════════════════════════════════════════════════════════════════


class TestMessageBusEngine:
    def test_route_kafka(self):
        bus = svc.MessageBusEngine()
        req = svc.IntegrationServicesFactory.create_kafka_request("signals", {"s": "NIFTY"})
        resp = bus.route(req)
        assert resp.status.value == "success"

    def test_route_rabbitmq(self):
        bus = svc.MessageBusEngine()
        req = svc.IntegrationServicesFactory.create_rabbitmq_request("ex", "rk", {"s": "NIFTY"})
        resp = bus.route(req)
        assert resp.status.value == "success"

    def test_route_redis(self):
        bus = svc.MessageBusEngine()
        req = ConnectorRequest.create(
            approved_request_id = "redis-bus",
            service_type        = ServiceType.REDIS_STREAM,
            endpoint            = "redis://localhost",
            payload             = {"ev": "trade"},
            connector_config    = {"redis_operation": "xadd", "redis_stream_key": "k"},
        )
        resp = bus.route(req)
        assert resp.status.value == "success"

    def test_health_check(self):
        assert svc.MessageBusEngine().health_check() is True

    def test_stats(self):
        bus = svc.MessageBusEngine()
        req = svc.IntegrationServicesFactory.create_kafka_request("t", {})
        bus.route(req)
        st = bus.stats
        assert st.published >= 1


class TestEventBusEngine:
    def test_subscribe_and_publish(self):
        bus = svc.EventBusEngine()
        received: List[Any] = []
        bus.subscribe("market.signal", lambda e: received.append(e))
        n = bus.publish_to("market.signal", "test", {"sym": "NIFTY"})
        assert n == 1
        assert len(received) == 1

    def test_unsubscribe(self):
        bus = svc.EventBusEngine()
        handler = lambda e: None
        bus.subscribe("t", handler)
        removed = bus.unsubscribe("t", handler)
        assert removed is True

    def test_publish_to_unknown_topic(self):
        bus = svc.EventBusEngine()
        n = bus.publish_to("no-subscribers", "test", {})
        assert n == 0

    def test_handler_exception_suppressed(self):
        bus = svc.EventBusEngine()
        bus.subscribe("t", lambda e: (_ for _ in ()).throw(RuntimeError("boom")))  # type: ignore
        n = bus.publish_to("t", "test", {})
        assert n == 0  # exception suppressed

    def test_stats(self):
        bus = svc.EventBusEngine()
        bus.publish_to("t", "x", {})
        st = bus.stats
        assert st["published"] >= 1


class TestStreamEngine:
    def test_open_and_close_session(self):
        se = svc.StreamEngine()
        s  = se.open_session("test-source", StreamMode.PUSH)
        assert s.active is True
        ok = se.close_session(s.session_id)
        assert ok is True

    def test_push_frame(self):
        se = svc.StreamEngine()
        received: List[Any] = []
        s = se.open_session("src", StreamMode.PUSH)
        se.subscribe(s.session_id, lambda f: received.append(f))
        n = se.push_frame(s.session_id, {"tick": 100})
        assert n == 1
        assert received[0]["tick"] == 100

    def test_pull_frame(self):
        se = svc.StreamEngine()
        s  = se.open_session("src", StreamMode.PULL)
        f  = se.pull_frame(s.session_id, {"request": True})
        assert "session_id" in f

    def test_max_sessions_enforced(self):
        se = svc.StreamEngine(max_sessions=2)
        se.open_session("s1", StreamMode.PUSH)
        se.open_session("s2", StreamMode.PUSH)
        with pytest.raises(RuntimeError):
            se.open_session("s3", StreamMode.PUSH)


class TestQueueEngine:
    def test_enqueue_dequeue(self):
        q = svc.QueueEngine()
        q.create_queue("my-queue")
        msg = q.enqueue("my-queue", {"val": 1})
        assert msg is not None
        msgs = q.dequeue("my-queue", max_count=10)
        assert len(msgs) == 1

    def test_depth(self):
        q = svc.QueueEngine()
        for _ in range(5):
            q.enqueue("q", {"n": 1})
        assert q.depth("q") == 5

    def test_drop_when_full(self):
        q = svc.QueueEngine(max_size=2)
        q.enqueue("q", {"n": 1})
        q.enqueue("q", {"n": 2})
        dropped = q.enqueue("q", {"n": 3})  # 3rd should be dropped
        assert dropped is None

    def test_peek(self):
        q = svc.QueueEngine()
        q.enqueue("q", {"val": 42})
        msg = q.peek("q")
        assert msg is not None
        assert msg.payload["val"] == 42
        assert q.depth("q") == 1  # peek doesn't consume

    def test_delete_queue(self):
        q = svc.QueueEngine()
        q.create_queue("temp")
        q.enqueue("temp", {})
        ok = q.delete_queue("temp")
        assert ok is True
        assert q.depth("temp") == 0

    def test_stats(self):
        q = svc.QueueEngine()
        q.enqueue("q2", {"x": 1})
        st = q.stats("q2")
        assert st.enqueued == 1


# ════════════════════════════════════════════════════════════════════════
# I — Specialized connectors
# ════════════════════════════════════════════════════════════════════════


class TestWebhookEngine:
    def test_register_and_dispatch(self):
        wh = svc.WebhookEngine()
        ep = wh.register("https://hooks.example.com", "secret", ["trade.executed"])
        records = wh.dispatch("trade.executed", {"symbol": "NIFTY"})
        assert len(records) == 1
        assert records[0].success is True

    def test_deregister(self):
        wh = svc.WebhookEngine()
        ep = wh.register("https://hooks.example.com", "secret", [])
        ok = wh.deregister(ep.webhook_id)
        assert ok is True

    def test_dispatch_no_subscribers(self):
        wh = svc.WebhookEngine()
        records = wh.dispatch("unknown.event", {})
        assert records == []

    def test_execute(self):
        wh = svc.WebhookEngine()
        wh.register("https://hooks.example.com", "secret", ["signals"])
        req = svc.IntegrationServicesFactory.create_webhook_request("signals", {"x": 1})
        resp = wh.execute(req)
        assert resp.status.value == "success"

    def test_delivery_count(self):
        wh = svc.WebhookEngine()
        wh.register("https://h1.example.com", "s1", [])
        wh.dispatch("any", {})
        assert wh.delivery_count >= 1


class TestDatabaseConnectorEngine:
    def test_query(self):
        db = svc.DatabaseConnectorEngine()
        req = ConnectorRequest.create(
            approved_request_id = "db-test",
            service_type        = ServiceType.DATABASE,
            endpoint            = "db://localhost/mydb",
            connector_config    = {"db_operation": "query", "db_sql": "SELECT 1"},
        )
        resp = db.execute(req)
        assert resp.status.value == "success"
        assert "rows" in resp.data

    def test_execute_dml(self):
        db = svc.DatabaseConnectorEngine()
        req = ConnectorRequest.create(
            approved_request_id = "db-dml",
            service_type        = ServiceType.DATABASE,
            endpoint            = "db://localhost/mydb",
            connector_config    = {
                "db_operation": "execute",
                "db_sql": "INSERT INTO trades VALUES (1)",
            },
        )
        resp = db.execute(req)
        assert resp.status.value == "success"
        assert resp.data["rows_affected"] >= 1

    def test_stats(self):
        db = svc.DatabaseConnectorEngine()
        db.register_connection("default")
        st = db.stats
        assert st["connections"] >= 1


class TestFileTransferEngine:
    def test_upload(self):
        ft = svc.FileTransferEngine()
        req = ConnectorRequest.create(
            approved_request_id = "ft-test",
            service_type        = ServiceType.FILE_TRANSFER,
            endpoint            = "sftp://storage.example.com",
            connector_config    = {
                "transfer_operation": "upload",
                "transfer_source_path": "/tmp/trades.csv",
                "transfer_dest_path":   "/data/trades.csv",
            },
        )
        resp = ft.execute(req)
        assert resp.status.value == "success"
        assert resp.data["operation"] == "upload"

    def test_download(self):
        ft = svc.FileTransferEngine()
        req = ConnectorRequest.create(
            approved_request_id = "ft-dl",
            service_type        = ServiceType.FILE_TRANSFER,
            endpoint            = "sftp://storage.example.com",
            connector_config    = {
                "transfer_operation": "download",
                "transfer_source_path": "/data/trades.csv",
                "transfer_dest_path":   "/tmp/trades.csv",
            },
        )
        resp = ft.execute(req)
        assert resp.status.value == "success"
        assert resp.data["operation"] == "download"


class TestNotificationEngine:
    def test_email(self):
        ne = svc.NotificationEngine()
        req = svc.IntegrationServicesFactory.create_notification_request(
            channel="email", recipient="user@example.com",
            subject="Trade Alert", body="NIFTY BUY signal"
        )
        resp = ne.execute(req)
        assert resp.status.value == "success"
        assert resp.data["channel"] == "email"

    def test_sms(self):
        ne = svc.NotificationEngine()
        req = svc.IntegrationServicesFactory.create_notification_request(
            channel="sms", recipient="+91-9876543210",
            subject="Alert", body="Position closed"
        )
        resp = ne.execute(req)
        assert resp.status.value == "success"

    def test_push(self):
        ne = svc.NotificationEngine()
        req = svc.IntegrationServicesFactory.create_notification_request(
            channel="push", recipient="device-token-abc",
            subject="Alert", body="P&L update"
        )
        resp = ne.execute(req)
        assert resp.status.value == "success"

    def test_unknown_channel_failure(self):
        ne = svc.NotificationEngine()
        req = ConnectorRequest.create(
            approved_request_id = "notif-bad",
            service_type        = ServiceType.EMAIL,
            endpoint            = "notification://unknown",
            connector_config    = {"notification_channel": "fax"},
        )
        resp = ne.execute(req)
        assert resp.status.value == "failure"

    def test_health_check(self):
        assert svc.NotificationEngine().health_check() is True


# ════════════════════════════════════════════════════════════════════════
# J — Security
# ════════════════════════════════════════════════════════════════════════


class TestAuthenticationEngine:
    def test_none_auth_always_succeeds(self):
        ae = svc.AuthenticationEngine()
        result = ae.authenticate(AuthScheme.NONE, {})
        assert result.success is True

    def test_api_key_success(self):
        ae = svc.AuthenticationEngine()
        result = ae.authenticate(AuthScheme.API_KEY, {"api_key": "my-key", "client_id": "app"})
        assert result.success is True
        assert result.token is not None

    def test_api_key_failure_empty(self):
        ae = svc.AuthenticationEngine()
        result = ae.authenticate(AuthScheme.API_KEY, {})
        assert result.success is False

    def test_bearer_token(self):
        ae = svc.AuthenticationEngine()
        result = ae.authenticate(AuthScheme.BEARER_TOKEN, {"token": "jwt-xyz"})
        assert result.success is True

    def test_basic_auth(self):
        ae = svc.AuthenticationEngine()
        result = ae.authenticate(AuthScheme.BASIC, {"username": "admin", "password": "pass"})
        assert result.success is True

    def test_oauth2(self):
        ae = svc.AuthenticationEngine()
        result = ae.authenticate(AuthScheme.OAUTH2, {"client_id": "my-app", "client_secret": "s"})
        assert result.success is True

    def test_validate_token(self):
        ae = svc.AuthenticationEngine()
        result = ae.authenticate(AuthScheme.API_KEY, {"api_key": "k", "client_id": "c"})
        assert ae.validate_token(result.token.token_id) is True

    def test_revoke_token(self):
        ae = svc.AuthenticationEngine()
        result = ae.authenticate(AuthScheme.API_KEY, {"api_key": "k", "client_id": "c"})
        ae.revoke_token(result.token.token_id)
        assert ae.validate_token(result.token.token_id) is False

    def test_stats(self):
        ae = svc.AuthenticationEngine()
        ae.authenticate(AuthScheme.API_KEY, {"api_key": "k"})
        ae.authenticate(AuthScheme.API_KEY, {})
        st = ae.stats
        assert st["success"] >= 1
        assert st["failure"] >= 1


class TestAuthorizationEngine:
    def _policy(self, principal="user1", operations=None, allow=True, service_type=None):
        ops = operations or (ConnectorOperation.PUBLISH,)
        return svc.AuthorizationPolicy(
            policy_id    = f"pol-{uuid.uuid4().hex[:6]}",
            principal    = principal,
            service_type = service_type,
            operations   = tuple(ops),
            allow        = allow,
        )

    def test_default_allow(self):
        azn = svc.AuthorizationEngine(default_allow=True)
        result = azn.authorize("user1", ConnectorOperation.QUERY)
        assert result.allowed is True

    def test_default_deny(self):
        azn = svc.AuthorizationEngine(default_allow=False)
        result = azn.authorize("user1", ConnectorOperation.QUERY)
        assert result.allowed is False

    def test_allow_policy_match(self):
        azn = svc.AuthorizationEngine(default_allow=False)
        azn.add_policy(self._policy("user1", [ConnectorOperation.PUBLISH], allow=True))
        result = azn.authorize("user1", ConnectorOperation.PUBLISH)
        assert result.allowed is True

    def test_deny_policy_match(self):
        azn = svc.AuthorizationEngine(default_allow=True)
        azn.add_policy(self._policy("user1", [ConnectorOperation.PUBLISH], allow=False))
        result = azn.authorize("user1", ConnectorOperation.PUBLISH)
        assert result.allowed is False

    def test_wildcard_principal(self):
        azn = svc.AuthorizationEngine(default_allow=False)
        azn.add_policy(self._policy("*", [ConnectorOperation.HEALTH_CHECK], allow=True))
        result = azn.authorize("any-user", ConnectorOperation.HEALTH_CHECK)
        assert result.allowed is True

    def test_remove_policy(self):
        azn = svc.AuthorizationEngine()
        pol = self._policy()
        azn.add_policy(pol)
        removed = azn.remove_policy(pol.policy_id)
        assert removed is True


class TestCredentialProvider:
    def test_store_and_retrieve(self):
        cp = svc.CredentialProvider()
        cid = cp.store(AuthScheme.API_KEY, "my-connector", {"api_key": "secret"})
        entry = cp.retrieve(cid)
        assert entry is not None
        assert entry.credentials["api_key"] == "secret"

    def test_safe_repr_hides_secrets(self):
        cp = svc.CredentialProvider()
        cid = cp.store(AuthScheme.API_KEY, "c", {"api_key": "my-secret", "client_id": "app"})
        entry = cp.retrieve(cid)
        safe = entry.safe_repr()
        assert safe["api_key"] == "***"
        assert safe.get("client_id") == "app"

    def test_delete(self):
        cp = svc.CredentialProvider()
        cid = cp.store(AuthScheme.BASIC, "c", {"username": "u", "password": "p"})
        ok = cp.delete(cid)
        assert ok is True
        assert cp.retrieve(cid) is None

    def test_count(self):
        cp = svc.CredentialProvider()
        cp.store(AuthScheme.NONE, "c1", {})
        cp.store(AuthScheme.NONE, "c2", {})
        assert cp.count == 2


class TestSecretManager:
    def test_set_and_get(self):
        sm = svc.SecretManager()
        sm.set_secret("db-pass", "secret123")
        val = sm.get_secret("db-pass")
        assert val == "secret123"

    def test_rotate(self):
        sm = svc.SecretManager()
        sm.set_secret("db-pass", "old-password")
        sm.rotate_secret("db-pass", "new-password")
        val = sm.get_secret("db-pass")
        assert val == "new-password"

    def test_version_history(self):
        sm = svc.SecretManager()
        v1 = sm.set_secret("key", "val1")
        v2 = sm.set_secret("key", "val2")
        assert sm.get_secret("key", version_id=v1) == "val1"
        assert sm.get_secret("key", version_id=v2) == "val2"

    def test_delete(self):
        sm = svc.SecretManager()
        sm.set_secret("temp", "value")
        ok = sm.delete_secret("temp")
        assert ok is True
        assert sm.get_secret("temp") is None

    def test_missing_returns_none(self):
        sm = svc.SecretManager()
        assert sm.get_secret("nonexistent") is None


class TestCertificateManager:
    def test_register_and_get(self):
        cm = svc.CertificateManager()
        entry = cm.register(
            common_name = "test.example.com",
            certificate = "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
            private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----",
        )
        found = cm.get(entry.cert_id)
        assert found is not None
        assert found.common_name == "test.example.com"

    def test_safe_repr_no_private_key(self):
        cm = svc.CertificateManager()
        entry = cm.register("cn", "CERT", "PRIVATE_KEY")
        sr = entry.safe_repr()
        assert "private_key" not in sr

    def test_revoke(self):
        cm = svc.CertificateManager()
        entry = cm.register("cn", "CERT", "KEY")
        ok = cm.revoke(entry.cert_id)
        assert ok is True
        assert cm.get(entry.cert_id).revoked is True

    def test_list_valid_only(self):
        cm = svc.CertificateManager()
        e1 = cm.register("cn1", "C1", "K1")
        e2 = cm.register("cn2", "C2", "K2")
        cm.revoke(e1.cert_id)
        valid = cm.list_certs(include_revoked=False)
        assert all(not e.revoked for e in valid)
        assert cm.valid_count == 1


# ════════════════════════════════════════════════════════════════════════
# K — Resilience
# ════════════════════════════════════════════════════════════════════════


class TestRetryEngine:
    def test_success_on_first_try(self):
        re = svc.RetryEngine()
        result = re.execute(lambda: 42)
        assert result.success is True
        assert result.result == 42
        assert result.total_attempts == 1

    def test_success_after_retry(self):
        counter = {"n": 0}
        def fn():
            counter["n"] += 1
            if counter["n"] < 2:
                raise RuntimeError("transient")
            return "done"
        from iios.integration.services.retry_engine import RetryConfig
        re = svc.RetryEngine(RetryConfig(max_attempts=3, strategy=RetryStrategy.IMMEDIATE))
        result = re.execute(fn)
        assert result.success is True
        assert result.total_attempts == 2

    def test_exhausted_returns_failure(self):
        re = svc.RetryEngine()
        from iios.integration.services.retry_engine import RetryConfig
        result = re.execute(
            lambda: (_ for _ in ()).throw(RuntimeError("always fails")),  # type: ignore
            config=RetryConfig(max_attempts=2, strategy=RetryStrategy.IMMEDIATE),
        )
        assert result.success is False
        assert result.total_attempts == 2

    def test_fibonacci_strategy(self):
        from iios.integration.services.retry_engine import RetryConfig, RetryEngine
        re = RetryEngine(RetryConfig(max_attempts=1, strategy=RetryStrategy.FIBONACCI))
        result = re.execute(lambda: "ok")
        assert result.success is True

    def test_fixed_delay_strategy(self):
        from iios.integration.services.retry_engine import RetryConfig, RetryEngine
        re = RetryEngine(RetryConfig(max_attempts=1, strategy=RetryStrategy.FIXED_DELAY, delay_ms=0))
        result = re.execute(lambda: "ok")
        assert result.success is True


class TestFailoverEngine:
    def test_primary_endpoint_used(self):
        fe = svc.FailoverEngine()
        fe.add_endpoint("primary", "https://primary.example.com", priority=0)
        result = fe.execute(lambda addr: f"called {addr}")
        assert result.success is True
        assert "primary" in result.endpoint_used

    def test_failover_to_secondary(self):
        fe = svc.FailoverEngine(failure_threshold=1)
        fe.add_endpoint("primary",   "https://p.example.com", priority=0)
        fe.add_endpoint("secondary", "https://s.example.com", priority=1)
        calls = {"n": 0}
        def fn(addr):
            calls["n"] += 1
            if "p.example.com" in addr:
                raise RuntimeError("primary down")
            return "secondary response"
        result = fe.execute(fn)
        assert result.success is True
        assert "s.example.com" in result.endpoint_used

    def test_all_endpoints_exhausted(self):
        fe = svc.FailoverEngine(failure_threshold=1)
        fe.add_endpoint("ep1", "https://ep1.example.com", priority=0)
        result = fe.execute(lambda addr: (_ for _ in ()).throw(RuntimeError("down")))  # type: ignore
        assert result.success is False

    def test_no_endpoints(self):
        fe = svc.FailoverEngine()
        result = fe.execute(lambda addr: "ok")
        assert result.success is False

    def test_health_status(self):
        fe = svc.FailoverEngine()
        fe.add_endpoint("ep1", "a1", priority=0)
        assert fe.health_status() == HealthStatus.HEALTHY


class TestRateLimitEngine:
    def test_allow_within_limit(self):
        rle = svc.RateLimitEngine()
        result = rle.acquire("test-key")
        assert result.allowed is True

    def test_reject_when_depleted(self):
        from iios.integration.services.rate_limit_engine import RateLimitConfig
        rle = svc.RateLimitEngine()
        rle.configure("tight", RateLimitConfig(rps=1000, burst=2))
        rle.acquire("tight")
        rle.acquire("tight")
        result = rle.acquire("tight")
        # 3rd acquire from burst=2 bucket should fail
        assert result.allowed is False

    def test_stats(self):
        rle = svc.RateLimitEngine()
        rle.acquire("k")
        st = rle.stats
        assert st["allowed"] >= 1


class TestTimeoutEngine:
    def test_success_within_budget(self):
        te = svc.TimeoutEngine()
        result = te.execute(lambda: "fast", timeout_ms=5_000)
        assert result.success is True
        assert result.result == "fast"
        assert result.timed_out is False

    def test_timeout_exceeded(self):
        te = svc.TimeoutEngine()
        result = te.execute(lambda: time.sleep(5), timeout_ms=50)
        assert result.timed_out is True

    def test_exception_in_fn(self):
        te = svc.TimeoutEngine()
        result = te.execute(lambda: (_ for _ in ()).throw(ValueError("bad")), timeout_ms=2_000)  # type: ignore
        assert result.success is False
        assert "bad" in result.error

    def test_stats(self):
        te = svc.TimeoutEngine()
        te.execute(lambda: "ok")
        te.execute(lambda: time.sleep(5), timeout_ms=20)
        st = te.stats
        assert st["successful"] >= 1
        assert st["timed_out"] >= 1


class TestConnectionPool:
    def test_acquire_and_release(self):
        pool = svc.ConnectionPool("test-pool", min_size=2, max_size=5)
        slot = pool.acquire()
        assert slot.state.value == "connected"
        pool.release(slot)
        assert pool.stats().available >= 1

    def test_max_pool_size_enforced(self):
        pool = svc.ConnectionPool("tiny", min_size=1, max_size=2)
        s1 = pool.acquire()
        s2 = pool.acquire()
        with pytest.raises(RuntimeError):
            pool.acquire(timeout_ms=50)
        pool.release(s1)
        pool.release(s2)

    def test_invalidate_slot(self):
        pool = svc.ConnectionPool("pool-x", min_size=1, max_size=3)
        slot = pool.acquire()
        pool.invalidate(slot)
        st = pool.stats()
        assert st.in_use == 0

    def test_stats(self):
        pool = svc.ConnectionPool("stats-pool", min_size=3, max_size=10)
        st = pool.stats()
        assert st.total_slots >= 3
        assert st.available >= 1


# ════════════════════════════════════════════════════════════════════════
# L — Observability
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationServicesValidator:
    def _make_valid_request(self):
        return ConnectorRequest.create(
            approved_request_id = "val-test",
            service_type        = ServiceType.REST_API,
            endpoint            = "https://api.example.com",
            timeout_ms          = 5_000,
        )

    def test_valid_request_passes(self):
        v = svc.IntegrationServicesValidator()
        report = v.validate(self._make_valid_request())
        assert report.passed is True

    def test_zero_timeout_fails(self):
        v = svc.IntegrationServicesValidator()
        req = ConnectorRequest.create(
            approved_request_id = "val-to",
            service_type        = ServiceType.REST_API,
            endpoint            = "https://api.example.com",
            timeout_ms          = 0,
        )
        report = v.validate(req)
        assert report.passed is False
        assert any(i.check == ServiceValidationCheck.RESPONSE_INTEGRITY for i in report.errors)

    def test_empty_endpoint_fails(self):
        v = svc.IntegrationServicesValidator()
        req = ConnectorRequest.create(
            approved_request_id = "val-ep",
            service_type        = ServiceType.REST_API,
            endpoint            = "",
            timeout_ms          = 5_000,
        )
        report = v.validate(req)
        assert report.passed is False

    def test_report_has_checked_at(self):
        v   = svc.IntegrationServicesValidator()
        rep = v.validate(self._make_valid_request())
        assert rep.checked_at


class TestIntegrationServicesStatistics:
    def test_record_and_snapshot(self):
        st = svc.IntegrationServicesStatistics()
        st.record_request(success=True,  latency_ms=10.0)
        st.record_request(success=True,  latency_ms=20.0)
        st.record_request(success=False, latency_ms=5.0)
        snap = st.snapshot()
        assert snap.requests_processed   == 3
        assert snap.failure_count        == 1
        assert snap.average_latency_ms   == pytest.approx(35.0 / 3, rel=1e-6)
        assert snap.availability         == pytest.approx(2/3,       rel=1e-6)

    def test_10_metrics_present(self):
        st = svc.IntegrationServicesStatistics()
        snap = st.snapshot()
        d = snap.as_dict()
        assert len(d) == 11  # 10 metrics + generated_at

    def test_increment_counters(self):
        st = svc.IntegrationServicesStatistics()
        st.increment_connectors(3)
        st.increment_adapters(2)
        st.increment_connections(5)
        st.record_message()
        st.record_event()
        snap = st.snapshot()
        assert snap.connectors_active  == 3
        assert snap.adapters_loaded    == 2
        assert snap.connections_open   == 5
        assert snap.messages_delivered == 1
        assert snap.events_published   == 1

    def test_reset(self):
        st = svc.IntegrationServicesStatistics()
        st.record_request(success=True, latency_ms=10)
        st.reset()
        snap = st.snapshot()
        assert snap.requests_processed == 0


class TestIntegrationServicesHistory:
    def _make_pair(self, success=True):
        req = ConnectorRequest.create(
            approved_request_id = "h-test",
            service_type        = ServiceType.REST_API,
            endpoint            = "https://api.example.com",
        )
        resp = (ConnectorResponse.success(req.request_id, latency_ms=5.0)
                if success else
                ConnectorResponse.failure(req.request_id, error_message="test-failure"))
        return req, resp

    def test_record_and_recent(self):
        h = svc.IntegrationServicesHistory()
        req, resp = self._make_pair()
        h.record(req, resp)
        recent = h.recent(5)
        assert len(recent) == 1

    def test_bounded_at_max_size(self):
        h = svc.IntegrationServicesHistory(max_size=3)
        for _ in range(5):
            req, resp = self._make_pair()
            h.record(req, resp)
        assert h.size == 3

    def test_report(self):
        h = svc.IntegrationServicesHistory()
        for _ in range(3):
            req, resp = self._make_pair(success=True)
            h.record(req, resp)
        req, resp = self._make_pair(success=False)
        h.record(req, resp)
        rep = h.report()
        assert rep.total_entries == 4
        assert rep.successful    == 3
        assert rep.failed        == 1

    def test_failed_filter(self):
        h = svc.IntegrationServicesHistory()
        req, resp = self._make_pair(success=False)
        h.record(req, resp)
        req2, resp2 = self._make_pair(success=True)
        h.record(req2, resp2)
        assert len(h.failed()) == 1


class TestIntegrationServicesEventBus:
    def test_subscribe_emit(self):
        bus = svc.IntegrationServicesEventBus()
        received: List[Any] = []
        bus.subscribe(ServiceEventType.CONNECTOR_LOADED, lambda e: received.append(e))
        n = bus.emit(ServiceEventType.CONNECTOR_LOADED, "test", {"k": "v"})
        assert n == 1
        assert received[0].event_type == ServiceEventType.CONNECTOR_LOADED

    def test_all_10_event_types_publishable(self):
        bus = svc.IntegrationServicesEventBus()
        for et in ServiceEventType:
            n = bus.emit(et, "test", {})
            assert n == 0  # no handlers

    def test_history_bounded(self):
        bus = svc.IntegrationServicesEventBus(max_history=3)
        for _ in range(5):
            bus.emit(ServiceEventType.CONNECTION_OPENED, "test", {})
        assert len(bus.history()) == 3

    def test_history_by_type(self):
        bus = svc.IntegrationServicesEventBus()
        bus.emit(ServiceEventType.CONNECTOR_LOADED, "s", {})
        bus.emit(ServiceEventType.MESSAGE_PUBLISHED, "s", {})
        items = bus.history_by_type(ServiceEventType.CONNECTOR_LOADED)
        assert len(items) == 1

    def test_handler_exception_suppressed(self):
        bus = svc.IntegrationServicesEventBus()
        bus.subscribe(ServiceEventType.CONNECTOR_LOADED,
                      lambda e: (_ for _ in ()).throw(RuntimeError("boom")))  # type: ignore
        n = bus.emit(ServiceEventType.CONNECTOR_LOADED, "s", {})
        assert n == 0

    def test_stats(self):
        bus = svc.IntegrationServicesEventBus()
        bus.emit(ServiceEventType.CONNECTION_OPENED, "s", {})
        st = bus.stats
        assert st["published"] >= 1


# ════════════════════════════════════════════════════════════════════════
# M — Factory
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationServicesFactory:
    def test_create_rest_request(self):
        req = svc.IntegrationServicesFactory.create_rest_request(
            endpoint="https://api.example.com",
            payload={"symbol": "NIFTY"},
            http_method="GET",
        )
        assert req.service_type == ServiceType.REST_API
        assert req.payload["symbol"] == "NIFTY"

    def test_create_kafka_request(self):
        req = svc.IntegrationServicesFactory.create_kafka_request(
            "trade-signals", {"sym": "NIFTY"}, operation="produce"
        )
        assert req.service_type == ServiceType.KAFKA
        assert req.connector_config["kafka_topic"] == "trade-signals"

    def test_create_rabbitmq_request(self):
        req = svc.IntegrationServicesFactory.create_rabbitmq_request(
            "signals", "trade.buy", {"sym": "BANKNIFTY"}
        )
        assert req.service_type == ServiceType.RABBITMQ

    def test_create_webhook_request(self):
        req = svc.IntegrationServicesFactory.create_webhook_request("trade.exec", {"x": 1})
        assert req.service_type == ServiceType.WEBHOOK

    def test_create_notification_request_email(self):
        req = svc.IntegrationServicesFactory.create_notification_request(
            "email", "u@example.com", "Alert", "Body text"
        )
        assert req.service_type == ServiceType.EMAIL

    def test_create_retry_engine(self):
        re = svc.IntegrationServicesFactory.create_retry_engine(
            max_attempts=5, strategy=RetryStrategy.FIBONACCI
        )
        assert isinstance(re, svc.RetryEngine)

    def test_create_connection_pool(self):
        pool = svc.IntegrationServicesFactory.create_connection_pool("my-pool", min_size=2, max_size=10)
        assert isinstance(pool, svc.ConnectionPool)
        assert pool.name == "my-pool"

    def test_create_message_bus(self):
        assert isinstance(svc.IntegrationServicesFactory.create_message_bus(), svc.MessageBusEngine)

    def test_create_event_bus(self):
        assert isinstance(svc.IntegrationServicesFactory.create_event_bus(), svc.EventBusEngine)

    def test_create_stream_engine(self):
        assert isinstance(svc.IntegrationServicesFactory.create_stream_engine(), svc.StreamEngine)

    def test_create_queue_engine(self):
        assert isinstance(svc.IntegrationServicesFactory.create_queue_engine(), svc.QueueEngine)

    def test_create_webhook_engine(self):
        assert isinstance(svc.IntegrationServicesFactory.create_webhook_engine(), svc.WebhookEngine)

    def test_create_notification_engine(self):
        assert isinstance(svc.IntegrationServicesFactory.create_notification_engine(), svc.NotificationEngine)


# ════════════════════════════════════════════════════════════════════════
# N — Central engine
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationServicesEngine:
    def _make_engine(self):
        engine = svc.IntegrationServicesEngine()
        engine.start()
        return engine

    def _rest_req(self, **kwargs):
        return svc.IntegrationServicesFactory.create_rest_request(
            endpoint="https://api.example.com", **kwargs
        )

    def test_start_stop(self):
        engine = svc.IntegrationServicesEngine()
        engine.start()
        assert engine.status().running is True
        engine.stop()
        assert engine.status().running is False

    def test_execute_rest(self):
        engine = self._make_engine()
        resp = engine.execute(self._rest_req())
        assert resp.status.value == "success"
        engine.stop()

    def test_execute_kafka(self):
        engine = self._make_engine()
        req = svc.IntegrationServicesFactory.create_kafka_request("t", {"s": "n"})
        resp = engine.execute(req)
        assert resp.status.value == "success"
        engine.stop()

    def test_execute_rabbitmq(self):
        engine = self._make_engine()
        req = svc.IntegrationServicesFactory.create_rabbitmq_request("ex", "rk", {})
        resp = engine.execute(req)
        assert resp.status.value == "success"
        engine.stop()

    def test_execute_webhook(self):
        engine = self._make_engine()
        req = svc.IntegrationServicesFactory.create_webhook_request("ev", {})
        resp = engine.execute(req)
        assert resp.status.value == "success"
        engine.stop()

    def test_execute_database(self):
        engine = self._make_engine()
        req = ConnectorRequest.create(
            approved_request_id = "db-engine-test",
            service_type        = ServiceType.DATABASE,
            endpoint            = "db://localhost/mydb",
            connector_config    = {"db_operation": "query", "db_sql": "SELECT 1"},
        )
        resp = engine.execute(req)
        assert resp.status.value == "success"
        engine.stop()

    def test_execute_notification(self):
        engine = self._make_engine()
        req = svc.IntegrationServicesFactory.create_notification_request(
            "email", "u@example.com", "Subject", "Body"
        )
        resp = engine.execute(req)
        assert resp.status.value == "success"
        engine.stop()

    def test_validation_failure_on_zero_timeout(self):
        engine = self._make_engine()
        req = ConnectorRequest.create(
            approved_request_id = "val-fail",
            service_type        = ServiceType.REST_API,
            endpoint            = "https://api.example.com",
            timeout_ms          = 0,
        )
        resp = engine.execute(req)
        assert resp.status.value == "failure"
        engine.stop()

    def test_statistics_record_requests(self):
        engine = self._make_engine()
        for _ in range(5):
            engine.execute(self._rest_req())
        snap = engine.statistics.snapshot()
        assert snap.requests_processed == 5
        engine.stop()

    def test_history_records_entries(self):
        engine = self._make_engine()
        engine.execute(self._rest_req())
        engine.execute(self._rest_req())
        assert engine.history.size == 2
        engine.stop()

    def test_event_bus_completion_events(self):
        engine = self._make_engine()
        received: List[Any] = []
        engine.event_bus.subscribe(
            ServiceEventType.INTEGRATION_SERVICE_COMPLETED,
            lambda e: received.append(e)
        )
        engine.execute(self._rest_req())
        assert len(received) == 1
        engine.stop()

    def test_execute_batch(self):
        engine = self._make_engine()
        reqs = [self._rest_req() for _ in range(5)]
        resps = engine.execute_batch(reqs)
        assert len(resps) == 5
        assert all(r.status.value == "success" for r in resps)
        engine.stop()

    def test_status(self):
        engine = self._make_engine()
        st = engine.status()
        assert st.version == "1.0.0"
        assert st.running is True
        engine.stop()

    def test_authentication_enforced(self):
        engine = self._make_engine()
        req = ConnectorRequest.create(
            approved_request_id = "auth-test",
            service_type        = ServiceType.REST_API,
            endpoint            = "https://secure.api.com",
            auth_scheme         = AuthScheme.API_KEY,
            auth_config         = {"api_key": "valid-key", "client_id": "app"},
        )
        resp = engine.execute(req)
        assert resp.status.value == "success"
        engine.stop()

    def test_auth_failure_blocks_execution(self):
        engine = self._make_engine()
        req = ConnectorRequest.create(
            approved_request_id = "auth-fail",
            service_type        = ServiceType.REST_API,
            endpoint            = "https://secure.api.com",
            auth_scheme         = AuthScheme.API_KEY,
            auth_config         = {},   # missing api_key
        )
        resp = engine.execute(req)
        assert resp.status.value == "failure"
        engine.stop()


# ════════════════════════════════════════════════════════════════════════
# O — Concurrency & stress
# ════════════════════════════════════════════════════════════════════════


class TestConcurrency:
    def test_engine_concurrent_requests(self):
        engine = svc.IntegrationServicesEngine()
        engine.start()
        errors: List[Exception] = []
        results: List[ConnectorResponse] = []
        lock = threading.Lock()

        def worker():
            try:
                req  = svc.IntegrationServicesFactory.create_rest_request(
                    endpoint="https://api.example.com", payload={"t": time.time()}
                )
                resp = engine.execute(req)
                with lock:
                    results.append(resp)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 20
        assert all(r.status.value == "success" for r in results)
        engine.stop()

    def test_queue_concurrent_enqueue_dequeue(self):
        q = svc.QueueEngine()
        q.create_queue("concurrent-q")
        enqueued: List[Any] = []
        dequeued: List[Any] = []
        lock = threading.Lock()

        def producer():
            for _ in range(50):
                msg = q.enqueue("concurrent-q", {"n": time.time()})
                if msg:
                    with lock:
                        enqueued.append(msg)

        def consumer():
            for _ in range(10):
                msgs = q.dequeue("concurrent-q", max_count=5)
                with lock:
                    dequeued.extend(msgs)
                time.sleep(0.001)

        threads = [threading.Thread(target=producer) for _ in range(3)]
        threads += [threading.Thread(target=consumer) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        # Just verify no crash — counts may vary
        assert len(enqueued) > 0

    def test_event_bus_concurrent_publish(self):
        bus = svc.EventBusEngine()
        counts: List[int] = []
        lock = threading.Lock()

        def handler(event):
            with lock:
                counts.append(1)

        bus.subscribe("load-test", handler)

        def worker():
            for _ in range(25):
                bus.publish_to("load-test", "test", {})

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(counts) == 100

    def test_connection_pool_concurrent_acquire_release(self):
        pool = svc.ConnectionPool("stress-pool", min_size=5, max_size=20)
        errors: List[Exception] = []
        lock = threading.Lock()

        def worker():
            for _ in range(5):
                try:
                    slot = pool.acquire(timeout_ms=2_000)
                    time.sleep(0.001)
                    pool.release(slot)
                except Exception as exc:
                    with lock:
                        errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        assert len(errors) == 0

    def test_stress_1000_requests(self):
        engine = svc.IntegrationServicesEngine()
        engine.start()
        for _ in range(1000):
            req  = svc.IntegrationServicesFactory.create_rest_request(
                endpoint="https://api.example.com"
            )
            resp = engine.execute(req)
            assert resp.status.value == "success"
        snap = engine.statistics.snapshot()
        assert snap.requests_processed == 1000
        assert snap.failure_count      == 0
        engine.stop()


# ════════════════════════════════════════════════════════════════════════
# P — Regression
# ════════════════════════════════════════════════════════════════════════


class TestRegression:
    def test_no_circular_imports(self):
        """Verify iios.integration.services does not import from policies or engine."""
        import importlib, sys
        # Remove cached modules to force fresh import check
        for key in list(sys.modules.keys()):
            if "integration.services" in key:
                del sys.modules[key]
        import iios.integration.services  # must not raise
        # Check none of the services modules import from policies
        for key, mod in sys.modules.items():
            if "iios.integration.services" in key and hasattr(mod, "__file__"):
                if mod.__file__:
                    with open(mod.__file__, "r", encoding="utf-8", errors="ignore") as f:
                        src = f.read()
                    assert "iios.integration.policies" not in src, \
                        f"{key} imports from policies (circular)"
                    assert "iios.integration.engine" not in src, \
                        f"{key} imports from engine (circular)"

    def test_no_vendor_sdk_imports(self):
        """Verify no vendor SDKs are imported anywhere in the services package."""
        import sys
        FORBIDDEN = ["requests", "httpx", "aiohttp", "kafka", "pika", "redis",
                     "boto3", "google.cloud", "sqlalchemy", "pymysql", "psycopg2",
                     "paramiko", "ftplib", "smtplib", "twilio", "firebase_admin",
                     "grpc", "websockets"]
        for key, mod in sys.modules.items():
            if "iios.integration.services" in key and hasattr(mod, "__file__"):
                if mod.__file__:
                    with open(mod.__file__, "r", encoding="utf-8", errors="ignore") as f:
                        src = f.read()
                    for vendor in FORBIDDEN:
                        assert f"import {vendor}" not in src, \
                            f"{key} imports forbidden vendor SDK: {vendor}"

    def test_all_public_api_importable(self):
        """Every name in __all__ must be importable from the package."""
        import iios.integration.services as svc_mod
        for name in svc_mod.__all__:
            assert hasattr(svc_mod, name), f"__all__ member {name!r} not accessible"

    def test_connector_request_immutable_not_mutated_by_engine(self):
        """Engine must not mutate the input ConnectorRequest."""
        engine = svc.IntegrationServicesEngine()
        engine.start()
        req = svc.IntegrationServicesFactory.create_rest_request(
            endpoint="https://api.example.com", payload={"key": "original"}
        )
        original_payload = dict(req.payload)
        engine.execute(req)
        assert req.payload == original_payload
        engine.stop()

    def test_concurrent_statistics_no_race(self):
        """Statistics counter must not lose increments under concurrent load."""
        stats = svc.IntegrationServicesStatistics()
        def worker():
            for _ in range(100):
                stats.record_request(success=True, latency_ms=1.0)
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        snap = stats.snapshot()
        assert snap.requests_processed == 1000
