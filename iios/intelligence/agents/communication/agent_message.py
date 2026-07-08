"""
iios/intelligence/agents/communication/agent_message.py
========================================================
AgentMessage — the fundamental unit of inter-agent communication.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from ..agent_constants import MessageType, MessagePriority

__all__ = ["AgentMessage", "MessageEnvelope"]


@dataclass
class AgentMessage:
    """
    An immutable unit of communication between agents.

    Fields
    ------
    message_id     — globally unique identifier
    message_type   — semantic type of the message
    sender_id      — originating agent's ID (or SYSTEM_AGENT_ID)
    recipient_id   — target agent ID; None = broadcast
    payload        — application-level content (free-form dict)
    priority       — delivery priority
    channel        — optional pub/sub channel name
    correlation_id — links request to response
    reply_to       — sender's agent_id for request/reply pattern
    ttl_s          — message time-to-live in seconds (0 = no expiry)
    """
    message_id:     str          = field(default_factory=lambda: str(uuid.uuid4()))
    message_type:   MessageType  = MessageType.NOTIFICATION
    sender_id:      str          = ""
    recipient_id:   Optional[str] = None
    payload:        dict         = field(default_factory=dict)
    priority:       MessagePriority = MessagePriority.NORMAL
    channel:        Optional[str] = None
    correlation_id: Optional[str] = None
    reply_to:       Optional[str] = None
    ttl_s:          float         = 0.0        # 0 = never expires
    created_at:     float         = field(default_factory=time.time)
    metadata:       dict          = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        if self.ttl_s <= 0:
            return False
        return (time.time() - self.created_at) > self.ttl_s

    @property
    def is_broadcast(self) -> bool:
        return self.recipient_id is None

    @classmethod
    def task(
        cls,
        sender_id:    str,
        recipient_id: str,
        payload:      dict,
        priority:     MessagePriority = MessagePriority.NORMAL,
        correlation_id: Optional[str] = None,
        reply_to:     Optional[str]   = None,
        ttl_s:        float           = 0.0,
    ) -> "AgentMessage":
        return cls(
            message_type   = MessageType.TASK,
            sender_id      = sender_id,
            recipient_id   = recipient_id,
            payload        = payload,
            priority       = priority,
            correlation_id = correlation_id or str(uuid.uuid4()),
            reply_to       = reply_to,
            ttl_s          = ttl_s,
        )

    @classmethod
    def response(
        cls,
        sender_id:      str,
        recipient_id:   str,
        payload:        dict,
        correlation_id: str,
        priority:       MessagePriority = MessagePriority.NORMAL,
    ) -> "AgentMessage":
        return cls(
            message_type   = MessageType.RESPONSE,
            sender_id      = sender_id,
            recipient_id   = recipient_id,
            payload        = payload,
            priority       = priority,
            correlation_id = correlation_id,
        )

    @classmethod
    def broadcast(
        cls,
        sender_id: str,
        payload:   dict,
        channel:   Optional[str]      = None,
        priority:  MessagePriority    = MessagePriority.NORMAL,
    ) -> "AgentMessage":
        return cls(
            message_type = MessageType.BROADCAST,
            sender_id    = sender_id,
            recipient_id = None,
            payload      = payload,
            priority     = priority,
            channel      = channel,
        )

    @classmethod
    def heartbeat(cls, sender_id: str) -> "AgentMessage":
        return cls(
            message_type = MessageType.HEARTBEAT,
            sender_id    = sender_id,
            priority     = MessagePriority.BACKGROUND,
        )

    def to_dict(self) -> dict:
        return {
            "message_id":     self.message_id,
            "message_type":   self.message_type.value,
            "sender_id":      self.sender_id,
            "recipient_id":   self.recipient_id,
            "payload":        self.payload,
            "priority":       self.priority.name,
            "channel":        self.channel,
            "correlation_id": self.correlation_id,
            "reply_to":       self.reply_to,
            "ttl_s":          self.ttl_s,
            "created_at":     self.created_at,
        }

    def __lt__(self, other: "AgentMessage") -> bool:
        """Support PriorityQueue ordering (lower priority value = higher urgency)."""
        if not isinstance(other, AgentMessage):
            return NotImplemented
        return self.priority < other.priority


@dataclass
class MessageEnvelope:
    """
    Wraps an AgentMessage with delivery metadata (attempts, timestamps).
    """
    message:      AgentMessage
    attempts:     int   = 0
    enqueued_at:  float = field(default_factory=time.time)
    delivered_at: Optional[float] = None

    @property
    def age_s(self) -> float:
        return time.time() - self.enqueued_at

    def to_dict(self) -> dict:
        return {
            "message":      self.message.to_dict(),
            "attempts":     self.attempts,
            "enqueued_at":  self.enqueued_at,
            "delivered_at": self.delivered_at,
        }
