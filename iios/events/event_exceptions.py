"""
iios/events/event_exceptions.py
================================
Exception hierarchy for the IIOS Event & Messaging Framework.
"""

from __future__ import annotations

from typing import Any, Optional

__all__ = [
    "EventError",
    "PublishError",
    "SubscribeError",
    "HandlerError",
    "HandlerTimeoutError",
    "EventNotFoundError",
    "EventTypeError",
    "DispatchError",
    "RouterError",
    "NoRouteError",
    "RegistryError",
    "EventAlreadyRegisteredError",
    "MessageError",
    "MessageDeliveryError",
    "MessageExpiredError",
    "QueueError",
    "QueueFullError",
    "QueueEmptyError",
    "QueueTimeoutError",
    "DeadLetterError",
    "CommandError",
    "CommandNotFoundError",
    "CommandHandlerError",
    "QueryError",
    "QueryTimeoutError",
    "WorkflowError",
    "WorkflowStepError",
    "WorkflowTimeoutError",
    "WorkflowRollbackError",
    "RetryExhaustedError",
    "IdempotencyError",
]


class EventError(Exception):
    """Base for all Event & Messaging Framework errors."""

    def __init__(
        self,
        message: str,
        code: str = "EVT-000",
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.context: dict[str, Any] = context or {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.args[0]!r}, code={self.code!r})"


# ── Publish / Subscribe ───────────────────────────────────────────────────────

class PublishError(EventError):
    def __init__(self, msg: str = "Publish failed", **kw: Any) -> None:
        super().__init__(msg, code=kw.pop("code", "EVT-PUB-001"), **kw)


class SubscribeError(EventError):
    def __init__(self, msg: str = "Subscribe failed", **kw: Any) -> None:
        super().__init__(msg, code=kw.pop("code", "EVT-SUB-001"), **kw)


class HandlerError(EventError):
    def __init__(self, msg: str = "Handler failed", **kw: Any) -> None:
        super().__init__(msg, code=kw.pop("code", "EVT-HDL-001"), **kw)


class HandlerTimeoutError(HandlerError):
    def __init__(self, handler: str = "", timeout: float = 0.0, **kw: Any) -> None:
        super().__init__(
            f"Handler '{handler}' timed out after {timeout}s",
            code="EVT-HDL-002",
            context={"handler": handler, "timeout": timeout},
        )


# ── Event type / lookup ───────────────────────────────────────────────────────

class EventNotFoundError(EventError):
    def __init__(self, event_type: str = "", **kw: Any) -> None:
        super().__init__(f"Event type not found: {event_type}", code="EVT-REG-001")


class EventTypeError(EventError):
    def __init__(self, msg: str = "Invalid event type", **kw: Any) -> None:
        super().__init__(msg, code="EVT-TYP-001")


# ── Dispatch / Route ─────────────────────────────────────────────────────────

class DispatchError(EventError):
    def __init__(self, msg: str = "Dispatch failed", **kw: Any) -> None:
        super().__init__(msg, code=kw.pop("code", "EVT-DIS-001"), **kw)


class RouterError(EventError):
    def __init__(self, msg: str = "Router error", **kw: Any) -> None:
        super().__init__(msg, code=kw.pop("code", "EVT-RTE-001"), **kw)


class NoRouteError(RouterError):
    def __init__(self, event_type: str = "", **kw: Any) -> None:
        super().__init__(f"No route for event type: {event_type}", code="EVT-RTE-002")


# ── Registry ─────────────────────────────────────────────────────────────────

class RegistryError(EventError):
    def __init__(self, msg: str = "Registry error", **kw: Any) -> None:
        super().__init__(msg, code=kw.pop("code", "EVT-REG-002"), **kw)


class EventAlreadyRegisteredError(RegistryError):
    def __init__(self, event_type: str = "", **kw: Any) -> None:
        super().__init__(f"Event type already registered: {event_type}", code="EVT-REG-003")


# ── Messaging ─────────────────────────────────────────────────────────────────

class MessageError(EventError):
    def __init__(self, msg: str = "Message error", **kw: Any) -> None:
        super().__init__(msg, code=kw.pop("code", "EVT-MSG-001"), **kw)


class MessageDeliveryError(MessageError):
    def __init__(self, msg: str = "Message delivery failed", **kw: Any) -> None:
        super().__init__(msg, code="EVT-MSG-002")


class MessageExpiredError(MessageError):
    def __init__(self, msg_id: str = "", **kw: Any) -> None:
        super().__init__(f"Message expired: {msg_id}", code="EVT-MSG-003")


# ── Queue ─────────────────────────────────────────────────────────────────────

class QueueError(EventError):
    def __init__(self, msg: str = "Queue error", **kw: Any) -> None:
        super().__init__(msg, code=kw.pop("code", "EVT-QUE-001"), **kw)


class QueueFullError(QueueError):
    def __init__(self, name: str = "", max_size: int = 0, **kw: Any) -> None:
        super().__init__(f"Queue '{name}' is full (max={max_size})", code="EVT-QUE-002")


class QueueEmptyError(QueueError):
    def __init__(self, name: str = "", **kw: Any) -> None:
        super().__init__(f"Queue '{name}' is empty", code="EVT-QUE-003")


class QueueTimeoutError(QueueError):
    def __init__(self, name: str = "", timeout: float = 0.0, **kw: Any) -> None:
        super().__init__(f"Queue '{name}' timed out after {timeout}s", code="EVT-QUE-004")


class DeadLetterError(QueueError):
    def __init__(self, msg: str = "Dead letter queue error", **kw: Any) -> None:
        super().__init__(msg, code="EVT-QUE-DLQ")


# ── Command / Query ───────────────────────────────────────────────────────────

class CommandError(EventError):
    def __init__(self, msg: str = "Command error", **kw: Any) -> None:
        super().__init__(msg, code=kw.pop("code", "EVT-CMD-001"), **kw)


class CommandNotFoundError(CommandError):
    def __init__(self, command_type: str = "", **kw: Any) -> None:
        super().__init__(f"No handler for command: {command_type}", code="EVT-CMD-002")


class CommandHandlerError(CommandError):
    def __init__(self, msg: str = "Command handler failed", **kw: Any) -> None:
        super().__init__(msg, code="EVT-CMD-003")


class QueryError(EventError):
    def __init__(self, msg: str = "Query error", **kw: Any) -> None:
        super().__init__(msg, code=kw.pop("code", "EVT-QRY-001"), **kw)


class QueryTimeoutError(QueryError):
    def __init__(self, query_type: str = "", timeout: float = 0.0, **kw: Any) -> None:
        super().__init__(f"Query '{query_type}' timed out after {timeout}s", code="EVT-QRY-002")


# ── Workflow ──────────────────────────────────────────────────────────────────

class WorkflowError(EventError):
    def __init__(self, msg: str = "Workflow error", **kw: Any) -> None:
        super().__init__(msg, code=kw.pop("code", "EVT-WFL-001"), **kw)


class WorkflowStepError(WorkflowError):
    def __init__(self, step: str = "", msg: str = "", **kw: Any) -> None:
        super().__init__(f"Workflow step '{step}' failed: {msg}", code="EVT-WFL-002")


class WorkflowTimeoutError(WorkflowError):
    def __init__(self, workflow_id: str = "", timeout: float = 0.0, **kw: Any) -> None:
        super().__init__(f"Workflow '{workflow_id}' timed out after {timeout}s", code="EVT-WFL-003")


class WorkflowRollbackError(WorkflowError):
    def __init__(self, msg: str = "Workflow rollback failed", **kw: Any) -> None:
        super().__init__(msg, code="EVT-WFL-004")


# ── Reliability ───────────────────────────────────────────────────────────────

class RetryExhaustedError(EventError):
    def __init__(self, attempts: int = 0, **kw: Any) -> None:
        super().__init__(f"Retry exhausted after {attempts} attempts", code="EVT-RTY-001")


class IdempotencyError(EventError):
    def __init__(self, msg_id: str = "", **kw: Any) -> None:
        super().__init__(f"Duplicate message detected: {msg_id}", code="EVT-IDP-001")
