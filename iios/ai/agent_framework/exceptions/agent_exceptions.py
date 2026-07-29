"""
agent_exceptions.py -- iios.ai.agent_framework.exceptions
==========================================================
A5 exception hierarchy.  All exceptions extend :class:`AIException` from A1.

Error code range: AI-1000 – AI-1099

Hierarchy
---------
AIException (A1, AI-000)
└── AIAgentException             AI-1000  base agent exception
    ├── AIAgentNotFoundError     AI-1001  agent not registered
    ├── AIAgentAlreadyExistsError AI-1002 agent already registered
    ├── AIAgentNotRunningError   AI-1003  agent not in active state
    ├── AIAgentAlreadyRunningError AI-1004 agent already active
    ├── AIAgentValidationError   AI-1005  spec/config validation failure
    ├── AITaskException          AI-1010  base task exception
    │   ├── AITaskNotFoundError  AI-1011  task not found
    │   ├── AITaskExecutionError AI-1012  task execution failed
    │   └── AITaskTimeoutError   AI-1013  task timed out
    ├── AICapabilityException    AI-1020  base capability exception
    │   ├── AICapabilityNotFoundError  AI-1021  capability not in registry
    │   └── AICapabilityNotPermittedError AI-1022 agent not permitted
    ├── AIRegistryException      AI-1030  base registry exception
    │   └── AIRegistrationFailedError AI-1031  registration failed
    ├── AIPermissionException    AI-1040  base permission exception
    │   ├── AIPermissionDeniedError AI-1041  access denied
    │   └── AIPermissionNotFoundError AI-1042 permission not found
    ├── AIRoleException          AI-1050  base role exception
    │   └── AIRoleNotFoundError  AI-1051  role not found
    └── AIPolicyException        AI-1060  base policy exception (agent-level)
        └── AIAgentPolicyViolationError AI-1061  policy violation

A5 AI Agent Framework -- Phase 3, Module 5
"""
from __future__ import annotations

from iios.ai.foundation.exceptions import AIException


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class AIAgentException(AIException):
    """Base exception for the A5 Agent Framework (AI-1000)."""

    def __init__(self, message: str = "Agent error", code: str = "AI-1000") -> None:
        super().__init__(message, code=code)


# ---------------------------------------------------------------------------
# Agent identity/lifecycle errors  AI-1001–AI-1005
# ---------------------------------------------------------------------------

class AIAgentNotFoundError(AIAgentException):
    """Agent is not registered in the registry (AI-1001)."""

    def __init__(self, agent_id: str = "") -> None:
        super().__init__(
            f"Agent not found: {agent_id!r}" if agent_id else "Agent not found",
            code="AI-1001",
        )


class AIAgentAlreadyExistsError(AIAgentException):
    """An agent with that ID is already registered (AI-1002)."""

    def __init__(self, agent_id: str = "") -> None:
        super().__init__(
            f"Agent already registered: {agent_id!r}" if agent_id else "Agent already registered",
            code="AI-1002",
        )


class AIAgentNotRunningError(AIAgentException):
    """Agent is not in an active/running state (AI-1003)."""

    def __init__(self, agent_id: str = "") -> None:
        super().__init__(
            f"Agent not running: {agent_id!r}" if agent_id else "Agent not running",
            code="AI-1003",
        )


class AIAgentAlreadyRunningError(AIAgentException):
    """Agent is already active/running (AI-1004)."""

    def __init__(self, agent_id: str = "") -> None:
        super().__init__(
            f"Agent already running: {agent_id!r}" if agent_id else "Agent already running",
            code="AI-1004",
        )


class AIAgentValidationError(AIAgentException):
    """Agent specification or configuration failed validation (AI-1005)."""

    def __init__(self, message: str = "Agent validation failed") -> None:
        super().__init__(message, code="AI-1005")


# ---------------------------------------------------------------------------
# Task errors  AI-1010–AI-1013
# ---------------------------------------------------------------------------

class AITaskException(AIAgentException):
    """Base exception for agent task operations (AI-1010)."""

    def __init__(self, message: str = "Task error", code: str = "AI-1010") -> None:
        super().__init__(message, code=code)


class AITaskNotFoundError(AITaskException):
    """Requested task does not exist (AI-1011)."""

    def __init__(self, task_id: str = "") -> None:
        super().__init__(
            f"Task not found: {task_id!r}" if task_id else "Task not found",
            code="AI-1011",
        )


class AITaskExecutionError(AITaskException):
    """Task execution failed (AI-1012)."""

    def __init__(self, message: str = "Task execution failed") -> None:
        super().__init__(message, code="AI-1012")


class AITaskTimeoutError(AITaskException):
    """Task exceeded its allowed execution time (AI-1013)."""

    def __init__(self, task_id: str = "", timeout_ms: float = 0.0) -> None:
        detail = f" (task={task_id!r}, timeout={timeout_ms}ms)" if task_id else ""
        super().__init__(f"Task timed out{detail}", code="AI-1013")


# ---------------------------------------------------------------------------
# Capability errors  AI-1020–AI-1022
# ---------------------------------------------------------------------------

class AICapabilityException(AIAgentException):
    """Base exception for capability operations (AI-1020)."""

    def __init__(self, message: str = "Capability error", code: str = "AI-1020") -> None:
        super().__init__(message, code=code)


class AICapabilityNotFoundError(AICapabilityException):
    """Requested capability is not registered (AI-1021)."""

    def __init__(self, capability: str = "") -> None:
        super().__init__(
            f"Capability not found: {capability!r}" if capability else "Capability not found",
            code="AI-1021",
        )


class AICapabilityNotPermittedError(AICapabilityException):
    """Agent does not have permission for this capability (AI-1022)."""

    def __init__(self, agent_id: str = "", capability: str = "") -> None:
        detail = f" (agent={agent_id!r}, capability={capability!r})" if agent_id else ""
        super().__init__(f"Capability not permitted{detail}", code="AI-1022")


# ---------------------------------------------------------------------------
# Registry errors  AI-1030–AI-1031
# ---------------------------------------------------------------------------

class AIRegistryException(AIAgentException):
    """Base exception for agent registry operations (AI-1030)."""

    def __init__(self, message: str = "Registry error", code: str = "AI-1030") -> None:
        super().__init__(message, code=code)


class AIRegistrationFailedError(AIRegistryException):
    """Agent registration failed (AI-1031)."""

    def __init__(self, message: str = "Agent registration failed") -> None:
        super().__init__(message, code="AI-1031")


# ---------------------------------------------------------------------------
# Permission errors  AI-1040–AI-1042
# ---------------------------------------------------------------------------

class AIAgentPermissionException(AIAgentException):
    """Base exception for agent permission operations (AI-1040)."""

    def __init__(self, message: str = "Permission error", code: str = "AI-1040") -> None:
        super().__init__(message, code=code)


class AIAgentPermissionDeniedError(AIAgentPermissionException):
    """Access denied — insufficient agent permission level (AI-1041)."""

    def __init__(self, resource: str = "", required: str = "") -> None:
        detail = f" (resource={resource!r}, required={required!r})" if resource else ""
        super().__init__(f"Permission denied{detail}", code="AI-1041")


class AIPermissionNotFoundError(AIAgentPermissionException):
    """No permission entry found for this resource (AI-1042)."""

    def __init__(self, resource: str = "") -> None:
        super().__init__(
            f"Permission not found for resource: {resource!r}" if resource else "Permission not found",
            code="AI-1042",
        )


# ---------------------------------------------------------------------------
# Role errors  AI-1050–AI-1051
# ---------------------------------------------------------------------------

class AIRoleException(AIAgentException):
    """Base exception for agent role operations (AI-1050)."""

    def __init__(self, message: str = "Role error", code: str = "AI-1050") -> None:
        super().__init__(message, code=code)


class AIAgentRoleNotFoundError(AIRoleException):
    """Requested agent role does not exist (AI-1051)."""

    def __init__(self, role_id: str = "") -> None:
        super().__init__(
            f"Role not found: {role_id!r}" if role_id else "Role not found",
            code="AI-1051",
        )


# ---------------------------------------------------------------------------
# Policy errors  AI-1060–AI-1061
# ---------------------------------------------------------------------------

class AIAgentPolicyException(AIAgentException):
    """Base exception for agent policy operations (AI-1060)."""

    def __init__(self, message: str = "Policy error", code: str = "AI-1060") -> None:
        super().__init__(message, code=code)


class AIAgentPolicyViolationError(AIAgentPolicyException):
    """An agent policy was violated (AI-1061)."""

    def __init__(self, message: str = "Agent policy violation") -> None:
        super().__init__(message, code="AI-1061")


# ---------------------------------------------------------------------------
# Backward-compatible aliases (deprecated — use agent-prefixed canonical names)
# ---------------------------------------------------------------------------

AIPermissionException   = AIAgentPermissionException
AIPermissionDeniedError = AIAgentPermissionDeniedError
AIRoleNotFoundError     = AIAgentRoleNotFoundError
AIPolicyException       = AIAgentPolicyException
