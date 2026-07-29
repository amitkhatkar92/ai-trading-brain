"""
orchestrator_exceptions.py -- iios.ai.orchestrator.exceptions
==============================================================
A10 exception hierarchy.  All exceptions extend :class:`AIException` from A1.

Error code range: AI-1500 – AI-1599

Hierarchy
---------
AIException (A1)
└── AIOrchestrationException                 AI-1500  base
    ├── AIObjectiveException                 AI-1510  base objective
    │   ├── AIObjectiveNotFoundError         AI-1511
    │   ├── AIObjectiveAlreadyExistsError    AI-1512
    │   └── AIObjectiveValidationError       AI-1513
    ├── AIPlanningException                  AI-1520  base planning
    │   ├── AIPlanNotFoundError              AI-1521
    │   ├── AIPlanGenerationError            AI-1522
    │   ├── AIPlanDependencyError            AI-1523
    │   └── AIReplanningError                AI-1524
    ├── AIWorkflowException                  AI-1530  base workflow
    │   ├── AIWorkflowNotFoundError          AI-1531
    │   ├── AIWorkflowAlreadyExistsError     AI-1532
    │   ├── AIWorkflowStateError             AI-1533
    │   ├── AIWorkflowExecutionError         AI-1534
    │   └── AIWorkflowTimeoutError           AI-1535
    ├── AITaskSchedulerException             AI-1540  base scheduler
    │   ├── AITaskNotFoundError              AI-1541
    │   ├── AITaskQueueFullError             AI-1542
    │   ├── AITaskDependencyError            AI-1543
    │   └── AITaskExecutionError             AI-1544
    ├── AIResourceException                  AI-1550  base resource
    │   ├── AIAgentNotAvailableError         AI-1551
    │   ├── AIResourceExhaustedError         AI-1552
    │   └── AIAllocationConflictError        AI-1553
    └── AIRecoveryException                  AI-1560  base recovery
        ├── AIRecoveryFailedError            AI-1561
        ├── AIRollbackFailedError            AI-1562
        └── AIMaxRetriesExceededError        AI-1563

A10 Enterprise AI Orchestrator — Phase 3, Module 10
"""
from __future__ import annotations

from iios.ai.foundation.exceptions import AIException


# ── Base ──────────────────────────────────────────────────────────────────────

class AIOrchestrationException(AIException):
    """Base exception for A10 Enterprise AI Orchestrator (AI-1500)."""

    def __init__(self, message: str = "Orchestration error", code: str = "AI-1500") -> None:
        super().__init__(message, code=code)


# ── Objective exceptions (AI-1510 – AI-1513) ─────────────────────────────────

class AIObjectiveException(AIOrchestrationException):
    """Base exception for objective-handling failures (AI-1510)."""

    def __init__(self, message: str = "Objective error", code: str = "AI-1510") -> None:
        super().__init__(message, code=code)


class AIObjectiveNotFoundError(AIObjectiveException):
    """Requested objective / session not found (AI-1511)."""

    def __init__(self, message: str = "Objective not found") -> None:
        super().__init__(message, code="AI-1511")


class AIObjectiveAlreadyExistsError(AIObjectiveException):
    """Objective already registered (AI-1512)."""

    def __init__(self, message: str = "Objective already exists") -> None:
        super().__init__(message, code="AI-1512")


class AIObjectiveValidationError(AIObjectiveException):
    """Objective failed validation (AI-1513)."""

    def __init__(self, message: str = "Objective validation failed") -> None:
        super().__init__(message, code="AI-1513")


# ── Planning exceptions (AI-1520 – AI-1524) ───────────────────────────────────

class AIPlanningException(AIOrchestrationException):
    """Base exception for planning engine failures (AI-1520)."""

    def __init__(self, message: str = "Planning error", code: str = "AI-1520") -> None:
        super().__init__(message, code=code)


class AIPlanNotFoundError(AIPlanningException):
    """Requested plan not found (AI-1521)."""

    def __init__(self, message: str = "Plan not found") -> None:
        super().__init__(message, code="AI-1521")


class AIPlanGenerationError(AIPlanningException):
    """Plan could not be generated from the given objective (AI-1522)."""

    def __init__(self, message: str = "Plan generation failed") -> None:
        super().__init__(message, code="AI-1522")


class AIPlanDependencyError(AIPlanningException):
    """Plan has invalid or cyclic dependencies (AI-1523)."""

    def __init__(self, message: str = "Plan dependency error") -> None:
        super().__init__(message, code="AI-1523")


class AIReplanningError(AIPlanningException):
    """Dynamic replanning failed (AI-1524)."""

    def __init__(self, message: str = "Replanning failed") -> None:
        super().__init__(message, code="AI-1524")


# ── Workflow exceptions (AI-1530 – AI-1535) ───────────────────────────────────

class AIWorkflowException(AIOrchestrationException):
    """Base exception for workflow engine failures (AI-1530)."""

    def __init__(self, message: str = "Workflow error", code: str = "AI-1530") -> None:
        super().__init__(message, code=code)


class AIWorkflowNotFoundError(AIWorkflowException):
    """Workflow definition or instance not found (AI-1531)."""

    def __init__(self, message: str = "Workflow not found") -> None:
        super().__init__(message, code="AI-1531")


class AIWorkflowAlreadyExistsError(AIWorkflowException):
    """Workflow already registered (AI-1532)."""

    def __init__(self, message: str = "Workflow already exists") -> None:
        super().__init__(message, code="AI-1532")


class AIWorkflowStateError(AIWorkflowException):
    """Invalid workflow state transition (AI-1533)."""

    def __init__(self, message: str = "Invalid workflow state") -> None:
        super().__init__(message, code="AI-1533")


class AIWorkflowExecutionError(AIWorkflowException):
    """Workflow step execution failed (AI-1534)."""

    def __init__(self, message: str = "Workflow execution failed") -> None:
        super().__init__(message, code="AI-1534")


class AIWorkflowTimeoutError(AIWorkflowException):
    """Workflow execution exceeded the allowed timeout (AI-1535)."""

    def __init__(self, message: str = "Workflow timed out") -> None:
        super().__init__(message, code="AI-1535")


# ── Task scheduler exceptions (AI-1540 – AI-1544) ─────────────────────────────

class AITaskSchedulerException(AIOrchestrationException):
    """Base exception for task scheduler failures (AI-1540)."""

    def __init__(self, message: str = "Task scheduler error", code: str = "AI-1540") -> None:
        super().__init__(message, code=code)


class AITaskNotFoundError(AITaskSchedulerException):
    """Scheduled task not found (AI-1541)."""

    def __init__(self, message: str = "Task not found") -> None:
        super().__init__(message, code="AI-1541")


class AITaskQueueFullError(AITaskSchedulerException):
    """Task queue has reached its capacity limit (AI-1542)."""

    def __init__(self, message: str = "Task queue is full") -> None:
        super().__init__(message, code="AI-1542")


class AITaskDependencyError(AITaskSchedulerException):
    """Task dependency cannot be satisfied (AI-1543)."""

    def __init__(self, message: str = "Task dependency error") -> None:
        super().__init__(message, code="AI-1543")


class AITaskExecutionError(AITaskSchedulerException):
    """Task execution failed (AI-1544)."""

    def __init__(self, message: str = "Task execution failed") -> None:
        super().__init__(message, code="AI-1544")


# ── Resource exceptions (AI-1550 – AI-1553) ───────────────────────────────────

class AIResourceException(AIOrchestrationException):
    """Base exception for resource-coordination failures (AI-1550)."""

    def __init__(self, message: str = "Resource error", code: str = "AI-1550") -> None:
        super().__init__(message, code=code)


class AIAgentNotAvailableError(AIResourceException):
    """No suitable agent is available for the requested capability (AI-1551)."""

    def __init__(self, message: str = "Agent not available") -> None:
        super().__init__(message, code="AI-1551")


class AIResourceExhaustedError(AIResourceException):
    """All available resources are exhausted (AI-1552)."""

    def __init__(self, message: str = "Resources exhausted") -> None:
        super().__init__(message, code="AI-1552")


class AIAllocationConflictError(AIResourceException):
    """Resource allocation conflict detected (AI-1553)."""

    def __init__(self, message: str = "Allocation conflict") -> None:
        super().__init__(message, code="AI-1553")


# ── Recovery exceptions (AI-1560 – AI-1563) ───────────────────────────────────

class AIRecoveryException(AIOrchestrationException):
    """Base exception for failure-recovery errors (AI-1560)."""

    def __init__(self, message: str = "Recovery error", code: str = "AI-1560") -> None:
        super().__init__(message, code=code)


class AIRecoveryFailedError(AIRecoveryException):
    """Recovery attempt failed (AI-1561)."""

    def __init__(self, message: str = "Recovery failed") -> None:
        super().__init__(message, code="AI-1561")


class AIRollbackFailedError(AIRecoveryException):
    """Rollback operation failed (AI-1562)."""

    def __init__(self, message: str = "Rollback failed") -> None:
        super().__init__(message, code="AI-1562")


class AIMaxRetriesExceededError(AIRecoveryException):
    """Maximum retry attempts exhausted (AI-1563)."""

    def __init__(self, message: str = "Maximum retries exceeded") -> None:
        super().__init__(message, code="AI-1563")
