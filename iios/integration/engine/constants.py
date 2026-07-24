"""
constants.py — iios.integration.engine
----------------------------------------
Enums, state definitions, and constants for the Integration Engine.

C15 Enterprise Integration & Connectivity — Phase 1, Module 2
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, Set


# ════════════════════════════════════════════════════════════════════════
# Engine States
# ════════════════════════════════════════════════════════════════════════


class IntegrationEngineState(str, Enum):
    """11 operational states for the Integration Engine."""
    IDLE         = "idle"
    INITIALIZING = "initializing"
    CONFIGURING  = "configuring"
    VALIDATING   = "validating"
    CONNECTING   = "connecting"
    DISPATCHING  = "dispatching"
    MONITORING   = "monitoring"
    PUBLISHING   = "publishing"
    COMPLETED    = "completed"
    FAILED       = "failed"
    STOPPED      = "stopped"


# ════════════════════════════════════════════════════════════════════════
# Connector, Adapter, Protocol Types
# ════════════════════════════════════════════════════════════════════════


class ConnectorType(str, Enum):
    """Supported enterprise connector types."""
    REST_API          = "rest_api"
    GRAPHQL           = "graphql"
    WEBSOCKET         = "websocket"
    GRPC              = "grpc"
    KAFKA             = "kafka"
    RABBITMQ          = "rabbitmq"
    REDIS_STREAM      = "redis_stream"
    MESSAGE_QUEUE     = "message_queue"
    DATABASE          = "database"
    FILE_TRANSFER     = "file_transfer"
    CLOUD_SERVICE     = "cloud_service"
    BROKER_API        = "broker_api"
    MARKET_DATA       = "market_data"
    NOTIFICATION      = "notification"
    IDENTITY_PROVIDER = "identity_provider"
    ERP               = "erp"
    CRM               = "crm"
    ENTERPRISE        = "enterprise"


class AdapterType(str, Enum):
    """Adapter types that transform data for connector consumption."""
    REST         = "rest"
    GRAPHQL      = "graphql"
    WEBSOCKET    = "websocket"
    GRPC         = "grpc"
    KAFKA        = "kafka"
    RABBITMQ     = "rabbitmq"
    REDIS        = "redis"
    DATABASE     = "database"
    FILE         = "file"
    CLOUD        = "cloud"
    BROKER       = "broker"
    MARKET_DATA  = "market_data"
    NOTIFICATION = "notification"
    IDENTITY     = "identity"
    ERP          = "erp"
    CRM          = "crm"
    GENERIC      = "generic"


class ProtocolType(str, Enum):
    """Communication protocol types."""
    HTTP            = "http"
    HTTPS           = "https"
    WEBSOCKET       = "websocket"
    GRPC            = "grpc"
    AMQP            = "amqp"
    KAFKA_PROTOCOL  = "kafka_protocol"
    REDIS_PROTOCOL  = "redis_protocol"
    JDBC            = "jdbc"
    FILE_SYSTEM     = "file_system"
    CLOUD_API       = "cloud_api"
    BROKER_API      = "broker_api"
    MARKET_DATA_API = "market_data_api"
    INTERNAL        = "internal"


# ════════════════════════════════════════════════════════════════════════
# Dispatch and Scheduler Modes
# ════════════════════════════════════════════════════════════════════════


class DispatchMode(str, Enum):
    """How an integration request is dispatched."""
    IMMEDIATE    = "immediate"
    CONTINUOUS   = "continuous"
    SCHEDULED    = "scheduled"
    EVENT_DRIVEN = "event_driven"
    PRIORITY     = "priority"
    BATCH        = "batch"
    RETRY        = "retry"


class SchedulerMode(str, Enum):
    """Scheduler scheduling mode."""
    IMMEDIATE    = "immediate"
    CONTINUOUS   = "continuous"
    SCHEDULED    = "scheduled"
    EVENT_DRIVEN = "event_driven"
    PRIORITY     = "priority"
    BATCH        = "batch"
    RETRY        = "retry"


# ════════════════════════════════════════════════════════════════════════
# Events
# ════════════════════════════════════════════════════════════════════════


class IntegrationEngineEventType(str, Enum):
    """9 lifecycle events emitted by the Integration Engine."""
    INTEGRATION_INITIALIZED = "integration_initialized"
    CONNECTOR_LOADED        = "connector_loaded"
    ADAPTER_LOADED          = "adapter_loaded"
    PROTOCOL_VALIDATED      = "protocol_validated"
    INTEGRATION_CONNECTED   = "integration_connected"
    INTEGRATION_DISPATCHED  = "integration_dispatched"
    INTEGRATION_PUBLISHED   = "integration_published"
    INTEGRATION_COMPLETED   = "integration_completed"
    INTEGRATION_FAILED      = "integration_failed"


# ════════════════════════════════════════════════════════════════════════
# Validation Checks
# ════════════════════════════════════════════════════════════════════════


class EngineValidationCheck(str, Enum):
    """7 validation checks run before dispatch."""
    CONNECTOR_VALIDITY      = "connector_validity"
    ADAPTER_COMPATIBILITY   = "adapter_compatibility"
    PROTOCOL_COMPATIBILITY  = "protocol_compatibility"
    CONFIGURATION_INTEGRITY = "configuration_integrity"
    AUTHENTICATION_VALIDITY = "authentication_validity"
    LIFECYCLE_CONSISTENCY   = "lifecycle_consistency"
    INPUT_COMPLETENESS      = "input_completeness"


# ════════════════════════════════════════════════════════════════════════
# Pipeline Stages
# ════════════════════════════════════════════════════════════════════════


class PipelineStage(str, Enum):
    """Ordered stages of the integration pipeline."""
    VALIDATE             = "validate"
    INITIALIZE           = "initialize"
    LOAD_CONNECTOR       = "load_connector"
    LOAD_ADAPTER         = "load_adapter"
    VALIDATE_PROTOCOL    = "validate_protocol"
    DISPATCH             = "dispatch"
    COORDINATE_GOVERNANCE = "coordinate_governance"
    COORDINATE_SERVICES  = "coordinate_services"
    PUBLISH              = "publish"
    COMPLETE             = "complete"


PIPELINE_STAGE_ORDER = [
    PipelineStage.VALIDATE,
    PipelineStage.INITIALIZE,
    PipelineStage.LOAD_CONNECTOR,
    PipelineStage.LOAD_ADAPTER,
    PipelineStage.VALIDATE_PROTOCOL,
    PipelineStage.DISPATCH,
    PipelineStage.COORDINATE_GOVERNANCE,
    PipelineStage.COORDINATE_SERVICES,
    PipelineStage.PUBLISH,
    PipelineStage.COMPLETE,
]


# ════════════════════════════════════════════════════════════════════════
# Request status values
# ════════════════════════════════════════════════════════════════════════


class IntegrationResponseStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"


# ════════════════════════════════════════════════════════════════════════
# System identifiers
# ════════════════════════════════════════════════════════════════════════

ENGINE_SYSTEM_ID  = "iios:integration:engine"
MANAGER_SYSTEM_ID = "iios:integration:manager"
VERSION           = "1.0.0"
SCHEMA_VERSION    = "1.0"
FRAMEWORK_VERSION = "1.0.0"
BUILD_VERSION     = "1.0.0-stable"

ACTOR_ENGINE    = "iios:integration:engine"
ACTOR_SCHEDULER = "iios:integration:scheduler"
ACTOR_SYSTEM    = "iios:system"

# ════════════════════════════════════════════════════════════════════════
# Operational defaults
# ════════════════════════════════════════════════════════════════════════

DEFAULT_MAX_SESSIONS    = 10_000
DEFAULT_MAX_HISTORY     = 5_000
DEFAULT_MAX_CONNECTORS  = 1_000
DEFAULT_MAX_ADAPTERS    = 1_000
DEFAULT_MAX_PROTOCOLS   = 500
DEFAULT_QUEUE_SIZE      = 50_000
DEFAULT_ENGINE_ID       = "iios-engine-default"
DEFAULT_PRIORITY        = 5
DEFAULT_ENVIRONMENT     = "production"
