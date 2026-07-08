"""
iios/intelligence/agents/agent_exceptions.py
=============================================
Full exception hierarchy for the Multi-Agent Coordination Engine.

Error code prefix: AGT-

Hierarchy
---------
AgentError                (AGT-000)
  AgentLifecycleError     (AGT-010)
    AgentNotFoundError    (AGT-011)
    AgentAlreadyRegisteredError (AGT-012)
    AgentExecutionError   (AGT-013)
    AgentTimeoutError     (AGT-014)
    AgentNotInitializedError (AGT-015)  — no args
    AgentUnavailableError (AGT-016)
    AgentStatusError      (AGT-017)
  CommunicationError      (AGT-020)
    MailboxFullError       (AGT-021)
    ChannelNotFoundError   (AGT-022)
    MessageRoutingError    (AGT-023)
    MessageExpiredError    (AGT-024)
    ChannelAlreadyExistsError (AGT-025)
  CoordinationError       (AGT-030)
    CoordinationTimeoutError  (AGT-031)
    InsufficientAgentsError   (AGT-032)
    CoordinationStrategyError (AGT-033)
  ConsensusError          (AGT-040)
    ConsensusTimeoutError  (AGT-041)
    NoConsensusError       (AGT-042)
    ConflictError          (AGT-043)
    InsufficientVotesError (AGT-044)
  SupervisionError        (AGT-050)
    SupervisorNotRunningError (AGT-051) — no args
    MaxRestartsExceededError  (AGT-052)
    HeartbeatTimeoutError     (AGT-053)
"""

from __future__ import annotations

__all__ = [
    "AgentError",
    "AgentLifecycleError",
    "AgentNotFoundError",
    "AgentAlreadyRegisteredError",
    "AgentExecutionError",
    "AgentTimeoutError",
    "AgentNotInitializedError",
    "AgentUnavailableError",
    "AgentStatusError",
    "CommunicationError",
    "MailboxFullError",
    "ChannelNotFoundError",
    "MessageRoutingError",
    "MessageExpiredError",
    "ChannelAlreadyExistsError",
    "CoordinationError",
    "CoordinationTimeoutError",
    "InsufficientAgentsError",
    "CoordinationStrategyError",
    "ConsensusError",
    "ConsensusTimeoutError",
    "NoConsensusError",
    "ConflictError",
    "InsufficientVotesError",
    "SupervisionError",
    "SupervisorNotRunningError",
    "MaxRestartsExceededError",
    "HeartbeatTimeoutError",
]


# ══════════════════════════════════════════════════════════════════════════════
#  Base
# ══════════════════════════════════════════════════════════════════════════════

class AgentError(Exception):
    """Base class for all Multi-Agent Coordination Engine errors."""
    code: str = "AGT-000"

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}" if self.message else f"[{self.code}]"


# ══════════════════════════════════════════════════════════════════════════════
#  Agent lifecycle errors (AGT-01x)
# ══════════════════════════════════════════════════════════════════════════════

class AgentLifecycleError(AgentError):
    """Base for agent lifecycle errors."""
    code = "AGT-010"


class AgentNotFoundError(AgentLifecycleError):
    """Raised when a requested agent_id is not registered."""
    code = "AGT-011"

    def __init__(self, agent_id: str) -> None:
        super().__init__(f"Agent not found: {agent_id!r}")
        self.agent_id = agent_id


class AgentAlreadyRegisteredError(AgentLifecycleError):
    """Raised when registering an agent_id that already exists."""
    code = "AGT-012"

    def __init__(self, agent_id: str) -> None:
        super().__init__(f"Agent already registered: {agent_id!r}")
        self.agent_id = agent_id


class AgentExecutionError(AgentLifecycleError):
    """Raised when an agent's execute() raises an unhandled exception."""
    code = "AGT-013"

    def __init__(self, agent_id: str, reason: str = "") -> None:
        super().__init__(f"Agent {agent_id!r} execution failed: {reason}")
        self.agent_id = agent_id
        self.reason   = reason


class AgentTimeoutError(AgentLifecycleError):
    """Raised when an agent execution exceeds its time budget."""
    code = "AGT-014"

    def __init__(self, agent_id: str, timeout_s: float) -> None:
        super().__init__(
            f"Agent {agent_id!r} timed out after {timeout_s:.1f}s"
        )
        self.agent_id  = agent_id
        self.timeout_s = timeout_s


class AgentNotInitializedError(AgentLifecycleError):
    """Raised when the coordinator is not yet initialized."""
    code = "AGT-015"

    def __init__(self) -> None:
        super().__init__("Multi-agent coordinator is not initialized")


class AgentUnavailableError(AgentLifecycleError):
    """Raised when an agent exists but cannot accept work (paused, stopped, etc.)."""
    code = "AGT-016"

    def __init__(self, agent_id: str, status: str = "") -> None:
        super().__init__(f"Agent {agent_id!r} is unavailable ({status})")
        self.agent_id = agent_id
        self.status   = status


class AgentStatusError(AgentLifecycleError):
    """Raised when a lifecycle transition is not allowed from the current status."""
    code = "AGT-017"

    def __init__(self, agent_id: str, current: str, operation: str) -> None:
        super().__init__(
            f"Agent {agent_id!r} cannot perform {operation!r} from status {current!r}"
        )
        self.agent_id  = agent_id
        self.current   = current
        self.operation = operation


# ══════════════════════════════════════════════════════════════════════════════
#  Communication errors (AGT-02x)
# ══════════════════════════════════════════════════════════════════════════════

class CommunicationError(AgentError):
    """Base for inter-agent communication errors."""
    code = "AGT-020"


class MailboxFullError(CommunicationError):
    """Raised when an agent's mailbox has no capacity."""
    code = "AGT-021"

    def __init__(self, agent_id: str, capacity: int) -> None:
        super().__init__(f"Mailbox for agent {agent_id!r} is full (capacity={capacity})")
        self.agent_id = agent_id
        self.capacity = capacity


class ChannelNotFoundError(CommunicationError):
    """Raised when a message is sent to a non-existent channel."""
    code = "AGT-022"

    def __init__(self, channel: str) -> None:
        super().__init__(f"Channel not found: {channel!r}")
        self.channel = channel


class MessageRoutingError(CommunicationError):
    """Raised when a message cannot be delivered to its recipient."""
    code = "AGT-023"

    def __init__(self, recipient: str, reason: str = "") -> None:
        super().__init__(f"Cannot route message to {recipient!r}: {reason}")
        self.recipient = recipient
        self.reason    = reason


class MessageExpiredError(CommunicationError):
    """Raised when a message is processed after its TTL has elapsed."""
    code = "AGT-024"

    def __init__(self, message_id: str) -> None:
        super().__init__(f"Message {message_id!r} has expired")
        self.message_id = message_id


class ChannelAlreadyExistsError(CommunicationError):
    """Raised when creating a channel that already exists."""
    code = "AGT-025"

    def __init__(self, channel: str) -> None:
        super().__init__(f"Channel already exists: {channel!r}")
        self.channel = channel


# ══════════════════════════════════════════════════════════════════════════════
#  Coordination errors (AGT-03x)
# ══════════════════════════════════════════════════════════════════════════════

class CoordinationError(AgentError):
    """Base for coordination strategy errors."""
    code = "AGT-030"


class CoordinationTimeoutError(CoordinationError):
    """Raised when a coordination task exceeds its allowed time."""
    code = "AGT-031"

    def __init__(self, task_id: str, timeout_s: float) -> None:
        super().__init__(f"Coordination task {task_id!r} timed out after {timeout_s:.1f}s")
        self.task_id   = task_id
        self.timeout_s = timeout_s


class InsufficientAgentsError(CoordinationError):
    """Raised when not enough agents are available for a coordination task."""
    code = "AGT-032"

    def __init__(self, required: int, available: int) -> None:
        super().__init__(
            f"Insufficient agents: need {required}, got {available}"
        )
        self.required  = required
        self.available = available


class CoordinationStrategyError(CoordinationError):
    """Raised when the coordination strategy encounters an internal error."""
    code = "AGT-033"

    def __init__(self, strategy: str, reason: str = "") -> None:
        super().__init__(f"Coordination strategy {strategy!r} failed: {reason}")
        self.strategy = strategy
        self.reason   = reason


# ══════════════════════════════════════════════════════════════════════════════
#  Consensus errors (AGT-04x)
# ══════════════════════════════════════════════════════════════════════════════

class ConsensusError(AgentError):
    """Base for consensus errors."""
    code = "AGT-040"


class ConsensusTimeoutError(ConsensusError):
    """Raised when not all agents respond within the consensus window."""
    code = "AGT-041"

    def __init__(self, timeout_s: float, received: int, expected: int) -> None:
        super().__init__(
            f"Consensus timed out after {timeout_s:.1f}s "
            f"({received}/{expected} responses)"
        )
        self.timeout_s = timeout_s
        self.received  = received
        self.expected  = expected


class NoConsensusError(ConsensusError):
    """Raised when agents cannot agree (no clear majority/threshold reached)."""
    code = "AGT-042"

    def __init__(self, method: str, agreement_rate: float) -> None:
        super().__init__(
            f"No consensus reached via {method!r} "
            f"(agreement rate {agreement_rate:.1%})"
        )
        self.method         = method
        self.agreement_rate = agreement_rate


class ConflictError(ConsensusError):
    """Raised when agent decisions are in irresolvable conflict."""
    code = "AGT-043"

    def __init__(self, conflicting: list[str]) -> None:
        super().__init__(
            f"Irresolvable conflict among agents: {conflicting}"
        )
        self.conflicting = conflicting


class InsufficientVotesError(ConsensusError):
    """Raised when too few agents submitted decisions for a valid vote."""
    code = "AGT-044"

    def __init__(self, required: int, received: int) -> None:
        super().__init__(
            f"Insufficient votes: need {required}, got {received}"
        )
        self.required = required
        self.received = received


# ══════════════════════════════════════════════════════════════════════════════
#  Supervision errors (AGT-05x)
# ══════════════════════════════════════════════════════════════════════════════

class SupervisionError(AgentError):
    """Base for supervision errors."""
    code = "AGT-050"


class SupervisorNotRunningError(SupervisionError):
    """Raised when a supervision operation is attempted before start()."""
    code = "AGT-051"

    def __init__(self) -> None:
        super().__init__("Agent supervisor is not running")


class MaxRestartsExceededError(SupervisionError):
    """Raised when an agent has been restarted too many times."""
    code = "AGT-052"

    def __init__(self, agent_id: str, max_attempts: int) -> None:
        super().__init__(
            f"Agent {agent_id!r} exceeded max restart attempts ({max_attempts})"
        )
        self.agent_id     = agent_id
        self.max_attempts = max_attempts


class HeartbeatTimeoutError(SupervisionError):
    """Raised when an agent stops sending heartbeats."""
    code = "AGT-053"

    def __init__(self, agent_id: str, silence_s: float) -> None:
        super().__init__(
            f"Agent {agent_id!r} heartbeat timed out (silent for {silence_s:.1f}s)"
        )
        self.agent_id = agent_id
        self.silence_s = silence_s
