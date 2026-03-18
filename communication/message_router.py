"""
Message Router — Point-to-Point Agent Messaging
================================================
Complements the EventBus (broadcast) with directed unicast messaging:
one agent sends a message to one specific named agent.

When to use EventBus vs MessageRouter:
  EventBus   → "broadcast to all who care"  (e.g. TRADE_APPROVED)
  MessageRouter → "ask this specific agent" (e.g. request portfolio state)

Features:
  • Named agent registry — agents register themselves by name
  • Request/Reply pattern — send a message and wait for a typed response
  • Timeout support — callers never block forever
  • Message inbox — agents pull messages at their own pace
  • Full message audit trail per agent

Architecture:
  AgentA.send_to("RiskManagerAI", msg)
         │
         ▼
    MessageRouter
         │
         ▼
    RiskManagerAI._inbox  ← polls or waits with timeout
         │
         ▼
    AgentA  ←── reply
"""

from __future__ import annotations

import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

DEFAULT_TIMEOUT = 5.0   # seconds


@dataclass
class Message:
    """
    A single directed message between two agents.
    """
    sender:        str
    recipient:     str
    subject:       str                        # short descriptor
    body:          Dict[str, Any] = field(default_factory=dict)
    msg_id:        str  = field(default_factory=lambda: str(uuid.uuid4())[:12])
    reply_to_id:   Optional[str]  = None     # Set when this is a reply
    timestamp:     datetime = field(default_factory=datetime.now)
    ttl_seconds:   float = 30.0              # Message expires after this

    @property
    def expired(self) -> bool:
        age = (datetime.now() - self.timestamp).total_seconds()
        return age > self.ttl_seconds

    def reply(self, sender: str, body: Dict[str, Any]) -> "Message":
        return Message(sender=sender, recipient=self.sender,
                       subject=f"RE: {self.subject}",
                       body=body, reply_to_id=self.msg_id)

    def __str__(self) -> str:
        return (f"[Msg {self.msg_id}] {self.sender}→{self.recipient} "
                f"'{self.subject}'")


class AgentInbox:
    """Thread-safe message inbox for one agent."""

    def __init__(self, agent_name: str, maxsize: int = 200):
        self._name  = agent_name
        self._queue: queue.Queue[Message] = queue.Queue(maxsize=maxsize)
        self._handler: Optional[Callable[[Message], Optional[Message]]] = None

    def put(self, msg: Message) -> bool:
        """Deliver a message. Returns False if inbox is full."""
        try:
            self._queue.put_nowait(msg)
            return True
        except queue.Full:
            log.warning("[Inbox:%s] Inbox full — dropped msg from %s.",
                        self._name, msg.sender)
            return False

    def get(self, timeout: float = DEFAULT_TIMEOUT) -> Optional[Message]:
        """
        Blocking read. Returns None on timeout.
        Automatically discards expired messages.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            try:
                msg = self._queue.get(timeout=min(remaining, 0.5))
                if msg.expired:
                    log.debug("[Inbox:%s] Discarded expired msg %s.", self._name, msg.msg_id)
                    continue
                return msg
            except queue.Empty:
                continue
        return None

    def get_nowait(self) -> Optional[Message]:
        """Non-blocking read."""
        try:
            msg = self._queue.get_nowait()
            return None if msg.expired else msg
        except queue.Empty:
            return None

    def drain(self) -> List[Message]:
        """Return all currently queued (non-expired) messages."""
        msgs = []
        while True:
            msg = self.get_nowait()
            if msg is None:
                break
            msgs.append(msg)
        return msgs

    def set_handler(self, fn: Callable[[Message], Optional[Message]]):
        """Register an auto-handler: called for every incoming message."""
        self._handler = fn

    @property
    def qsize(self) -> int:
        return self._queue.qsize()


class MessageRouter:
    """
    Central registry and delivery hub for point-to-point agent messages.

    Usage:
        router = MessageRouter()

        # Register agents
        router.register("RiskManagerAI")
        router.register("DecisionEngine")

        # Send a directed message
        router.send(Message(
            sender    = "StrategyGeneratorAI",
            recipient = "RiskManagerAI",
            subject   = "portfolio_heat_query",
        ))

        # Receive in RiskManagerAI
        msg = router.inbox("RiskManagerAI").get(timeout=2.0)

        # Request/Reply
        reply = router.request(
            sender    = "Orchestrator",
            recipient = "RiskManagerAI",
            subject   = "portfolio_heat_query",
            timeout   = 3.0,
        )
    """

    def __init__(self):
        self._lock:   threading.Lock = threading.Lock()
        self._inboxes: Dict[str, AgentInbox] = {}
        self._message_log: List[Message] = []
        log.info("[MessageRouter] Initialised.")

    # ─────────────────────────────────────────────────────────────────
    # AGENT REGISTRATION
    # ─────────────────────────────────────────────────────────────────

    def register(self, agent_name: str, inbox_size: int = 200) -> AgentInbox:
        """Register an agent and create its inbox."""
        with self._lock:
            if agent_name not in self._inboxes:
                self._inboxes[agent_name] = AgentInbox(agent_name, inbox_size)
                log.debug("[MessageRouter] Registered '%s'.", agent_name)
        return self._inboxes[agent_name]

    def inbox(self, agent_name: str) -> AgentInbox:
        """Return the inbox for an agent (registers if not found)."""
        if agent_name not in self._inboxes:
            self.register(agent_name)
        return self._inboxes[agent_name]

    def registered_agents(self) -> List[str]:
        with self._lock:
            return list(self._inboxes.keys())

    # ─────────────────────────────────────────────────────────────────
    # MESSAGING
    # ─────────────────────────────────────────────────────────────────

    def send(self, msg: Message) -> bool:
        """
        Deliver a message to a named agent's inbox.
        Returns True if delivered, False if recipient unknown or inbox full.
        """
        inbox = self._inboxes.get(msg.recipient)
        if inbox is None:
            log.warning("[MessageRouter] Unknown recipient '%s' — message dropped.",
                        msg.recipient)
            return False

        ok = inbox.put(msg)
        if ok:
            self._message_log.append(msg)
            if len(self._message_log) > 10_000:
                self._message_log = self._message_log[-10_000:]
            log.debug("[MessageRouter] Delivered: %s", msg)
        return ok

    def broadcast(self, sender: str, subject: str,
                  body: Dict[str, Any],
                  exclude: Optional[List[str]] = None) -> int:
        """Send the same message to every registered agent."""
        delivered = 0
        for agent in self.registered_agents():
            if exclude and agent in exclude:
                continue
            msg = Message(sender=sender, recipient=agent,
                          subject=subject, body=body)
            if self.send(msg):
                delivered += 1
        return delivered

    def request(self, sender: str, recipient: str,
                subject: str, body: Optional[Dict] = None,
                timeout: float = DEFAULT_TIMEOUT) -> Optional[Message]:
        """
        Synchronous request/reply:
          1. Send a message to recipient
          2. Block until a reply arrives in sender's inbox (or timeout)
        """
        self.register(sender)     # Ensure sender has an inbox for the reply
        req = Message(sender=sender, recipient=recipient,
                      subject=subject, body=body or {})
        self.send(req)

        # Poll sender's inbox for a reply matching req.msg_id
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            reply = self.inbox(sender).get_nowait()
            if reply and reply.reply_to_id == req.msg_id:
                return reply
            time.sleep(0.05)
        log.warning("[MessageRouter] Request timeout: %s→%s '%s'",
                    sender, recipient, subject)
        return None

    # ─────────────────────────────────────────────────────────────────
    # DIAGNOSTICS
    # ─────────────────────────────────────────────────────────────────

    def queue_depths(self) -> Dict[str, int]:
        return {name: inbox.qsize for name, inbox in self._inboxes.items()}

    def message_count(self) -> int:
        return len(self._message_log)


# ── Global singleton ─────────────────────────────────────────────────────────

_router: Optional[MessageRouter] = None

def get_router() -> MessageRouter:
    """Return the global shared MessageRouter."""
    global _router
    if _router is None:
        _router = MessageRouter()
    return _router
