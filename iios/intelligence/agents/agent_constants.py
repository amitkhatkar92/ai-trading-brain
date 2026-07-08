"""
iios/intelligence/agents/agent_constants.py
============================================
All enumerations and constants for the Multi-Agent Coordination Engine.

Error code prefix: AGT-
"""

from __future__ import annotations

from enum import Enum, IntEnum

__all__ = [
    # Enums
    "AgentType", "AgentStatus", "CoordinationMode", "ConsensusMethod",
    "MessageType", "MessagePriority", "SupervisionPolicy", "AgentEventType",
    "CoordinatorStatus",
    # Limits
    "MAX_AGENTS", "MAX_CONCURRENT_AGENTS", "MAX_MAILBOX_SIZE",
    "MAX_CHANNEL_SUBSCRIBERS", "MAX_BROADCAST_RECIPIENTS", "MAX_RESTART_ATTEMPTS",
    # Timing
    "HEARTBEAT_INTERVAL_S", "HEARTBEAT_TIMEOUT_S", "AGENT_EXECUTION_TIMEOUT_S",
    "DEFAULT_CONSENSUS_TIMEOUT_S", "MAILBOX_POLL_TIMEOUT_S", "SUPERVISOR_TICK_S",
    # Metadata
    "MULTI_AGENT_ENGINE_VERSION", "SYSTEM_AGENT_ID",
    "BROADCAST_CHANNEL", "CONTROL_CHANNEL",
]


class AgentType(Enum):
    """All supported AI agent types within IIOS."""
    REASONING     = "reasoning_agent"
    ANALYSIS      = "analysis_agent"
    DECISION      = "decision_agent"
    LEARNING      = "learning_agent"
    PLANNING      = "planning_agent"
    OBSERVATION   = "observation_agent"
    COORDINATION  = "coordination_agent"
    EXECUTION     = "execution_agent"
    RISK          = "risk_agent"
    STRATEGY      = "strategy_agent"
    PORTFOLIO     = "portfolio_agent"
    SENTIMENT     = "sentiment_agent"
    MACRO         = "macro_agent"
    TECHNICAL     = "technical_agent"
    ARBITRAGE     = "arbitrage_agent"
    SUPERVISOR    = "supervisor_agent"
    GENERIC       = "generic_agent"


class AgentStatus(Enum):
    """Lifecycle states for an agent."""
    REGISTERED    = "registered"
    INITIALIZING  = "initializing"
    IDLE          = "idle"
    RUNNING       = "running"
    PAUSED        = "paused"
    STOPPING      = "stopping"
    STOPPED       = "stopped"
    ERROR         = "error"
    RECOVERING    = "recovering"
    TERMINATED    = "terminated"


class CoordinationMode(Enum):
    """How multiple agents collaborate on a task."""
    SEQUENTIAL        = "sequential"
    PARALLEL          = "parallel"
    HIERARCHICAL      = "hierarchical"
    PEER_TO_PEER      = "peer_to_peer"
    SUPERVISOR_WORKER = "supervisor_worker"
    COMPETITIVE       = "competitive"
    CONSENSUS         = "consensus"
    DELEGATION        = "delegation"
    DYNAMIC           = "dynamic"


class ConsensusMethod(Enum):
    """Algorithm used to reach consensus from multiple agent decisions."""
    MAJORITY             = "majority"
    WEIGHTED_MAJORITY    = "weighted_majority"
    CONFIDENCE_WEIGHTED  = "confidence_weighted"
    UNANIMOUS            = "unanimous"
    FIRST_PASS           = "first_pass"
    RANKED_CHOICE        = "ranked_choice"
    CUSTOM               = "custom"


class MessageType(Enum):
    """Categories of inter-agent messages."""
    TASK          = "task"
    RESULT        = "result"
    NOTIFICATION  = "notification"
    REQUEST       = "request"
    RESPONSE      = "response"
    BROADCAST     = "broadcast"
    HEARTBEAT     = "heartbeat"
    CONTROL       = "control"
    ERROR         = "error"


class MessagePriority(IntEnum):
    """Message priority — lower value = higher priority (for PriorityQueue)."""
    CRITICAL   = 0
    HIGH       = 1
    NORMAL     = 2
    LOW        = 3
    BACKGROUND = 4


class SupervisionPolicy(Enum):
    """What the supervisor does when an agent fails."""
    RESTART_ALWAYS      = "restart_always"
    RESTART_ON_FAILURE  = "restart_on_failure"
    NO_RESTART          = "no_restart"
    ISOLATE_ON_FAILURE  = "isolate_on_failure"


class AgentEventType(Enum):
    """Events emitted by the multi-agent system."""
    REGISTERED        = "agent_registered"
    STARTED           = "agent_started"
    PAUSED            = "agent_paused"
    RESUMED           = "agent_resumed"
    STOPPED           = "agent_stopped"
    FAILED            = "agent_failed"
    RECOVERED         = "agent_recovered"
    MESSAGE_SENT      = "message_sent"
    MESSAGE_RECEIVED  = "message_received"
    CONSENSUS_REACHED = "consensus_reached"
    TASK_COMPLETED    = "task_completed"
    TASK_FAILED       = "task_failed"
    HEARTBEAT         = "heartbeat"


class CoordinatorStatus(Enum):
    """Multi-agent coordinator lifecycle states."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING  = "initializing"
    READY         = "ready"
    DEGRADED      = "degraded"
    SHUTTING_DOWN = "shutting_down"
    STOPPED       = "stopped"


# ── Capacity limits ────────────────────────────────────────────────────────────

MAX_AGENTS               = 256      # total registered agents
MAX_CONCURRENT_AGENTS    = 100      # agents running simultaneously
MAX_MAILBOX_SIZE         = 1_000    # messages per agent inbox
MAX_CHANNEL_SUBSCRIBERS  = 256      # subscribers per channel
MAX_BROADCAST_RECIPIENTS = 256      # max fan-out for a single broadcast
MAX_RESTART_ATTEMPTS     = 3        # per agent per supervision window

# ── Timing ─────────────────────────────────────────────────────────────────────

HEARTBEAT_INTERVAL_S        = 5.0    # how often agents should call heartbeat()
HEARTBEAT_TIMEOUT_S         = 30.0   # dead if no heartbeat for this long
AGENT_EXECUTION_TIMEOUT_S   = 300.0  # max seconds a single execute() call runs
DEFAULT_CONSENSUS_TIMEOUT_S = 30.0   # consensus collection window
MAILBOX_POLL_TIMEOUT_S      = 0.1    # blocking-get timeout in mailbox consumers
SUPERVISOR_TICK_S           = 2.0    # supervisor checks every N seconds

# ── Metadata ───────────────────────────────────────────────────────────────────

MULTI_AGENT_ENGINE_VERSION = "1.0.0"
SYSTEM_AGENT_ID            = "iios:agent:system"
BROADCAST_CHANNEL          = "iios:channel:broadcast"
CONTROL_CHANNEL            = "iios:channel:control"
