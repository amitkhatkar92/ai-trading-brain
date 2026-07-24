"""
iios.integration.services — Public API
========================================
Integration Services Framework — C15 Phase 1, Module 4

48 source files implementing provider-independent integration connectors,
adapters, messaging, authentication, resilience, and lifecycle management.
"""
from __future__ import annotations

# ── Constants ─────────────────────────────────────────────────────────
from .constants import (
    AdapterProtocol,
    AuthScheme,
    ConnectionState,
    ConnectorOperation,
    ConnectorStatus,
    DEFAULT_ENGINE_ID,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_QUEUE_SIZE,
    DEFAULT_POOL_MAX,
    DEFAULT_POOL_SIZE,
    DEFAULT_RATE_LIMIT_BURST,
    DEFAULT_RATE_LIMIT_RPS,
    DEFAULT_RETRY_COUNT,
    DEFAULT_RETRY_DELAY_MS,
    DEFAULT_RETRY_MAX_ATTEMPTS,
    DEFAULT_TIMEOUT_MS,
    FIBONACCI_DELAYS_MS,
    HealthStatus,
    MANAGER_SYSTEM_ID,
    MessageDeliveryMode,
    RetryStrategy,
    SERVICES_SYSTEM_ID,
    ServiceEventType,
    ServiceResponseStatus,
    ServiceType,
    ServiceValidationCheck,
    StreamMode,
    TransportType,
    VERSION,
    WORKFLOW_STAGES,
)

# ── Exceptions ────────────────────────────────────────────────────────
from .exceptions import (
    AdapterExecutionError,
    AdapterNotFoundError,
    AuthenticationError,
    AuthorizationError,
    ConnectionPoolExhausted,
    ConnectorExecutionError,
    ConnectorNotFoundError,
    IntegrationServiceError,
    ProtocolExecutionError,
    RateLimitExceeded,
    ServiceNotReadyError,
    ServiceTimeoutError,
    TransportError,
)

# ── Core data objects ─────────────────────────────────────────────────
from .connector_context import ConnectorContext
from .connector_request import ConnectorRequest
from .connector_response import ConnectorResponse

# ── Registry & management ─────────────────────────────────────────────
from .adapter_registry import AdapterDescriptor, AdapterRegistry
from .connector_registry import ConnectorDescriptor, ConnectorRegistry
from .connector_factory import ConnectorFactory
from .connector_manager import ConnectorManager
from .adapter_factory import AdapterFactory
from .protocol_registry import ProtocolDescriptor, ProtocolRegistry

# ── Engines ───────────────────────────────────────────────────────────
from .adapter_engine import AdapterEngine
from .connector_engine import ConnectorEngine
from .protocol_engine import ProtocolEngine
from .transport_engine import TransportEngine, TransportSession

# ── API clients ───────────────────────────────────────────────────────
from .http_client import BaseHttpClient, SimulatedHttpClient
from .rest_client import BaseRestClient, SimulatedRestClient
from .graphql_client import BaseGraphqlClient, SimulatedGraphqlClient
from .grpc_client import BaseGrpcClient, SimulatedGrpcClient
from .websocket_client import BaseWebSocketClient, SimulatedWebSocketClient

# ── API Gateway ───────────────────────────────────────────────────────
from .api_gateway_engine import ApiGatewayEngine

# ── Messaging adapters ────────────────────────────────────────────────
from .kafka_adapter import BaseKafkaAdapter, KafkaMessage, SimulatedKafkaAdapter
from .rabbitmq_adapter import AmqpMessage, BaseRabbitMQAdapter, SimulatedRabbitMQAdapter
from .redis_stream_adapter import (
    BaseRedisStreamAdapter,
    RedisStreamEntry,
    SimulatedRedisStreamAdapter,
)

# ── Messaging & streaming engines ─────────────────────────────────────
from .message_bus_engine import MessageBusEngine, MessageBusStats
from .event_bus_engine import EventBusEngine, IntegrationEvent
from .stream_engine import StreamEngine, StreamSession
from .queue_engine import QueueEngine, QueueMessage, QueueStats

# ── Specialized connector engines ─────────────────────────────────────
from .webhook_engine import WebhookDeliveryRecord, WebhookEndpoint, WebhookEngine
from .database_connector_engine import (
    BaseDatabaseConnector,
    DatabaseConnectorEngine,
    SimulatedDatabaseConnector,
)
from .file_transfer_engine import (
    BaseFileTransferAdapter,
    FileTransferEngine,
    SimulatedFileTransferAdapter,
    TransferRecord,
)
from .notification_engine import (
    BaseNotificationAdapter,
    NotificationEngine,
    NotificationRecord,
    SimulatedEmailAdapter,
    SimulatedPushAdapter,
    SimulatedSmsAdapter,
)

# ── Security ──────────────────────────────────────────────────────────
from .authentication_engine import AuthenticationEngine, AuthenticationResult, AuthToken
from .authorization_engine import (
    AuthorizationEngine,
    AuthorizationPolicy,
    AuthorizationResult,
)
from .credential_provider import CredentialEntry, CredentialProvider
from .secret_manager import SecretEntry, SecretManager, SecretVersion
from .certificate_manager import CertificateEntry, CertificateManager

# ── Resilience ────────────────────────────────────────────────────────
from .retry_engine import RetryAttempt, RetryConfig, RetryEngine, RetryResult
from .failover_engine import FailoverEndpoint, FailoverEngine, FailoverResult
from .rate_limit_engine import RateLimitConfig, RateLimitEngine, RateLimitResult
from .timeout_engine import TimeoutEngine, TimeoutResult
from .connection_pool import ConnectionPool, PoolSlot, PoolStats

# ── Observability ─────────────────────────────────────────────────────
from .integration_services_validator import (
    IntegrationServicesValidator,
    ServiceValidationIssue,
    ServiceValidationReport,
)
from .integration_services_statistics import (
    IntegrationServicesStatistics,
    ServicesStatisticsReport,
)
from .integration_services_history import (
    IntegrationServicesHistory,
    ServicesHistoryEntry,
    ServicesHistoryReport,
)
from .integration_services_events import (
    IntegrationServicesEventBus,
    ServiceEvent,
)

# ── Factory & central engine ──────────────────────────────────────────
from .integration_services_factory import IntegrationServicesFactory
from .integration_services_engine import EngineStatus, IntegrationServicesEngine


__all__ = [
    # constants
    "AdapterProtocol", "AuthScheme", "ConnectionState", "ConnectorOperation",
    "ConnectorStatus", "DEFAULT_ENGINE_ID", "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_QUEUE_SIZE", "DEFAULT_POOL_MAX", "DEFAULT_POOL_SIZE",
    "DEFAULT_RATE_LIMIT_BURST", "DEFAULT_RATE_LIMIT_RPS", "DEFAULT_RETRY_COUNT",
    "DEFAULT_RETRY_DELAY_MS", "DEFAULT_RETRY_MAX_ATTEMPTS", "DEFAULT_TIMEOUT_MS",
    "FIBONACCI_DELAYS_MS", "HealthStatus", "MANAGER_SYSTEM_ID",
    "MessageDeliveryMode", "RetryStrategy", "SERVICES_SYSTEM_ID",
    "ServiceEventType", "ServiceResponseStatus", "ServiceType",
    "ServiceValidationCheck", "StreamMode", "TransportType",
    "VERSION", "WORKFLOW_STAGES",
    # exceptions
    "AdapterExecutionError", "AdapterNotFoundError", "AuthenticationError",
    "AuthorizationError", "ConnectionPoolExhausted", "ConnectorExecutionError",
    "ConnectorNotFoundError", "IntegrationServiceError", "ProtocolExecutionError",
    "RateLimitExceeded", "ServiceNotReadyError", "ServiceTimeoutError", "TransportError",
    # core data
    "ConnectorContext", "ConnectorRequest", "ConnectorResponse",
    # registry & management
    "AdapterDescriptor", "AdapterRegistry", "ConnectorDescriptor", "ConnectorRegistry",
    "ConnectorFactory", "ConnectorManager", "AdapterFactory",
    "ProtocolDescriptor", "ProtocolRegistry",
    # engines
    "AdapterEngine", "ConnectorEngine", "ProtocolEngine",
    "TransportEngine", "TransportSession",
    # clients
    "BaseHttpClient", "SimulatedHttpClient",
    "BaseRestClient", "SimulatedRestClient",
    "BaseGraphqlClient", "SimulatedGraphqlClient",
    "BaseGrpcClient", "SimulatedGrpcClient",
    "BaseWebSocketClient", "SimulatedWebSocketClient",
    # gateway
    "ApiGatewayEngine",
    # messaging adapters
    "BaseKafkaAdapter", "KafkaMessage", "SimulatedKafkaAdapter",
    "AmqpMessage", "BaseRabbitMQAdapter", "SimulatedRabbitMQAdapter",
    "BaseRedisStreamAdapter", "RedisStreamEntry", "SimulatedRedisStreamAdapter",
    # messaging engines
    "MessageBusEngine", "MessageBusStats",
    "EventBusEngine", "IntegrationEvent",
    "StreamEngine", "StreamSession",
    "QueueEngine", "QueueMessage", "QueueStats",
    # specialized engines
    "WebhookDeliveryRecord", "WebhookEndpoint", "WebhookEngine",
    "BaseDatabaseConnector", "DatabaseConnectorEngine", "SimulatedDatabaseConnector",
    "BaseFileTransferAdapter", "FileTransferEngine",
    "SimulatedFileTransferAdapter", "TransferRecord",
    "BaseNotificationAdapter", "NotificationEngine", "NotificationRecord",
    "SimulatedEmailAdapter", "SimulatedPushAdapter", "SimulatedSmsAdapter",
    # security
    "AuthenticationEngine", "AuthenticationResult", "AuthToken",
    "AuthorizationEngine", "AuthorizationPolicy", "AuthorizationResult",
    "CredentialEntry", "CredentialProvider",
    "SecretEntry", "SecretManager", "SecretVersion",
    "CertificateEntry", "CertificateManager",
    # resilience
    "RetryAttempt", "RetryConfig", "RetryEngine", "RetryResult",
    "FailoverEndpoint", "FailoverEngine", "FailoverResult",
    "RateLimitConfig", "RateLimitEngine", "RateLimitResult",
    "TimeoutEngine", "TimeoutResult",
    "ConnectionPool", "PoolSlot", "PoolStats",
    # observability
    "IntegrationServicesValidator", "ServiceValidationIssue", "ServiceValidationReport",
    "IntegrationServicesStatistics", "ServicesStatisticsReport",
    "IntegrationServicesHistory", "ServicesHistoryEntry", "ServicesHistoryReport",
    "IntegrationServicesEventBus", "ServiceEvent",
    # factory & engine
    "IntegrationServicesFactory",
    "EngineStatus", "IntegrationServicesEngine",
]
