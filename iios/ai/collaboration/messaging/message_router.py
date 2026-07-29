"""
message_router.py -- iios.ai.collaboration.messaging
======================================================
:class:`MessageRouter` — routes message envelopes to registered handlers.

Handlers are callables ``(MessageEnvelope) -> None`` keyed by recipient_id.
Broadcast messages are dispatched to all registered handlers.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

import threading
from collections import defaultdict
from typing import Callable, Dict, List, Set

from .message_envelope import MessageEnvelope


Handler = Callable[[MessageEnvelope], None]


class MessageRouter:
    """
    Routes :class:`MessageEnvelope` objects to recipient-specific handlers.

    Usage::

        router.register_handler("agent-123", my_handler)
        router.route(envelope)   # calls my_handler(envelope)
    """

    def __init__(self) -> None:
        self._lock:     threading.Lock                   = threading.Lock()
        self._handlers: Dict[str, Set[Handler]]          = defaultdict(set)

    def register_handler(self, recipient_id: str, handler: Handler) -> None:
        """Register *handler* for messages addressed to *recipient_id*."""
        with self._lock:
            self._handlers[recipient_id].add(handler)

    def unregister_handler(self, recipient_id: str, handler: Handler) -> None:
        """Remove *handler* for *recipient_id*.  No-op if not registered."""
        with self._lock:
            self._handlers[recipient_id].discard(handler)

    def route(self, envelope: MessageEnvelope) -> None:
        """
        Dispatch *envelope* to all handlers for the target recipient.

        For broadcast messages (``recipient_id is None``) dispatch to all
        registered handlers.  Handler exceptions are swallowed.
        """
        with self._lock:
            if envelope.message.is_broadcast:
                handlers = [h for hs in self._handlers.values() for h in hs]
            else:
                handlers = list(self._handlers.get(envelope.message.recipient_id or "", []))

        for handler in handlers:
            try:
                handler(envelope)
            except Exception:  # noqa: BLE001
                pass

    def registered_recipients(self) -> List[str]:
        with self._lock:
            return list(self._handlers.keys())

    def handler_count(self, recipient_id: str) -> int:
        with self._lock:
            return len(self._handlers.get(recipient_id, set()))

    def clear(self) -> None:
        with self._lock:
            self._handlers.clear()
