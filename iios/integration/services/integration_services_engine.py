"""
integration_services_engine.py — iios.integration.services
------------------------------------------------------------
IntegrationServicesEngine — central coordinator for the Integration
Services Framework.

Receives a ConnectorRequest, routes it through the correct sub-engine,
applies authentication / rate-limiting / retry, records statistics and
history, and publishes lifecycle events.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .api_gateway_engine import ApiGatewayEngine
from .authentication_engine import AuthenticationEngine
from .connector_context import ConnectorContext
from .connector_engine import ConnectorEngine
from .connector_request import ConnectorRequest
from .connector_response import ConnectorResponse
from .constants import (
    AuthScheme,
    DEFAULT_ENGINE_ID,
    SERVICES_SYSTEM_ID,
    ServiceEventType,
    ServiceType,
    VERSION,
)
from .database_connector_engine import DatabaseConnectorEngine
from .file_transfer_engine import FileTransferEngine
from .integration_services_events import IntegrationServicesEventBus
from .integration_services_history import IntegrationServicesHistory
from .integration_services_statistics import IntegrationServicesStatistics
from .integration_services_validator import IntegrationServicesValidator
from .message_bus_engine import MessageBusEngine
from .notification_engine import NotificationEngine
from .rate_limit_engine import RateLimitConfig, RateLimitEngine
from .retry_engine import RetryEngine
from .webhook_engine import WebhookEngine

_log = get_logger(__name__)

# ── Service type → routing group ─────────────────────────────────────────
_MESSAGING_TYPES = {ServiceType.KAFKA, ServiceType.RABBITMQ, ServiceType.REDIS_STREAM,
                    ServiceType.MESSAGE_QUEUE}
_GATEWAY_TYPES   = {ServiceType.REST_API, ServiceType.GRAPHQL, ServiceType.GRPC,
                    ServiceType.WEBSOCKET, ServiceType.HTTP}
_WEBHOOK_TYPES   = {ServiceType.WEBHOOK}
_DATABASE_TYPES  = {ServiceType.DATABASE}
_FILE_TYPES      = {ServiceType.FILE_TRANSFER}
_NOTIFY_TYPES    = {ServiceType.EMAIL, ServiceType.SMS, ServiceType.PUSH_NOTIFICATION}


@dataclass
class EngineStatus:
    """Current status of the IntegrationServicesEngine."""
    engine_id:    str
    running:      bool
    version:      str
    started_at:   Optional[str]
    connectors:   int
    requests:     int
    uptime_s:     float


class IntegrationServicesEngine:
    """
    Central coordinator for the Integration Services Framework.

    Responsibilities:
    - Validate incoming ConnectorRequests
    - Route to the appropriate sub-engine (gateway / messaging / db / file / notify / webhook)
    - Apply authentication
    - Apply rate limiting
    - Trigger retry via RetryEngine
    - Record statistics, history, and lifecycle events
    """

    def __init__(
        self,
        engine_id:              Optional[str]                          = None,
        validator:              Optional[IntegrationServicesValidator]  = None,
        statistics:             Optional[IntegrationServicesStatistics] = None,
        history:                Optional[IntegrationServicesHistory]    = None,
        event_bus:              Optional[IntegrationServicesEventBus]   = None,
        connector_engine:       Optional[ConnectorEngine]               = None,
        api_gateway:            Optional[ApiGatewayEngine]              = None,
        message_bus:            Optional[MessageBusEngine]              = None,
        webhook_engine:         Optional[WebhookEngine]                 = None,
        database_engine:        Optional[DatabaseConnectorEngine]       = None,
        file_transfer:          Optional[FileTransferEngine]            = None,
        notification_engine:    Optional[NotificationEngine]            = None,
        auth_engine:            Optional[AuthenticationEngine]          = None,
        rate_limit_engine:      Optional[RateLimitEngine]               = None,
        retry_engine:           Optional[RetryEngine]                   = None,
    ) -> None:
        self._engine_id       = engine_id or DEFAULT_ENGINE_ID
        self._lock            = threading.Lock()
        self._running         = False
        self._started_at:     Optional[str] = None
        self._start_time:     Optional[float] = None
        self._requests        = 0

        # Sub-systems
        self._validator        = validator          or IntegrationServicesValidator()
        self._statistics       = statistics         or IntegrationServicesStatistics()
        self._history          = history            or IntegrationServicesHistory()
        self._event_bus        = event_bus          or IntegrationServicesEventBus()
        self._connector_engine = connector_engine   or ConnectorEngine()
        self._api_gateway      = api_gateway        or ApiGatewayEngine()
        self._message_bus      = message_bus        or MessageBusEngine()
        self._webhook_engine   = webhook_engine     or WebhookEngine()
        self._database_engine  = database_engine    or DatabaseConnectorEngine()
        self._file_transfer    = file_transfer      or FileTransferEngine()
        self._notification     = notification_engine or NotificationEngine()
        self._auth_engine      = auth_engine        or AuthenticationEngine()
        # Default rate limiter: 10_000 rps with large burst for framework validation.
        # Production deployments inject a stricter RateLimitEngine.
        self._rate_limiter     = rate_limit_engine  or RateLimitEngine(
            RateLimitConfig(rps=10_000, burst=10_000)
        )
        self._retry_engine     = retry_engine       or RetryEngine()

    # ── Lifecycle ────────────────────────────────────────────────────────

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running    = True
            self._started_at = datetime.now(timezone.utc).isoformat()
            self._start_time = time.monotonic()
        _log.debug(f"integration-services-engine {self._engine_id!r} started")
        self._event_bus.emit(
            ServiceEventType.CONNECTOR_LOADED,
            source  = SERVICES_SYSTEM_ID,
            payload = {"engine_id": self._engine_id, "version": VERSION},
        )

    def stop(self) -> None:
        with self._lock:
            self._running = False
        _log.debug(f"integration-services-engine {self._engine_id!r} stopped")

    # ── Request execution ────────────────────────────────────────────────

    def execute(self, request: ConnectorRequest) -> ConnectorResponse:
        """
        Execute a ConnectorRequest through the full service workflow.

        Returns a ConnectorResponse.
        """
        total_start = time.perf_counter_ns()

        # 1. Validate
        report = self._validator.validate(request)
        if not report.passed:
            errors = "; ".join(i.message for i in report.errors)
            return ConnectorResponse.failure(
                request.request_id,
                error_message=f"Validation failed: {errors}",
                adapter_id="services-engine",
            )

        # 2. Authenticate (if auth_scheme != NONE)
        if request.auth_scheme != AuthScheme.NONE:
            auth_result = self._auth_engine.authenticate(
                request.auth_scheme, request.auth_config
            )
            if not auth_result.success:
                return ConnectorResponse.failure(
                    request.request_id,
                    error_message=f"Authentication failed: {auth_result.error}",
                    adapter_id="services-engine",
                )
            self._event_bus.emit(
                ServiceEventType.AUTHENTICATION_SUCCEEDED,
                source  = SERVICES_SYSTEM_ID,
                payload = {"request_id": request.request_id,
                           "scheme": request.auth_scheme.value},
            )

        # 3. Rate limit
        rate_result = self._rate_limiter.acquire(
            key=request.service_type.value
        )
        if not rate_result.allowed:
            return ConnectorResponse.failure(
                request.request_id,
                error_message="Rate limit exceeded",
                adapter_id="services-engine",
            )

        # 4. Route + execute (with retry)
        response = self._execute_with_retry(request)

        # 5. Record stats
        total_ms = (time.perf_counter_ns() - total_start) / 1_000_000
        self._statistics.record_request(
            success    = (response.status.value == "success"),
            latency_ms = total_ms,
            retries    = response.retry_count,
        )

        # 6. Record history
        self._history.record(request, response)

        # 7. Emit completion event
        self._event_bus.emit(
            ServiceEventType.INTEGRATION_SERVICE_COMPLETED,
            source  = SERVICES_SYSTEM_ID,
            payload = {
                "request_id": request.request_id,
                "success":    response.status.value == "success",
                "latency_ms": total_ms,
            },
        )

        with self._lock:
            self._requests += 1

        return response

    def execute_batch(
        self,
        requests: List[ConnectorRequest],
    ) -> List[ConnectorResponse]:
        """Execute multiple requests sequentially."""
        return [self.execute(r) for r in requests]

    # ── Sub-system accessors ─────────────────────────────────────────────

    @property
    def validator(self)   -> IntegrationServicesValidator:  return self._validator
    @property
    def statistics(self)  -> IntegrationServicesStatistics: return self._statistics
    @property
    def history(self)     -> IntegrationServicesHistory:    return self._history
    @property
    def event_bus(self)   -> IntegrationServicesEventBus:   return self._event_bus
    @property
    def auth_engine(self) -> AuthenticationEngine:          return self._auth_engine
    @property
    def rate_limiter(self)-> RateLimitEngine:               return self._rate_limiter

    # ── Status ───────────────────────────────────────────────────────────

    def status(self) -> EngineStatus:
        with self._lock:
            uptime = (
                (time.monotonic() - self._start_time)
                if self._start_time else 0.0
            )
            return EngineStatus(
                engine_id  = self._engine_id,
                running    = self._running,
                version    = VERSION,
                started_at = self._started_at,
                connectors = self._connector_engine.connector_manager.active_count(),
                requests   = self._requests,
                uptime_s   = uptime,
            )

    # ── Internals ────────────────────────────────────────────────────────

    def _execute_with_retry(self, request: ConnectorRequest) -> ConnectorResponse:
        """Route and execute with retry support."""
        response_box: Dict[str, Any] = {}

        def _do_execute() -> None:
            response_box["value"] = self._route(request)
            status = response_box["value"].status.value
            if status not in ("success", "partial"):
                raise RuntimeError(response_box["value"].error_message)

        from .retry_engine import RetryConfig
        cfg = RetryConfig(
            max_attempts = max(1, request.retry_max_attempts),
            strategy     = request.retry_strategy,
        )
        retry_result = self._retry_engine.execute(_do_execute, config=cfg)

        if retry_result.success:
            resp = response_box.get("value")
            if resp is not None:
                return resp

        # If retry exhausted, build failure response
        if retry_result.total_attempts > 1:
            self._event_bus.emit(
                ServiceEventType.RETRY_TRIGGERED,
                source  = SERVICES_SYSTEM_ID,
                payload = {"attempts": retry_result.total_attempts,
                           "request_id": request.request_id},
            )

        return response_box.get("value") or ConnectorResponse.failure(
            request.request_id,
            error_message=retry_result.error,
            retry_count=retry_result.total_attempts,
            adapter_id="services-engine",
        )

    def _route(self, request: ConnectorRequest) -> ConnectorResponse:
        """Route a request to the appropriate sub-engine."""
        self._event_bus.emit(
            ServiceEventType.PROTOCOL_EXECUTED,
            source  = SERVICES_SYSTEM_ID,
            payload = {"service_type": request.service_type.value,
                       "request_id":  request.request_id},
        )

        if request.service_type in _MESSAGING_TYPES:
            response = self._message_bus.route(request)
            if response.status.value == "success":
                self._statistics.record_message()
                self._event_bus.emit(
                    ServiceEventType.MESSAGE_PUBLISHED,
                    source=SERVICES_SYSTEM_ID,
                    payload={"request_id": request.request_id,
                             "service_type": request.service_type.value},
                )
            return response

        if request.service_type in _WEBHOOK_TYPES:
            return self._webhook_engine.execute(request)

        if request.service_type in _DATABASE_TYPES:
            return self._database_engine.execute(request)

        if request.service_type in _FILE_TYPES:
            return self._file_transfer.execute(request)

        if request.service_type in _NOTIFY_TYPES:
            return self._notification.execute(request)

        # Default: API gateway (REST, GraphQL, gRPC, WS, HTTP, generic)
        return self._api_gateway.route(request)
