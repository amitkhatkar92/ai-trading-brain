"""
exceptions.py — iios.workflow.orchestration
--------------------------------------------
Exception hierarchy for the Workflow Orchestration Framework.

Error code prefix: WOF

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

from typing import List, Optional

from iios.common.errors.exceptions import IIOSError


class WorkflowOrchestrationError(IIOSError):
    """WOF-000 — Base exception for the Workflow Orchestration Framework."""
    error_code = "WOF-000"

    def __init__(self, message: str = "Workflow orchestration error", *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)


class WorkflowDefinitionError(WorkflowOrchestrationError):
    """WOF-001 — Invalid or missing workflow definition."""
    error_code = "WOF-001"

    def __init__(self, message: str = "Workflow definition error", *, definition_id: str = "", code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)
        self.definition_id = definition_id


class WorkflowValidationError(WorkflowOrchestrationError):
    """WOF-002 — Workflow definition or state validation failure."""
    error_code = "WOF-002"

    def __init__(self, message: str = "Workflow validation failed", *, issues: Optional[List[str]] = None, code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)
        self.issues: List[str] = issues or []


class WorkflowExecutionError(WorkflowOrchestrationError):
    """WOF-003 — Runtime workflow execution failure."""
    error_code = "WOF-003"

    def __init__(self, message: str = "Workflow execution failed", *, workflow_id: str = "", code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)
        self.workflow_id = workflow_id


class WorkflowStepError(WorkflowOrchestrationError):
    """WOF-004 — Step execution failure."""
    error_code = "WOF-004"

    def __init__(self, message: str = "Workflow step failed", *, step_id: str = "", code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)
        self.step_id = step_id


class WorkflowDependencyError(WorkflowOrchestrationError):
    """WOF-005 — Dependency resolution failure (e.g. circular dependency)."""
    error_code = "WOF-005"

    def __init__(self, message: str = "Workflow dependency error", *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)


class WorkflowTimeoutError(WorkflowOrchestrationError):
    """WOF-006 — Step or workflow timeout exceeded."""
    error_code = "WOF-006"

    def __init__(self, message: str = "Workflow timeout exceeded", *, step_id: str = "", code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)
        self.step_id = step_id


class WorkflowRetryExhaustedError(WorkflowOrchestrationError):
    """WOF-007 — Maximum retry attempts exhausted."""
    error_code = "WOF-007"

    def __init__(self, message: str = "Retry attempts exhausted", *, step_id: str = "", attempts: int = 0, code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)
        self.step_id  = step_id
        self.attempts = attempts


class WorkflowCompensationError(WorkflowOrchestrationError):
    """WOF-008 — Compensation execution failure."""
    error_code = "WOF-008"

    def __init__(self, message: str = "Workflow compensation failed", *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)


class WorkflowCheckpointError(WorkflowOrchestrationError):
    """WOF-009 — Checkpoint creation or restore failure."""
    error_code = "WOF-009"

    def __init__(self, message: str = "Workflow checkpoint error", *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)


class WorkflowRecoveryError(WorkflowOrchestrationError):
    """WOF-010 — Workflow recovery failure."""
    error_code = "WOF-010"

    def __init__(self, message: str = "Workflow recovery failed", *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)


class WorkflowRegistryError(WorkflowOrchestrationError):
    """WOF-011 — Registry operation failure."""
    error_code = "WOF-011"

    def __init__(self, message: str = "Workflow registry error", *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)


class WorkflowResourceError(WorkflowOrchestrationError):
    """WOF-012 — Resource allocation or limit failure."""
    error_code = "WOF-012"

    def __init__(self, message: str = "Workflow resource error", *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)


class WorkflowSchedulerError(WorkflowOrchestrationError):
    """WOF-013 — Scheduler operation failure."""
    error_code = "WOF-013"

    def __init__(self, message: str = "Workflow scheduler error", *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)


class WorkflowPersistenceError(WorkflowOrchestrationError):
    """WOF-014 — Persistence operation failure."""
    error_code = "WOF-014"

    def __init__(self, message: str = "Workflow persistence error", *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)


class WorkflowQueueError(WorkflowOrchestrationError):
    """WOF-015 — Queue operation failure."""
    error_code = "WOF-015"

    def __init__(self, message: str = "Workflow queue error", *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)
