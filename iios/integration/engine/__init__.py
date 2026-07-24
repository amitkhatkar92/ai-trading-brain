"""
iios/integration/engine/__init__.py
-------------------------------------
Public API for the Integration Engine module.

C15 Enterprise Integration & Connectivity — Phase 1, Module 2
"""
from .adapter_manager import AdapterDescriptor, AdapterManager
from .connector_manager import ConnectorDescriptor, ConnectorManager
from .constants import (
    ACTOR_ENGINE,
    ACTOR_SCHEDULER,
    ACTOR_SYSTEM,
    BUILD_VERSION,
    DEFAULT_ENGINE_ID,
    DEFAULT_MAX_ADAPTERS,
    DEFAULT_MAX_CONNECTORS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_PROTOCOLS,
    DEFAULT_MAX_SESSIONS,
    DEFAULT_PRIORITY,
    DEFAULT_QUEUE_SIZE,
    ENGINE_SYSTEM_ID,
    FRAMEWORK_VERSION,
    MANAGER_SYSTEM_ID,
    PIPELINE_STAGE_ORDER,
    SCHEMA_VERSION,
    VERSION,
    AdapterType,
    ConnectorType,
    DispatchMode,
    EngineValidationCheck,
    IntegrationEngineEventType,
    IntegrationEngineState,
    IntegrationResponseStatus,
    PipelineStage,
    ProtocolType,
    SchedulerMode,
)
from .exceptions import (
    AdapterNotFoundError,
    AdapterRegistrationError,
    ConnectorNotFoundError,
    ConnectorRegistrationError,
    IntegrationDispatchError,
    IntegrationEngineError,
    IntegrationEngineNotReadyError,
    IntegrationRequestValidationError,
    IntegrationSessionError,
    ProtocolNotRegisteredError,
)
from .integration_context import IntegrationEngineContext
from .integration_dispatcher import IntegrationDispatcher
from .integration_engine import IntegrationEngine
from .integration_events import IntegrationEngineEvent, IntegrationEngineEventBus
from .integration_factory import IntegrationEngineFactory
from .integration_health import EngineHealthReport, IntegrationEngineHealth
from .integration_history import IntegrationEngineHistory
from .integration_manager import IntegrationManager
from .integration_pipeline import IntegrationPipeline, PipelineExecution
from .integration_registry import IntegrationEngineRegistry
from .integration_request import IntegrationRequest
from .integration_response import IntegrationResponse
from .integration_scheduler import IntegrationScheduler, ScheduledJob
from .integration_session_manager import IntegrationSessionManager
from .integration_statistics import (
    IntegrationEngineStatistics,
    IntegrationEngineStatisticsReport,
)
from .integration_status import IntegrationEngineStatus, IntegrationEngineStatusTracker
from .integration_validation import (
    EngineValidationReport,
    EngineValidationResult,
    IntegrationEngineValidator,
)
from .protocol_registry import ProtocolDescriptor, ProtocolRegistry

__all__ = [
    # Enums & constants
    "IntegrationEngineState",
    "ConnectorType",
    "AdapterType",
    "ProtocolType",
    "DispatchMode",
    "SchedulerMode",
    "IntegrationEngineEventType",
    "EngineValidationCheck",
    "PipelineStage",
    "IntegrationResponseStatus",
    "PIPELINE_STAGE_ORDER",
    "ENGINE_SYSTEM_ID",
    "MANAGER_SYSTEM_ID",
    "VERSION",
    "SCHEMA_VERSION",
    "FRAMEWORK_VERSION",
    "BUILD_VERSION",
    "DEFAULT_ENGINE_ID",
    "DEFAULT_MAX_SESSIONS",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_CONNECTORS",
    "DEFAULT_MAX_ADAPTERS",
    "DEFAULT_MAX_PROTOCOLS",
    "DEFAULT_QUEUE_SIZE",
    "DEFAULT_PRIORITY",
    "ACTOR_ENGINE",
    "ACTOR_SCHEDULER",
    "ACTOR_SYSTEM",
    # Exceptions
    "IntegrationEngineError",
    "IntegrationEngineNotReadyError",
    "ConnectorNotFoundError",
    "AdapterNotFoundError",
    "ProtocolNotRegisteredError",
    "IntegrationRequestValidationError",
    "IntegrationDispatchError",
    "IntegrationSessionError",
    "ConnectorRegistrationError",
    "AdapterRegistrationError",
    # Data objects
    "IntegrationRequest",
    "IntegrationResponse",
    "IntegrationEngineContext",
    # Descriptors
    "ConnectorDescriptor",
    "AdapterDescriptor",
    "ProtocolDescriptor",
    # Scheduled
    "ScheduledJob",
    # Pipeline
    "PipelineExecution",
    # Validation
    "EngineValidationResult",
    "EngineValidationReport",
    # Health & Status
    "EngineHealthReport",
    "IntegrationEngineStatus",
    # Statistics
    "IntegrationEngineStatisticsReport",
    # Events
    "IntegrationEngineEvent",
    # Subsystems
    "ConnectorManager",
    "AdapterManager",
    "ProtocolRegistry",
    "IntegrationEngineRegistry",
    "IntegrationSessionManager",
    "IntegrationPipeline",
    "IntegrationDispatcher",
    "IntegrationScheduler",
    "IntegrationEngineValidator",
    "IntegrationEngineHealth",
    "IntegrationEngineStatusTracker",
    "IntegrationEngineStatistics",
    "IntegrationEngineHistory",
    "IntegrationEngineEventBus",
    "IntegrationEngineFactory",
    # Main
    "IntegrationEngine",
    "IntegrationManager",
]
