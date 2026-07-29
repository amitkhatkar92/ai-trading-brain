"""
agent_message.py -- iios.ai.collaboration.messaging
=====================================================
:class:`MessageType`     — message classification.
:class:`MessagePriority` — dispatch priority.
:class:`AgentMessage`    — immutable message unit.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, FrozenSet, Optional, Tuple


class MessageType(str, Enum):
    """Classification of a message's purpose and routing semantics."""

    DIRECT          = "direct"
    BROADCAST       = "broadcast"
    REQUEST         = "request"
    RESPONSE        = "response"
    ARGUMENT        = "argument"
    COUNTERARGUMENT = "counterargument"
    EVIDENCE        = "evidence"
    VOTE            = "vote"
    NOTIFICATION    = "notification"


class MessagePriority(str, Enum):
    """Scheduling priority for message dispatch."""

    LOW    = "low"
    NORMAL = "normal"
    HIGH   = "high"
    URGENT = "urgent"


@dataclass(frozen=True)
class AgentMessage:
    """
    Immutable message unit exchanged between agents within a session.

    ``recipient_id`` is ``None`` for broadcast messages.
    ``correlation_id`` links a :class:`MessageType.RESPONSE` back to its
    :class:`MessageType.REQUEST`.
    """

    message_id:     str
    sender_id:      str
    recipient_id:   Optional[str]   # None = broadcast
    session_id:     str
    message_type:   MessageType
    content:        Any
    priority:       MessagePriority
    sent_at:        float
    correlation_id: Optional[str]   # for request/response
    metadata:       FrozenSet[Tuple[str, Any]]

    @classmethod
    def create(
        cls,
        sender_id:      str,
        session_id:     str,
        message_type:   MessageType,
        content:        Any,
        recipient_id:   Optional[str]   = None,
        priority:       MessagePriority = MessagePriority.NORMAL,
        correlation_id: Optional[str]   = None,
        **meta: Any,
    ) -> "AgentMessage":
        return cls(
            message_id     = str(uuid.uuid4()),
            sender_id      = sender_id,
            recipient_id   = recipient_id,
            session_id     = session_id,
            message_type   = message_type,
            content        = content,
            priority       = priority,
            sent_at        = time.time(),
            correlation_id = correlation_id,
            metadata       = frozenset(meta.items()),
        )

    @property
    def is_broadcast(self) -> bool:
        return self.recipient_id is None

    def get_meta(self, key: str, default: Any = None) -> Any:
        for k, v in self.metadata:
            if k == key:
                return v
        return default
