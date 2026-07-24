"""
constants.py — iios.integration.services
-----------------------------------------
Enums, type definitions, and constants for the
Integration Services Framework.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, List


# ════════════════════════════════════════════════════════════════════════
# Service Types  (22)
# ════════════════════════════════════════════════════════════════════════


class ServiceType(str, Enum):
    """22 enterprise integration service types."""
    REST_API         = "rest_api"
    GRAPHQL          = "graphql"
    GRPC             = "grpc"
    WEBSOCKET        = "websocket"
    HTTP             = "http"
    KAFKA            = "kafka"
    RABBITMQ         = "rabbitmq"
    REDIS_STREAM     = "redis_stream"
    MESSAGE_QUEUE    = "message_queue"
    EVENT_BUS        = "event_bus"
    STREAMING        = "streaming"
    WEBHOOK          = "webhook"
    DATABASE         = "database"
    FILE_TRANSFER    = "file_transfer"
    EMAIL            = "email"
    SMS              = "sms"
    PUSH_NOTIFICATION= "push_notification"
    CLOUD_CONNECTOR  = "cloud_connector"
    IDENTITY_PROVIDER= "identity_provider"
    BROKER_CONNECTOR = "broker_connector"
    MARKET_DATA      = "market_data"
    ENTERPRISE       = "enterprise"


# ════════════════════════════════════════════════════════════════════════
# Adapter Protocols  (18)
# ════════════════════════════════════════════════════════════════════════


class AdapterProtocol(str, Enum):
    """Protocols supported by adapter implementations."""
    REST         = "rest"
    GRAPHQL      = "graphql"
    GRPC         = "grpc"
    WEBSOCKET    = "websocket"
    HTTP         = "http"
    KAFKA        = "kafka"
    RABBITMQ     = "rabbitmq"
    REDIS        = "redis"
    DATABASE     = "database"
    FILE         = "file"
    EMAIL        = "email"
    SMS          = "sms"
    PUSH         = "push"
    CLOUD        = "cloud"
    IDENTITY     = "identity"
    BROKER       = "broker"
    MARKET_DATA  = "market_data"
    GENERIC      = "generic"


# ════════════════════════════════════════════════════════════════════════
# Transport Types  (9)
# ════════════════════════════════════════════════════════════════════════


class TransportType(str, Enum):
    """Transport-layer types."""
    HTTP             = "http"
    WEBSOCKET        = "websocket"
    GRPC             = "grpc"
    AMQP             = "amqp"
    KAFKA_PROTOCOL   = "kafka_protocol"
    REDIS_PROTOCOL   = "redis_protocol"
    FILE_SYSTEM      = "file_system"
    DATABASE_WIRE    = "database_wire"
    INTERNAL         = "internal"


# ════════════════════════════════════════════════════════════════════════
# Authentication Schemes  (8)
# ════════════════════════════════════════════════════════════════════════


class AuthScheme(str, Enum):
    """Supported authentication schemes."""
    NONE         = "none"
    API_KEY      = "api_key"
    BEARER_TOKEN = "bearer_token"
    BASIC        = "basic"
    OAUTH2       = "oauth2"
    MTLS         = "mtls"
    SAML         = "saml"
    CUSTOM       = "custom"


# ════════════════════════════════════════════════════════════════════════
# Connector Status  (7)
# ════════════════════════════════════════════════════════════════════════


class ConnectorStatus(str, Enum):
    """Lifecycle status of a connector instance."""
    IDLE       = "idle"
    CONNECTING = "connecting"
    CONNECTED  = "connected"
    EXECUTING  = "executing"
    DONE       = "done"
    FAILED     = "failed"
    CLOSED     = "closed"


# ════════════════════════════════════════════════════════════════════════
# Connection State  (5)
# ════════════════════════════════════════════════════════════════════════


class ConnectionState(str, Enum):
    """State of a connection in the pool."""
    IDLE       = "idle"
    CONNECTING = "connecting"
    CONNECTED  = "connected"
    FAILED     = "failed"
    CLOSED     = "closed"


# ════════════════════════════════════════════════════════════════════════
# Service Response Status  (6)
# ════════════════════════════════════════════════════════════════════════


class ServiceResponseStatus(str, Enum):
    """Status of an integration service execution response."""
    SUCCESS      = "success"
    FAILURE      = "failure"
    PARTIAL      = "partial"
    TIMEOUT      = "timeout"
    RATE_LIMITED = "rate_limited"
    AUTH_FAILED  = "auth_failed"


# ════════════════════════════════════════════════════════════════════════
# Retry Strategy  (4)
# ════════════════════════════════════════════════════════════════════════


class RetryStrategy(str, Enum):
    """Retry strategies for failed integration calls."""
    NO_RETRY            = "no_retry"
    IMMEDIATE           = "immediate"
    FIXED_DELAY         = "fixed_delay"
    LINEAR_BACKOFF      = "linear_backoff"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    FIBONACCI           = "fibonacci"


# ════════════════════════════════════════════════════════════════════════
# Service Event Types  (10)
# ════════════════════════════════════════════════════════════════════════


class ServiceEventType(str, Enum):
    """10 service lifecycle event types."""
    CONNECTOR_LOADED             = "connector_loaded"
    CONNECTION_OPENED            = "connection_opened"
    AUTHENTICATION_SUCCEEDED     = "authentication_succeeded"
    PROTOCOL_EXECUTED            = "protocol_executed"
    MESSAGE_PUBLISHED            = "message_published"
    EVENT_DELIVERED              = "event_delivered"
    CONNECTION_CLOSED            = "connection_closed"
    RETRY_TRIGGERED              = "retry_triggered"
    FAILOVER_TRIGGERED           = "failover_triggered"
    INTEGRATION_SERVICE_COMPLETED= "integration_service_completed"


# ════════════════════════════════════════════════════════════════════════
# System constants
# ════════════════════════════════════════════════════════════════════════

SERVICES_SYSTEM_ID  = "iios:integration:services"
MANAGER_SYSTEM_ID   = "iios:integration:services-manager"
VERSION             = "1.0.0"

DEFAULT_ENGINE_ID               = "iios-services-engine-default"
DEFAULT_MAX_CONNECTORS          = 500
DEFAULT_MAX_ADAPTERS            = 500
DEFAULT_MAX_PROTOCOLS           = 200
DEFAULT_MAX_HISTORY             = 5_000
DEFAULT_MAX_EVENTS              = 10_000
DEFAULT_POOL_SIZE               = 50
DEFAULT_RETRY_MAX_ATTEMPTS      = 3
DEFAULT_RETRY_DELAY_MS          = 1_000
DEFAULT_TIMEOUT_MS              = 30_000
DEFAULT_RATE_LIMIT_RPS          = 100
DEFAULT_RATE_LIMIT_BURST        = 10

WORKFLOW_STAGES: List[str] = [
    "receive_approved_request",
    "load_connector",
    "load_adapter",
    "initialize_transport",
    "authenticate",
    "establish_connection",
    "execute_protocol",
    "validate_response",
    "collect_metrics",
    "publish_execution_result",
]

# ════════════════════════════════════════════════════════════════════════
# Connector Operations  (11)
# ════════════════════════════════════════════════════════════════════════


class ConnectorOperation(str, Enum):
    """Operations a connector can perform."""
    SEND           = "send"
    RECEIVE        = "receive"
    QUERY          = "query"
    PUBLISH        = "publish"
    SUBSCRIBE      = "subscribe"
    AUTHENTICATE   = "authenticate"
    HEALTH_CHECK   = "health_check"
    STREAM         = "stream"
    UPLOAD         = "upload"
    DOWNLOAD       = "download"
    NOTIFY         = "notify"


# ════════════════════════════════════════════════════════════════════════
# Health Status
# ════════════════════════════════════════════════════════════════════════


class HealthStatus(str, Enum):
    """Health status levels."""
    HEALTHY   = "healthy"
    DEGRADED  = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN   = "unknown"


# ════════════════════════════════════════════════════════════════════════
# Message Delivery Mode
# ════════════════════════════════════════════════════════════════════════


class MessageDeliveryMode(str, Enum):
    """Message delivery semantics."""
    AT_MOST_ONCE  = "at_most_once"
    AT_LEAST_ONCE = "at_least_once"
    EXACTLY_ONCE  = "exactly_once"


# ════════════════════════════════════════════════════════════════════════
# Stream Mode
# ════════════════════════════════════════════════════════════════════════


class StreamMode(str, Enum):
    """Streaming direction."""
    PUSH           = "push"
    PULL           = "pull"
    BIDIRECTIONAL  = "bidirectional"


# ════════════════════════════════════════════════════════════════════════
# Service Validation Checks
# ════════════════════════════════════════════════════════════════════════


class ServiceValidationCheck(str, Enum):
    """Service-layer validation checks."""
    CONNECTOR_COMPATIBILITY  = "connector_compatibility"
    PROTOCOL_COMPATIBILITY   = "protocol_compatibility"
    AUTH_VALIDITY            = "auth_validity"
    RESPONSE_INTEGRITY       = "response_integrity"
    CONNECTION_HEALTH        = "connection_health"
    TRANSPORT_AVAILABILITY   = "transport_availability"


# ════════════════════════════════════════════════════════════════════════
# Convenience aliases & additional defaults
# ════════════════════════════════════════════════════════════════════════

DEFAULT_RETRY_COUNT        = DEFAULT_RETRY_MAX_ATTEMPTS
DEFAULT_MAX_RATE_LIMIT_RPS = DEFAULT_RATE_LIMIT_RPS
DEFAULT_POOL_MAX           = 50
DEFAULT_MAX_QUEUE_SIZE     = 10_000

FIBONACCI_DELAYS_MS: List[int] = [100, 100, 200, 300, 500, 800, 1300, 2100, 3400, 5500]
