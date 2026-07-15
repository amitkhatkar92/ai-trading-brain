"""iios/common/errors/exceptions.py
Standard exception hierarchy for the IIOS institutional platform.

All exceptions derive from IIOSError, which derives from Exception.
Each exception carries:
  • message   — human-readable description
  • code      — machine-readable error code (for programmatic handling)
  • context   — arbitrary key-value metadata snapshot
  • correlation_id — for cross-service tracing

Usage::

    from iios.common.errors.exceptions import EngineError, ValidationError

    raise EngineError(
        "Market engine failed to start",
        code        = "ENGINE-START-001",
        context     = {"engine_id": "iios:market:integration"},
        correlation_id = ctx.correlation_id,
    )
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


# ── Base ──────────────────────────────────────────────────────────────────────

class IIOSError(Exception):
    """
    Base exception for the entire IIOS platform.

    All platform exceptions must derive from this class so that catch-all
    handlers can distinguish IIOS errors from unexpected third-party errors.
    """

    DEFAULT_CODE: str = "IIOS-000"

    def __init__(
        self,
        message:        str,
        *,
        code:           str = "",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message)
        self.message:        str                = message
        self.code:           str                = code or self.DEFAULT_CODE
        self.context:        Dict[str, Any]     = context or {}
        self.correlation_id: str                = correlation_id
        self.timestamp:      datetime           = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the exception to a JSON-compatible dict."""
        return {
            "type":           type(self).__name__,
            "code":           self.code,
            "message":        self.message,
            "correlation_id": self.correlation_id,
            "timestamp":      self.timestamp.isoformat(),
            "context":        self.context,
        }

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"code={self.code!r}, message={self.message!r}, "
            f"correlation_id={self.correlation_id!r})"
        )


# ── Domain-specific exceptions ────────────────────────────────────────────────

class ConfigurationError(IIOSError):
    """
    Raised when engine or system configuration is invalid or missing.

    Examples: missing required config key, out-of-range parameter,
    incompatible configuration combinations.
    """
    DEFAULT_CODE = "IIOS-CFG-001"


class ValidationError(IIOSError):
    """
    Raised when input data fails validation rules.

    Examples: invalid symbol format, out-of-range weight, malformed
    date range, constraint violation.
    """
    DEFAULT_CODE = "IIOS-VAL-001"

    def __init__(
        self,
        message:        str,
        *,
        field:          str = "",
        value:          Any = None,
        code:           str = "",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        ctx: Dict[str, Any] = context or {}
        if field:
            ctx["field"] = field
        if value is not None:
            ctx["value"] = value
        super().__init__(message, code=code, context=ctx, correlation_id=correlation_id)
        self.field = field
        self.value = value


class WorkflowError(IIOSError):
    """
    Raised when a workflow stage or orchestration step fails.

    Examples: stage dependency not met, workflow state machine violation,
    cycle detection, stage timeout.
    """
    DEFAULT_CODE = "IIOS-WF-001"

    def __init__(
        self,
        message:        str,
        *,
        workflow_id:    str = "",
        stage:          str = "",
        code:           str = "",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        ctx: Dict[str, Any] = context or {}
        if workflow_id:
            ctx["workflow_id"] = workflow_id
        if stage:
            ctx["stage"] = stage
        super().__init__(message, code=code, context=ctx, correlation_id=correlation_id)
        self.workflow_id = workflow_id
        self.stage       = stage


class EngineError(IIOSError):
    """
    Raised when an intelligence engine encounters an irrecoverable error.

    Examples: engine start failure, health check failure, resource
    exhaustion, unhandled engine-level exception.
    """
    DEFAULT_CODE = "IIOS-ENG-001"

    def __init__(
        self,
        message:        str,
        *,
        engine_id:      str = "",
        code:           str = "",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        ctx: Dict[str, Any] = context or {}
        if engine_id:
            ctx["engine_id"] = engine_id
        super().__init__(message, code=code, context=ctx, correlation_id=correlation_id)
        self.engine_id = engine_id


class DependencyError(IIOSError):
    """
    Raised when a required dependency (service, resource, feed) is unavailable.

    Examples: data feed offline, database unreachable, external API down.
    """
    DEFAULT_CODE = "IIOS-DEP-001"

    def __init__(
        self,
        message:        str,
        *,
        dependency:     str = "",
        code:           str = "",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        ctx: Dict[str, Any] = context or {}
        if dependency:
            ctx["dependency"] = dependency
        super().__init__(message, code=code, context=ctx, correlation_id=correlation_id)
        self.dependency = dependency


class IntegrationError(IIOSError):
    """
    Raised when an integration with an external system fails.

    Examples: broker API error, market data parse failure,
    authentication failure, protocol mismatch.
    """
    DEFAULT_CODE = "IIOS-INT-001"

    def __init__(
        self,
        message:        str,
        *,
        integration:    str = "",
        status_code:    int = 0,
        code:           str = "",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        ctx: Dict[str, Any] = context or {}
        if integration:
            ctx["integration"] = integration
        if status_code:
            ctx["status_code"] = status_code
        super().__init__(message, code=code, context=ctx, correlation_id=correlation_id)
        self.integration = integration
        self.status_code = status_code


class TimeoutError(IIOSError):  # noqa: A001 — intentional override of builtin
    """
    Raised when an operation exceeds its allowed time budget.

    Examples: data feed query timeout, engine startup timeout,
    workflow stage deadline exceeded.
    """
    DEFAULT_CODE = "IIOS-TMO-001"

    def __init__(
        self,
        message:        str,
        *,
        operation:      str   = "",
        timeout_sec:    float = 0.0,
        code:           str   = "",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str   = "",
    ) -> None:
        ctx: Dict[str, Any] = context or {}
        if operation:
            ctx["operation"] = operation
        if timeout_sec:
            ctx["timeout_sec"] = timeout_sec
        super().__init__(message, code=code, context=ctx, correlation_id=correlation_id)
        self.operation   = operation
        self.timeout_sec = timeout_sec


class RecoveryError(IIOSError):
    """
    Raised when recovery itself fails after exhausting all strategies.

    Signals that the system must escalate to operator intervention.
    """
    DEFAULT_CODE = "IIOS-REC-001"

    def __init__(
        self,
        message:        str,
        *,
        strategy:       str = "",
        attempts:       int = 0,
        code:           str = "",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        ctx: Dict[str, Any] = context or {}
        if strategy:
            ctx["strategy"] = strategy
        if attempts:
            ctx["attempts"] = attempts
        super().__init__(message, code=code, context=ctx, correlation_id=correlation_id)
        self.strategy = strategy
        self.attempts = attempts


class SecurityError(IIOSError):
    """
    Raised when a security constraint is violated.

    Examples: unauthorized access attempt, token validation failure,
    rate-limit breach, privilege escalation attempt.
    """
    DEFAULT_CODE = "IIOS-SEC-001"

    def __init__(
        self,
        message:        str,
        *,
        actor:          str = "",
        resource:       str = "",
        code:           str = "",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        ctx: Dict[str, Any] = context or {}
        if actor:
            ctx["actor"] = actor
        if resource:
            ctx["resource"] = resource
        super().__init__(message, code=code, context=ctx, correlation_id=correlation_id)
        self.actor    = actor
        self.resource = resource
