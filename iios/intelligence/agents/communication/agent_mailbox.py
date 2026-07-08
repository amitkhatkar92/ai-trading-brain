"""
iios/intelligence/agents/communication/agent_mailbox.py
========================================================
AgentMailbox — a thread-safe priority inbox for each agent.

Messages are stored in a heap-based priority queue so that
CRITICAL messages are always processed before NORMAL/LOW ones.
"""

from __future__ import annotations

import heapq
import threading
import time
from typing import Optional

from ..agent_constants import MAX_MAILBOX_SIZE, MAILBOX_POLL_TIMEOUT_S
from ..agent_exceptions import MailboxFullError, MessageExpiredError
from .agent_message import AgentMessage, MessageEnvelope

__all__ = ["AgentMailbox"]


class AgentMailbox:
    """
    Per-agent priority inbox.

    Thread-safe.  Uses a heap so pop() always returns the
    highest-priority (lowest MessagePriority int) message.
    """

    def __init__(
        self,
        agent_id: str,
        capacity: int = MAX_MAILBOX_SIZE,
    ) -> None:
        self.agent_id = agent_id
        self.capacity = capacity
        self._lock    = threading.RLock()
        self._heap:   list[tuple[int, float, MessageEnvelope]] = []
        self._event   = threading.Event()
        self._received_count = 0
        self._dropped_count  = 0

    # ── Write ─────────────────────────────────────────────────────────────────

    def put(
        self,
        message:    AgentMessage,
        block:      bool  = False,
        drop_if_full: bool = False,
    ) -> None:
        """
        Enqueue a message.

        block         — ignored (non-blocking by design; use drop_if_full)
        drop_if_full  — silently drop instead of raising MailboxFullError
        """
        if message.is_expired:
            raise MessageExpiredError(message.message_id)

        with self._lock:
            if len(self._heap) >= self.capacity:
                self._dropped_count += 1
                if drop_if_full:
                    return
                raise MailboxFullError(self.agent_id, self.capacity)
            envelope = MessageEnvelope(message=message)
            # heap key: (priority, timestamp) — lower priority int = higher urgency
            heapq.heappush(
                self._heap,
                (message.priority, message.created_at, envelope),
            )
            self._received_count += 1
        self._event.set()

    # ── Read ──────────────────────────────────────────────────────────────────

    def get(
        self,
        timeout_s: float = MAILBOX_POLL_TIMEOUT_S,
    ) -> Optional[MessageEnvelope]:
        """
        Dequeue the highest-priority message.

        Returns None if the mailbox is empty after timeout_s.
        """
        deadline = time.monotonic() + timeout_s
        while True:
            with self._lock:
                if self._heap:
                    _, _, envelope = heapq.heappop(self._heap)
                    envelope.delivered_at = time.time()
                    envelope.attempts    += 1
                    if len(self._heap) == 0:
                        self._event.clear()
                    return envelope
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            self._event.wait(timeout=min(remaining, MAILBOX_POLL_TIMEOUT_S))

    def get_nowait(self) -> Optional[MessageEnvelope]:
        """Non-blocking dequeue. Returns None if empty."""
        with self._lock:
            if not self._heap:
                return None
            _, _, envelope = heapq.heappop(self._heap)
            envelope.delivered_at = time.time()
            envelope.attempts    += 1
            if not self._heap:
                self._event.clear()
            return envelope

    def peek(self) -> Optional[AgentMessage]:
        """Peek at the highest-priority message without removing it."""
        with self._lock:
            if not self._heap:
                return None
            return self._heap[0][2].message

    # ── Inspection ────────────────────────────────────────────────────────────

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._heap)

    @property
    def is_empty(self) -> bool:
        return self.size == 0

    @property
    def is_full(self) -> bool:
        return self.size >= self.capacity

    def clear(self) -> None:
        with self._lock:
            self._heap.clear()
            self._event.clear()

    def stats(self) -> dict:
        with self._lock:
            return {
                "agent_id":       self.agent_id,
                "size":           len(self._heap),
                "capacity":       self.capacity,
                "received_count": self._received_count,
                "dropped_count":  self._dropped_count,
            }
