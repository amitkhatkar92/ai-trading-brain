"""iios/intelligence/agents/__init__.py — Public API for the IIOS Multi-Agent Engine."""

# Constants
from .agent_constants import (
    AgentType, AgentStatus, CoordinationMode, ConsensusMethod,
    MessageType, MessagePriority, SupervisionPolicy, AgentEventType,
    CoordinatorStatus,
    MAX_AGENTS, MAX_CONCURRENT_AGENTS, MAX_MAILBOX_SIZE,
    HEARTBEAT_INTERVAL_S, HEARTBEAT_TIMEOUT_S, AGENT_EXECUTION_TIMEOUT_S,
    DEFAULT_CONSENSUS_TIMEOUT_S, SUPERVISOR_TICK_S,
    MULTI_AGENT_ENGINE_VERSION, SYSTEM_AGENT_ID,
    BROADCAST_CHANNEL, CONTROL_CHANNEL,
)

# Exceptions
from .agent_exceptions import (
    AgentError,
    AgentLifecycleError, AgentNotFoundError, AgentAlreadyRegisteredError,
    AgentExecutionError, AgentTimeoutError, AgentNotInitializedError,
    AgentUnavailableError, AgentStatusError,
    CommunicationError, MailboxFullError, ChannelNotFoundError,
    MessageRoutingError, MessageExpiredError, ChannelAlreadyExistsError,
    CoordinationError, CoordinationTimeoutError, InsufficientAgentsError,
    CoordinationStrategyError,
    ConsensusError, ConsensusTimeoutError, NoConsensusError,
    ConflictError, InsufficientVotesError,
    SupervisionError, SupervisorNotRunningError,
    MaxRestartsExceededError, HeartbeatTimeoutError,
)

# Context
from .agent_context import (
    AgentDiagnostic, AgentContext,
    get_agent_context, reset_agent_context,
    agent_execution, coordination_scope, task_scope,
)

# Core agent types
from .core import (
    AgentRequest, AgentResponse, AgentDecision, BaseAgent,
    ReasoningAgent, AnalysisAgent, DecisionAgent,
    LearningAgent, PlannerAgent, ObserverAgent,
)

# Communication
from .communication import (
    AgentMessage, MessageEnvelope,
    AgentMailbox,
    AgentChannel, ChannelRegistry, get_channel_registry, reset_channel_registry,
    AgentRouter, get_agent_router, reset_agent_router,
    AgentEvent, AgentEventBus, get_agent_event_bus, reset_agent_event_bus,
)

# Coordination
from .coordination import (
    CoordinationTask, CoordinationResult, CoordinationStrategy,
    SequentialStrategy, ParallelStrategy, CompetitiveStrategy,
    ConsensusStrategy, HierarchicalStrategy, DelegationStrategy,
    get_strategy,
)

# Consensus
from .consensus import (
    ConsensusResult, ConsensusEngine, get_consensus_engine, reset_consensus_engine,
    VoteResult, VotingEngine,
    ConflictReport, ConflictResolver,
    MergedDecision, DecisionMerger,
    AggregatedConfidence, ConfidenceAggregator,
)

# Supervision
from .supervision import (
    AgentRecord, AgentSupervisor, get_agent_supervisor, reset_agent_supervisor,
)

# Monitoring
from .monitoring import (
    AgentMetrics, SystemMetrics, AgentMonitor, get_agent_monitor, reset_agent_monitor,
)

# Execution
from .execution import (
    ExecutionSpec, ExecutionResult, AgentExecutor, get_agent_executor, reset_agent_executor,
)

# Registry
from .agent_registry import (
    AgentRegistration, AgentRegistry, get_agent_registry, reset_agent_registry,
)

# Factory
from .agent_factory import (
    AgentFactory, get_agent_factory, reset_agent_factory,
)

# Manager
from .agent_manager import (
    AgentManager, get_agent_manager, reset_agent_manager,
)

# Coordinator (main entry point)
from .multi_agent_coordinator import (
    MultiAgentCoordinator,
    get_multi_agent_coordinator,
    reset_multi_agent_coordinator,
)

__all__ = [
    # constants
    "AgentType", "AgentStatus", "CoordinationMode", "ConsensusMethod",
    "MessageType", "MessagePriority", "SupervisionPolicy", "AgentEventType",
    "CoordinatorStatus",
    "MAX_AGENTS", "MAX_CONCURRENT_AGENTS", "MAX_MAILBOX_SIZE",
    "HEARTBEAT_INTERVAL_S", "HEARTBEAT_TIMEOUT_S", "AGENT_EXECUTION_TIMEOUT_S",
    "DEFAULT_CONSENSUS_TIMEOUT_S", "SUPERVISOR_TICK_S",
    "MULTI_AGENT_ENGINE_VERSION", "SYSTEM_AGENT_ID",
    "BROADCAST_CHANNEL", "CONTROL_CHANNEL",
    # exceptions
    "AgentError",
    "AgentLifecycleError", "AgentNotFoundError", "AgentAlreadyRegisteredError",
    "AgentExecutionError", "AgentTimeoutError", "AgentNotInitializedError",
    "AgentUnavailableError", "AgentStatusError",
    "CommunicationError", "MailboxFullError", "ChannelNotFoundError",
    "MessageRoutingError", "MessageExpiredError", "ChannelAlreadyExistsError",
    "CoordinationError", "CoordinationTimeoutError", "InsufficientAgentsError",
    "CoordinationStrategyError",
    "ConsensusError", "ConsensusTimeoutError", "NoConsensusError",
    "ConflictError", "InsufficientVotesError",
    "SupervisionError", "SupervisorNotRunningError",
    "MaxRestartsExceededError", "HeartbeatTimeoutError",
    # context
    "AgentDiagnostic", "AgentContext",
    "get_agent_context", "reset_agent_context",
    "agent_execution", "coordination_scope", "task_scope",
    # core
    "AgentRequest", "AgentResponse", "AgentDecision", "BaseAgent",
    "ReasoningAgent", "AnalysisAgent", "DecisionAgent",
    "LearningAgent", "PlannerAgent", "ObserverAgent",
    # communication
    "AgentMessage", "MessageEnvelope",
    "AgentMailbox",
    "AgentChannel", "ChannelRegistry", "get_channel_registry", "reset_channel_registry",
    "AgentRouter", "get_agent_router", "reset_agent_router",
    "AgentEvent", "AgentEventBus", "get_agent_event_bus", "reset_agent_event_bus",
    # coordination
    "CoordinationTask", "CoordinationResult", "CoordinationStrategy",
    "SequentialStrategy", "ParallelStrategy", "CompetitiveStrategy",
    "ConsensusStrategy", "HierarchicalStrategy", "DelegationStrategy",
    "get_strategy",
    # consensus
    "ConsensusResult", "ConsensusEngine", "get_consensus_engine", "reset_consensus_engine",
    "VoteResult", "VotingEngine",
    "ConflictReport", "ConflictResolver",
    "MergedDecision", "DecisionMerger",
    "AggregatedConfidence", "ConfidenceAggregator",
    # supervision
    "AgentRecord", "AgentSupervisor", "get_agent_supervisor", "reset_agent_supervisor",
    # monitoring
    "AgentMetrics", "SystemMetrics", "AgentMonitor", "get_agent_monitor", "reset_agent_monitor",
    # execution
    "ExecutionSpec", "ExecutionResult", "AgentExecutor", "get_agent_executor", "reset_agent_executor",
    # registry
    "AgentRegistration", "AgentRegistry", "get_agent_registry", "reset_agent_registry",
    # factory
    "AgentFactory", "get_agent_factory", "reset_agent_factory",
    # manager
    "AgentManager", "get_agent_manager", "reset_agent_manager",
    # coordinator
    "MultiAgentCoordinator",
    "get_multi_agent_coordinator", "reset_multi_agent_coordinator",
]
