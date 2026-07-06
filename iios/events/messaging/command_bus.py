"""
iios/events/messaging/command_bus.py
======================================
Command Bus — dispatches Commands to registered CommandHandlers.
Supports synchronous execution and optional response collection.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

from .message import Command, Response
from ..event_exceptions import CommandNotFoundError, CommandHandlerError

__all__ = ["CommandHandler", "CommandBus", "get_command_bus", "reset_command_bus"]

_LOG = logging.getLogger("iios.events.messaging.command_bus")

CommandHandler = Callable[[Command], Optional[Response]]

_bus_lock = threading.Lock()
_bus: Optional["CommandBus"] = None


@dataclass
class CommandStats:
    dispatched: int = 0
    succeeded: int = 0
    failed: int = 0
    avg_duration_ms: float = 0.0
    _total_ms: float = 0.0

    def record(self, ms: float, ok: bool) -> None:
        self.dispatched += 1
        self._total_ms += ms
        if ok:
            self.succeeded += 1
        else:
            self.failed += 1
        self.avg_duration_ms = self._total_ms / self.dispatched


class CommandBus:
    """Dispatches Commands to their registered handlers.

    One handler per command type (strict) — multiple handlers raises an error.

    Usage::

        bus = get_command_bus()
        bus.register("order.place", handle_place_order)
        response = bus.dispatch(Command(command_type="order.place", payload={...}))
    """

    def __init__(self) -> None:
        self._handlers: dict[str, CommandHandler] = {}
        self._middleware: list[Callable[[Command, CommandHandler], Optional[Response]]] = []
        self._stats = CommandStats()
        self._lock = threading.RLock()

    def register(self, command_type: str, handler: CommandHandler, allow_override: bool = False) -> None:
        with self._lock:
            if command_type in self._handlers and not allow_override:
                raise CommandHandlerError(f"Handler already registered for: {command_type}")
            self._handlers[command_type] = handler

    def unregister(self, command_type: str) -> bool:
        with self._lock:
            return self._handlers.pop(command_type, None) is not None

    def use(self, middleware: Callable[[Command, CommandHandler], Optional[Response]]) -> None:
        """Add middleware called before each command handler."""
        self._middleware.append(middleware)

    def dispatch(self, command: Command) -> Optional[Response]:
        with self._lock:
            handler = self._handlers.get(command.command_type)
        if handler is None:
            raise CommandNotFoundError(command.command_type)

        # Apply middleware chain
        current = handler
        for mw in reversed(self._middleware):
            _inner = current
            def _wrap(cmd: Command, h: CommandHandler = _inner, m: Any = mw) -> Optional[Response]:
                return m(cmd, h)
            current = _wrap

        t0 = time.monotonic()
        try:
            response = current(command)
            ms = (time.monotonic() - t0) * 1000
            self._stats.record(ms, ok=True)
            return response
        except Exception as exc:
            ms = (time.monotonic() - t0) * 1000
            self._stats.record(ms, ok=False)
            _LOG.error("Command %s handler failed: %s", command.command_type, exc)
            raise CommandHandlerError(str(exc)) from exc

    def has_handler(self, command_type: str) -> bool:
        with self._lock:
            return command_type in self._handlers

    def registered_types(self) -> list[str]:
        with self._lock:
            return list(self._handlers.keys())

    def stats(self) -> CommandStats:
        return self._stats


def get_command_bus() -> CommandBus:
    global _bus
    with _bus_lock:
        if _bus is None:
            _bus = CommandBus()
        return _bus


def reset_command_bus() -> None:
    global _bus
    with _bus_lock:
        _bus = None
