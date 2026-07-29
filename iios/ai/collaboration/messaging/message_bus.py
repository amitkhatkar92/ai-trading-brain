"""
message_bus.py -- iios.ai.collaboration.messaging
===================================================
:class:`MessageBus` — thread-safe in-session message store and dispatcher.

Supports direct messaging, broadcast, request/response, and full
message history per session.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

import threading
from collections import defaultdict
from typing import Dict, List, Optional

from .agent_message    import AgentMessage, MessageType
from .message_envelope import MessageEnvelope
from .message_metadata import MessageMetadata


class MessageBus:
    """
    Thread-safe message store and dispatcher for collaboration sessions.

    All messages are stored in memory indexed by session_id.
    """

    def __init__(self) -> None:
        self._lock:      threading.RLock                          = threading.RLock()
        self._messages:  Dict[str, List[AgentMessage]]           = defaultdict(list)
        self._envelopes: Dict[str, MessageEnvelope]              = {}

    # ── Send operations ───────────────────────────────────────────────────────

    def send(self, message: AgentMessage) -> MessageEnvelope:
        """
        Store *message* and return a delivered :class:`MessageEnvelope`.

        Works for both direct and broadcast messages (``recipient_id=None``).
        """
        meta     = MessageMetadata.create(session_id=message.session_id)
        envelope = MessageEnvelope.wrap(message, meta).with_delivered()
        with self._lock:
            self._messages[message.session_id].append(message)
            self._envelopes[envelope.envelope_id] = envelope
        return envelope

    def broadcast(
        self,
        message:       AgentMessage,
        recipient_ids: List[str],
    ) -> List[MessageEnvelope]:
        """
        Send *message* to each agent in *recipient_ids*.

        One envelope per recipient is created and returned.
        """
        envelopes = []
        for recipient_id in recipient_ids:
            copy = AgentMessage.create(
                sender_id      = message.sender_id,
                session_id     = message.session_id,
                message_type   = message.message_type,
                content        = message.content,
                recipient_id   = recipient_id,
                priority       = message.priority,
                correlation_id = message.correlation_id,
            )
            envelopes.append(self.send(copy))
        # Also store the original broadcast message
        with self._lock:
            self._messages[message.session_id].append(message)
        return envelopes

    # ── Query operations ──────────────────────────────────────────────────────

    def get_history(
        self,
        session_id:   str,
        sender_id:    Optional[str]        = None,
        message_type: Optional[MessageType] = None,
    ) -> List[AgentMessage]:
        """Return all messages for *session_id*, optionally filtered."""
        with self._lock:
            msgs = list(self._messages.get(session_id, []))
        if sender_id:
            msgs = [m for m in msgs if m.sender_id == sender_id]
        if message_type:
            msgs = [m for m in msgs if m.message_type == message_type]
        return msgs

    def get_for_recipient(
        self,
        recipient_id: str,
        session_id:   Optional[str] = None,
    ) -> List[AgentMessage]:
        """Return messages addressed to *recipient_id*."""
        with self._lock:
            if session_id:
                msgs = list(self._messages.get(session_id, []))
            else:
                msgs = [m for msgs in self._messages.values() for m in msgs]
        return [m for m in msgs if m.recipient_id == recipient_id]

    def message_count(self, session_id: str) -> int:
        with self._lock:
            return len(self._messages.get(session_id, []))

    def clear_session(self, session_id: str) -> None:
        """Remove all messages for *session_id*."""
        with self._lock:
            self._messages.pop(session_id, None)

    def total_count(self) -> int:
        with self._lock:
            return sum(len(v) for v in self._messages.values())
