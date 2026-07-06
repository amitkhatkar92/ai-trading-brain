"""
iios/events/messaging/command.py
==================================
Command handler base class and command registry.
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from typing import Any, Optional

from .message import Command, Response
from .command_bus import CommandBus, get_command_bus

__all__ = ["CommandHandlerBase", "CommandRegistry"]


class CommandHandlerBase(ABC):
    """Abstract base for command handlers.

    Subclass and implement ``handle()``, then register with a CommandBus::

        class PlaceOrderHandler(CommandHandlerBase):
            command_type = "order.place"

            def handle(self, command: Command) -> Optional[Response]:
                # ... process order ...
                return Response.ok(command.command_id, {"order_id": "ORD001"})

        handler = PlaceOrderHandler()
        handler.register()  # registers with the global command bus
    """

    command_type: str = ""

    @abstractmethod
    def handle(self, command: Command) -> Optional[Response]:
        """Execute the command and optionally return a Response."""

    def register(self, bus: Optional[CommandBus] = None) -> None:
        target = bus or get_command_bus()
        target.register(self.command_type, self.handle, allow_override=True)

    def __call__(self, command: Command) -> Optional[Response]:
        return self.handle(command)


class CommandRegistry:
    """Maintains a collection of CommandHandlerBase instances."""

    def __init__(self) -> None:
        self._handlers: dict[str, CommandHandlerBase] = {}
        self._lock = threading.Lock()

    def add(self, handler: CommandHandlerBase) -> None:
        with self._lock:
            self._handlers[handler.command_type] = handler

    def register_all(self, bus: Optional[CommandBus] = None) -> None:
        """Register all handlers with the bus."""
        with self._lock:
            handlers = list(self._handlers.values())
        for h in handlers:
            h.register(bus)

    def get(self, command_type: str) -> Optional[CommandHandlerBase]:
        with self._lock:
            return self._handlers.get(command_type)

    def list_types(self) -> list[str]:
        with self._lock:
            return list(self._handlers.keys())
