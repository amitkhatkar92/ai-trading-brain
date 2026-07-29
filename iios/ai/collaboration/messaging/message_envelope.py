"""
message_envelope.py -- iios.ai.collaboration.messaging
========================================================
:class:`DeliveryStatus` — envelope delivery states.
:class:`MessageEnvelope` — wraps an :class:`AgentMessage` with routing metadata.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum

from .agent_message    import AgentMessage
from .message_metadata import MessageMetadata


class DeliveryStatus(str, Enum):
    PENDING   = "pending"
    DELIVERED = "delivered"
    FAILED    = "failed"


@dataclass(frozen=True)
class MessageEnvelope:
    """
    Wraps a :class:`AgentMessage` with routing and delivery information.

    Created by :class:`MessageBus` when a message is sent.
    """

    envelope_id:     str
    message:         AgentMessage
    metadata:        MessageMetadata
    routed_at:       float
    delivery_status: DeliveryStatus
    retry_count:     int

    @classmethod
    def wrap(
        cls,
        message:  AgentMessage,
        metadata: MessageMetadata,
    ) -> "MessageEnvelope":
        return cls(
            envelope_id     = str(uuid.uuid4()),
            message         = message,
            metadata        = metadata,
            routed_at       = time.time(),
            delivery_status = DeliveryStatus.PENDING,
            retry_count     = 0,
        )

    def with_delivered(self) -> "MessageEnvelope":
        return MessageEnvelope(
            envelope_id     = self.envelope_id,
            message         = self.message,
            metadata        = self.metadata,
            routed_at       = self.routed_at,
            delivery_status = DeliveryStatus.DELIVERED,
            retry_count     = self.retry_count,
        )

    def with_failed(self) -> "MessageEnvelope":
        return MessageEnvelope(
            envelope_id     = self.envelope_id,
            message         = self.message,
            metadata        = self.metadata,
            routed_at       = self.routed_at,
            delivery_status = DeliveryStatus.FAILED,
            retry_count     = self.retry_count + 1,
        )

    def is_delivered(self) -> bool:
        return self.delivery_status == DeliveryStatus.DELIVERED
