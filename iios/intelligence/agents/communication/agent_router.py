"""
iios/intelligence/agents/communication/agent_router.py
=======================================================
AgentRouter — routes messages between agents.

Routing modes
-------------
direct      — message.recipient_id → agent's mailbox
broadcast   — fan-out to all registered mailboxes
channel     — publish to a named AgentChannel
request     — direct + store correlation for reply tracking
reply       — direct to the reply_to address

Singleton: get_agent_router() / reset_agent_router()
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional

from ..agent_constants import MessageType, SYSTEM_AGENT_ID
from ..agent_exceptions import MessageRoutingError, MessageExpiredError
from .agent_message import AgentMessage
from .agent_mailbox import AgentMailbox
from .agent_channel import ChannelRegistry, get_channel_registry

log = logging.getLogger(__name__)

__all__ = ["AgentRouter", "get_agent_router", "reset_agent_router"]


class AgentRouter:
    """
    Central message router.

    Usage
    -----
    router = get_agent_router()

    # Register agent mailboxes
    router.register_mailbox(agent_id, mailbox)

    # Route a message
    router.route(message)

    # Broadcast
    router.broadcast(message)
    """

    def __init__(
        self,
        channel_registry: Optional[ChannelRegistry] = None,
    ) -> None:
        self._channels = channel_registry or get_channel_registry()
        self._lock     = threading.RLock()
        self._mailboxes:      dict[str, AgentMailbox] = {}
        self._pending_replies: dict[str, str]          = {}  # correlation_id → reply_to
        self._routed_count  = 0
        self._dropped_count = 0

    # ── Mailbox registration ──────────────────────────────────────────────────

    def register_mailbox(self, agent_id: str, mailbox: AgentMailbox) -> None:
        with self._lock:
            self._mailboxes[agent_id] = mailbox

    def unregister_mailbox(self, agent_id: str) -> None:
        with self._lock:
            self._mailboxes.pop(agent_id, None)

    def has_mailbox(self, agent_id: str) -> bool:
        with self._lock:
            return agent_id in self._mailboxes

    # ── Core routing ──────────────────────────────────────────────────────────

    def route(self, message: AgentMessage) -> int:
        """
        Route a message to its destination(s).

        Returns the number of successful deliveries.
        """
        if message.is_expired:
            self._dropped_count += 1
            raise MessageExpiredError(message.message_id)

        if message.message_type == MessageType.BROADCAST or message.is_broadcast:
            return self._route_broadcast(message)

        if message.channel is not None:
            return self._route_channel(message)

        if message.recipient_id is not None:
            return self._route_direct(message)

        self._dropped_count += 1
        raise MessageRoutingError("unknown", "no recipient or channel specified")

    def send(
        self,
        sender_id:    str,
        recipient_id: str,
        payload:      dict,
        **kwargs,
    ) -> int:
        """Convenience: build a TASK message and route it."""
        msg = AgentMessage.task(
            sender_id    = sender_id,
            recipient_id = recipient_id,
            payload      = payload,
            **kwargs,
        )
        return self.route(msg)

    def broadcast(
        self,
        sender_id: str,
        payload:   dict,
        channel:   Optional[str] = None,
    ) -> int:
        """Broadcast to all agents (or all channel subscribers)."""
        msg = AgentMessage.broadcast(sender_id=sender_id, payload=payload, channel=channel)
        return self.route(msg)

    def request(
        self,
        sender_id:    str,
        recipient_id: str,
        payload:      dict,
        reply_handler: Optional[Callable[[AgentMessage], None]] = None,
    ) -> str:
        """
        Send a request and register a reply handler.

        Returns the correlation_id so the caller can track the response.
        """
        msg = AgentMessage.task(
            sender_id    = sender_id,
            recipient_id = recipient_id,
            payload      = payload,
            reply_to     = sender_id,
        )
        if reply_handler is not None:
            with self._lock:
                self._pending_replies[msg.correlation_id] = sender_id
        self.route(msg)
        return msg.correlation_id

    # ── Internal routing methods ──────────────────────────────────────────────

    def _route_direct(self, message: AgentMessage) -> int:
        with self._lock:
            mailbox = self._mailboxes.get(message.recipient_id)

        if mailbox is None:
            self._dropped_count += 1
            raise MessageRoutingError(
                message.recipient_id,
                "no mailbox registered",
            )
        try:
            mailbox.put(message)
            with self._lock:
                self._routed_count += 1
            return 1
        except Exception as exc:
            self._dropped_count += 1
            raise MessageRoutingError(message.recipient_id, str(exc)) from exc

    def _route_broadcast(self, message: AgentMessage) -> int:
        with self._lock:
            mailboxes = list(self._mailboxes.values())

        delivered = 0
        for mailbox in mailboxes:
            try:
                mailbox.put(message, drop_if_full=True)
                delivered += 1
            except Exception:
                pass
        with self._lock:
            self._routed_count += delivered
        return delivered

    def _route_channel(self, message: AgentMessage) -> int:
        try:
            delivered = self._channels.publish(message.channel, message)
            with self._lock:
                self._routed_count += delivered
            return delivered
        except Exception as exc:
            self._dropped_count += 1
            raise MessageRoutingError(message.channel, str(exc)) from exc

    # ── Stats ─────────────────────────────────────────────────────────────────

    @property
    def registered_agents(self) -> list[str]:
        with self._lock:
            return list(self._mailboxes.keys())

    def stats(self) -> dict:
        with self._lock:
            return {
                "registered_mailboxes": len(self._mailboxes),
                "routed_count":         self._routed_count,
                "dropped_count":        self._dropped_count,
                "pending_replies":      len(self._pending_replies),
            }


# ── Singleton ─────────────────────────────────────────────────────────────────

_router_lock = threading.Lock()
_router_inst: Optional[AgentRouter] = None


def get_agent_router() -> AgentRouter:
    global _router_inst
    if _router_inst is None:
        with _router_lock:
            if _router_inst is None:
                _router_inst = AgentRouter()
    return _router_inst


def reset_agent_router() -> None:
    global _router_inst
    with _router_lock:
        _router_inst = None
