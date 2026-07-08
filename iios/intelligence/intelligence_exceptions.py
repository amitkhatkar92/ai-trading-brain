"""
iios/intelligence/intelligence_exceptions.py
=============================================
Exception hierarchy for the IIOS Intelligence Orchestration Engine.

All exceptions derive from IntelligenceError → Exception.
Each carries a machine-readable ``code`` attribute for structured logging.

Error-code prefix: INT-
"""

from __future__ import annotations

__all__ = [
    # Base
    "IntelligenceError",
    # Engine errors
    "EngineError",
    "EngineNotFoundError",
    "EngineAlreadyRegisteredError",
    "EngineExecutionError",
    "EngineTimeoutError",
    "EngineNotInitializedError",
    "EngineUnavailableError",
    # Session errors
    "SessionError",
    "SessionNotFoundError",
    "SessionExpiredError",
    "SessionAlreadyActiveError",
    "SessionRecoveryError",
    "SessionCapacityError",
    # Workflow errors
    "WorkflowError",
    "WorkflowNotFoundError",
    "WorkflowExecutionError",
    "WorkflowStepError",
    "WorkflowTimeoutError",
    "WorkflowCancelledError",
    "CircularDependencyError",
    "CheckpointError",
    "WorkflowAlreadyRegisteredError",
    # Orchestrator errors
    "OrchestratorError",
    "OrchestratorNotInitializedError",
    "PolicyViolationError",
    # Scheduler errors
    "SchedulerError",
    "SchedulerNotRunningError",
]


class IntelligenceError(Exception):
    """INT-000: Base exception for the Intelligence Orchestration Engine."""
    code: str = "INT-000"

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


# ── Engine errors ─────────────────────────────────────────────────────────────

class EngineError(IntelligenceError):
    """INT-010: Base for AI engine errors."""
    code = "INT-010"


class EngineNotFoundError(EngineError):
    """INT-011: Requested engine is not registered."""
    code = "INT-011"

    def __init__(self, engine_id: str) -> None:
        super().__init__(f"Engine not found: {engine_id!r}")
        self.engine_id = engine_id


class EngineAlreadyRegisteredError(EngineError):
    """INT-012: Engine already registered with the same ID."""
    code = "INT-012"

    def __init__(self, engine_id: str) -> None:
        super().__init__(f"Engine already registered: {engine_id!r}")
        self.engine_id = engine_id


class EngineExecutionError(EngineError):
    """INT-013: Engine raised an exception during execution."""
    code = "INT-013"

    def __init__(self, engine_id: str, cause: str = "") -> None:
        super().__init__(f"Engine execution failed [{engine_id!r}]: {cause}")
        self.engine_id = engine_id


class EngineTimeoutError(EngineError):
    """INT-014: Engine did not complete within the allotted time."""
    code = "INT-014"

    def __init__(self, engine_id: str, timeout_ms: float) -> None:
        super().__init__(
            f"Engine {engine_id!r} timed out after {timeout_ms:.0f} ms"
        )
        self.engine_id  = engine_id
        self.timeout_ms = timeout_ms


class EngineNotInitializedError(EngineError):
    """INT-015: Engine registered but not yet initialised."""
    code = "INT-015"

    def __init__(self, engine_id: str) -> None:
        super().__init__(f"Engine not initialised: {engine_id!r}")
        self.engine_id = engine_id


class EngineUnavailableError(EngineError):
    """INT-016: Engine is temporarily unavailable."""
    code = "INT-016"

    def __init__(self, engine_id: str, reason: str = "") -> None:
        super().__init__(f"Engine unavailable [{engine_id!r}]: {reason}")
        self.engine_id = engine_id


# ── Session errors ────────────────────────────────────────────────────────────

class SessionError(IntelligenceError):
    """INT-020: Base for session errors."""
    code = "INT-020"


class SessionNotFoundError(SessionError):
    """INT-021: Session ID does not exist."""
    code = "INT-021"

    def __init__(self, session_id: str) -> None:
        super().__init__(f"Session not found: {session_id!r}")
        self.session_id = session_id


class SessionExpiredError(SessionError):
    """INT-022: Session has exceeded its TTL."""
    code = "INT-022"

    def __init__(self, session_id: str) -> None:
        super().__init__(f"Session expired: {session_id!r}")
        self.session_id = session_id


class SessionAlreadyActiveError(SessionError):
    """INT-023: Duplicate session creation attempt."""
    code = "INT-023"

    def __init__(self, session_id: str) -> None:
        super().__init__(f"Session already active: {session_id!r}")
        self.session_id = session_id


class SessionRecoveryError(SessionError):
    """INT-024: Session recovery failed."""
    code = "INT-024"

    def __init__(self, session_id: str, reason: str = "") -> None:
        super().__init__(f"Session recovery failed [{session_id!r}]: {reason}")
        self.session_id = session_id


class SessionCapacityError(SessionError):
    """INT-025: Session capacity exceeded."""
    code = "INT-025"

    def __init__(self, max_sessions: int) -> None:
        super().__init__(f"Session capacity exceeded (max={max_sessions})")


# ── Workflow errors ───────────────────────────────────────────────────────────

class WorkflowError(IntelligenceError):
    """INT-030: Base for workflow errors."""
    code = "INT-030"


class WorkflowNotFoundError(WorkflowError):
    """INT-031: Named workflow does not exist."""
    code = "INT-031"

    def __init__(self, workflow_id: str) -> None:
        super().__init__(f"Workflow not found: {workflow_id!r}")
        self.workflow_id = workflow_id


class WorkflowExecutionError(WorkflowError):
    """INT-032: Workflow failed during execution."""
    code = "INT-032"

    def __init__(self, workflow_id: str, cause: str = "") -> None:
        super().__init__(f"Workflow execution failed [{workflow_id!r}]: {cause}")
        self.workflow_id = workflow_id


class WorkflowStepError(WorkflowError):
    """INT-033: A single step within a workflow failed."""
    code = "INT-033"

    def __init__(self, step_id: str, workflow_id: str = "", cause: str = "") -> None:
        super().__init__(
            f"Step {step_id!r} failed in workflow {workflow_id!r}: {cause}"
        )
        self.step_id     = step_id
        self.workflow_id = workflow_id


class WorkflowTimeoutError(WorkflowError):
    """INT-034: Workflow exceeded its time limit."""
    code = "INT-034"

    def __init__(self, workflow_id: str, timeout_ms: float) -> None:
        super().__init__(
            f"Workflow {workflow_id!r} timed out after {timeout_ms:.0f} ms"
        )
        self.workflow_id = workflow_id
        self.timeout_ms  = timeout_ms


class WorkflowCancelledError(WorkflowError):
    """INT-035: Workflow was cancelled by the caller."""
    code = "INT-035"

    def __init__(self, workflow_id: str) -> None:
        super().__init__(f"Workflow cancelled: {workflow_id!r}")
        self.workflow_id = workflow_id


class CircularDependencyError(WorkflowError):
    """INT-036: Circular dependency detected in workflow DAG."""
    code = "INT-036"

    def __init__(self, cycle: list[str]) -> None:
        super().__init__(f"Circular dependency: {' -> '.join(cycle)}")
        self.cycle = cycle


class CheckpointError(WorkflowError):
    """INT-037: Checkpoint save or restore failed."""
    code = "INT-037"

    def __init__(self, workflow_id: str, cause: str = "") -> None:
        super().__init__(f"Checkpoint error [{workflow_id!r}]: {cause}")
        self.workflow_id = workflow_id


class WorkflowAlreadyRegisteredError(WorkflowError):
    """INT-038: Workflow already registered with this ID."""
    code = "INT-038"

    def __init__(self, workflow_id: str) -> None:
        super().__init__(f"Workflow already registered: {workflow_id!r}")
        self.workflow_id = workflow_id


# ── Orchestrator errors ───────────────────────────────────────────────────────

class OrchestratorError(IntelligenceError):
    """INT-040: Base for orchestrator-level errors."""
    code = "INT-040"


class OrchestratorNotInitializedError(OrchestratorError):
    """INT-041: Orchestrator used before initialization."""
    code = "INT-041"

    def __init__(self) -> None:
        super().__init__(
            "IntelligenceOrchestrator has not been initialized — call initialize() first"
        )


class PolicyViolationError(OrchestratorError):
    """INT-042: Execution policy was violated."""
    code = "INT-042"

    def __init__(self, policy_type: str, detail: str = "") -> None:
        super().__init__(f"Policy violation [{policy_type}]: {detail}")
        self.policy_type = policy_type


# ── Scheduler errors ──────────────────────────────────────────────────────────

class SchedulerError(IntelligenceError):
    """INT-050: Base for scheduler errors."""
    code = "INT-050"


class SchedulerNotRunningError(SchedulerError):
    """INT-051: Scheduler is not running."""
    code = "INT-051"

    def __init__(self) -> None:
        super().__init__("Workflow scheduler is not running — call start() first")
