"""
exceptions.py — iios.decision.engine
======================================
Exception hierarchy for the Institutional Decision Engine subsystem.

Error-code prefix: DE (Decision Engine).

C9 Decision Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class DecisionEngineError(IIOSError):
    """
    Base error for the Institutional Decision Engine subsystem.

    All decision engine exceptions derive from this class so callers can
    catch the entire family with ``except DecisionEngineError``.
    """
    error_code: str = "DE-000"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


class DecisionEngineNotRunningError(DecisionEngineError):
    """
    Raised when an operation is attempted on :class:`DecisionEngine` while
    it is not in a running state.
    """
    error_code = "DE-001"

    def __init__(self, operation: str = "") -> None:
        detail = f" (operation: {operation!r})" if operation else ""
        super().__init__(
            f"Decision engine is not running{detail}",
            code=self.error_code,
        )


class DecisionRequestValidationError(DecisionEngineError):
    """
    Raised when a :class:`~iios.decision.engine.DecisionRequest` fails
    structural or contextual validation.
    """
    error_code = "DE-002"

    def __init__(
        self,
        detail: str = "",
        *,
        failed_checks: tuple[str, ...] = (),
    ) -> None:
        checks_str = ", ".join(failed_checks) if failed_checks else ""
        msg = f"Decision request validation failed"
        if checks_str:
            msg = f"{msg} — checks: {checks_str}"
        if detail:
            msg = f"{msg} — {detail}"
        super().__init__(msg, code=self.error_code)
        self.failed_checks: tuple[str, ...] = failed_checks


class DecisionPipelineError(DecisionEngineError):
    """
    Raised when a :class:`~iios.decision.engine.DecisionPipeline` encounters
    an unrecoverable error during its execution.
    """
    error_code = "DE-003"

    def __init__(self, pipeline_id: str = "", detail: str = "") -> None:
        pid = f"pipeline_id={pipeline_id!r}" if pipeline_id else ""
        d   = f" — {detail}" if detail else ""
        super().__init__(
            f"Decision pipeline error {pid}{d}".strip(),
            code=self.error_code,
        )
        self.pipeline_id = pipeline_id


class DecisionSessionError(DecisionEngineError):
    """
    Raised when a session-management operation fails in the engine.
    """
    error_code = "DE-004"

    def __init__(self, session_id: str = "", detail: str = "") -> None:
        sid = f"session_id={session_id!r}" if session_id else ""
        d   = f" — {detail}" if detail else ""
        super().__init__(
            f"Decision session error {sid}{d}".strip(),
            code=self.error_code,
        )
        self.session_id = session_id


class DecisionDispatchError(DecisionEngineError):
    """
    Raised when the :class:`~iios.decision.engine.DecisionDispatcher` fails
    to route or invoke a pipeline.
    """
    error_code = "DE-005"

    def __init__(self, detail: str = "") -> None:
        msg = f"Decision dispatch error" + (f" — {detail}" if detail else "")
        super().__init__(msg, code=self.error_code)


class DecisionPublishError(DecisionEngineError):
    """
    Raised when snapshot publication fails.
    """
    error_code = "DE-006"

    def __init__(self, detail: str = "") -> None:
        msg = f"Decision publish error" + (f" — {detail}" if detail else "")
        super().__init__(msg, code=self.error_code)


class DecisionCollectionError(DecisionEngineError):
    """
    Raised when institutional input collection fails.
    """
    error_code = "DE-007"

    def __init__(self, detail: str = "") -> None:
        msg = f"Decision collection error" + (f" — {detail}" if detail else "")
        super().__init__(msg, code=self.error_code)


class DecisionRequestNotFoundError(DecisionEngineError):
    """
    Raised when a request_id lookup fails.
    """
    error_code = "DE-008"

    def __init__(self, request_id: str = "") -> None:
        detail = f" (request_id={request_id!r})" if request_id else ""
        super().__init__(
            f"Decision request not found{detail}",
            code=self.error_code,
        )
