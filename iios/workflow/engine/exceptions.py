"""
exceptions.py — iios.workflow.engine
---------------------------------------
Exception hierarchy for the Workflow Engine.

Error code prefix: WEN

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 2
"""
from __future__ import annotations

from typing import List, Optional

from iios.common.errors.exceptions import IIOSError


class WorkflowEngineError(IIOSError):
    """WEN-000 — Base exception for all Workflow Engine errors."""
    error_code = "WEN-000"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)


class WorkflowEngineNotReadyError(WorkflowEngineError):
    """WEN-001 — Engine is not in a state to accept requests."""
    error_code = "WEN-001"

    def __init__(
        self,
        message: str = "Workflow engine is not ready",
        *,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code)


class WorkflowRequestValidationError(WorkflowEngineError):
    """WEN-002 — Request failed one or more validation checks."""
    error_code = "WEN-002"

    def __init__(
        self,
        message:       str,
        *,
        failed_checks: Optional[List[str]] = None,
        code:          Optional[str]       = None,
    ) -> None:
        super().__init__(message, code=code)
        self.failed_checks = failed_checks or []


class WorkflowSessionError(WorkflowEngineError):
    """WEN-003 — Lifecycle session error during engine operation."""
    error_code = "WEN-003"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code)


class WorkflowQueueCapacityError(WorkflowEngineError):
    """WEN-004 — Workflow queue has reached capacity."""
    error_code = "WEN-004"

    def __init__(
        self,
        message: str = "",
        *,
        limit: int = 0,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(
            message or f"Workflow queue capacity exceeded: limit={limit}",
            code=code,
        )
        self.limit = limit


class WorkflowDispatchError(WorkflowEngineError):
    """WEN-005 — Failure during workflow dispatch coordination."""
    error_code = "WEN-005"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code)


class WorkflowSchedulerError(WorkflowEngineError):
    """WEN-006 — Failure in the workflow scheduler."""
    error_code = "WEN-006"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code)


class WorkflowPipelineError(WorkflowEngineError):
    """WEN-007 — Pipeline stage failure."""
    error_code = "WEN-007"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code)


class WorkflowMonitorError(WorkflowEngineError):
    """WEN-008 — Workflow monitoring failure."""
    error_code = "WEN-008"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code)


class WorkflowGovernanceError(WorkflowEngineError):
    """WEN-009 — Governance hook invocation failure (M3 delegation)."""
    error_code = "WEN-009"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code)


class WorkflowOrchestrationError(WorkflowEngineError):
    """WEN-010 — Orchestration hook invocation failure (M4 delegation)."""
    error_code = "WEN-010"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code)
