"""
iios/intelligence/agents/communication/agent_channel.py
========================================================
AgentChannel — named pub/sub communication channel.

Agents subscribe to channels by name.  When a message is
published to a channel, all current subscribers receive a copy
via their AgentMailbox.
"""

from __future__ import annotations

import threading
from typing import Callable, Optional

from ..agent_constants import MAX_CHANNEL_SUBSCRIBERS
from ..agent_exceptions import ChannelNotFoundError, ChannelAlreadyExistsError
from .agent_message import AgentMessage

__all__ = ["AgentChannel", "ChannelRegistry", "get_channel_registry", "reset_channel_registry"]


class AgentChannel:
    """
    A named publish/subscribe channel.

    Subscribers register a callable that will be invoked (in the
    publisher's thread) whenever a message is published.
    """

    def __init__(self, name: str, max_subscribers: int = MAX_CHANNEL_SUBSCRIBERS) -> None:
        self.name            = name
        self.max_subscribers = max_subscribers
        self._lock           = threading.RLock()
        self._subscribers:   dict[str, Callable[[AgentMessage], None]] = {}
        self._message_count  = 0

    def subscribe(
        self,
        agent_id: str,
        handler:  Callable[[AgentMessage], None],
    ) -> None:
        with self._lock:
            self._subscribers[agent_id] = handler

    def unsubscribe(self, agent_id: str) -> None:
        with self._lock:
            self._subscribers.pop(agent_id, None)

    def publish(self, message: AgentMessage) -> int:
        """Publish to all subscribers. Returns number of deliveries."""
        with self._lock:
            handlers = list(self._subscribers.values())
            self._message_count += 1
        delivered = 0
        for h in handlers:
            try:
                h(message)
                delivered += 1
            except Exception:
                pass
        return delivered

    @property
    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscribers)

    @property
    def subscriber_ids(self) -> list[str]:
        with self._lock:
            return list(self._subscribers.keys())

    def stats(self) -> dict:
        with self._lock:
            return {
                "name":             self.name,
                "subscriber_count": len(self._subscribers),
                "message_count":    self._message_count,
            }


class ChannelRegistry:
    """
    Thread-safe registry of all named channels.
    """

    def __init__(self) -> None:
        self._lock:     threading.RLock = threading.RLock()
        self._channels: dict[str, AgentChannel] = {}

    def create(self, name: str, overwrite: bool = False) -> AgentChannel:
        with self._lock:
            if name in self._channels and not overwrite:
                raise ChannelAlreadyExistsError(name)
            ch = AgentChannel(name)
            self._channels[name] = ch
            return ch

    def get_or_create(self, name: str) -> AgentChannel:
        with self._lock:
            if name not in self._channels:
                self._channels[name] = AgentChannel(name)
            return self._channels[name]

    def get(self, name: str) -> AgentChannel:
        with self._lock:
            ch = self._channels.get(name)
            if ch is None:
                raise ChannelNotFoundError(name)
            return ch

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._channels

    def delete(self, name: str) -> bool:
        with self._lock:
            return self._channels.pop(name, None) is not None

    def list_names(self) -> list[str]:
        with self._lock:
            return list(self._channels.keys())

    def publish(self, channel_name: str, message: AgentMessage) -> int:
        """Publish a message to a named channel. Returns delivery count."""
        return self.get(channel_name).publish(message)

    def stats(self) -> dict:
        with self._lock:
            return {
                "total_channels": len(self._channels),
                "channels": [
                    ch.stats() for ch in self._channels.values()
                ],
            }

    def clear(self) -> None:
        with self._lock:
            self._channels.clear()


# ── Singleton ─────────────────────────────────────────────────────────────────

_reg_lock = threading.Lock()
_reg_inst: Optional[ChannelRegistry] = None


def get_channel_registry() -> ChannelRegistry:
    global _reg_inst
    if _reg_inst is None:
        with _reg_lock:
            if _reg_inst is None:
                _reg_inst = ChannelRegistry()
    return _reg_inst


def reset_channel_registry() -> None:
    global _reg_inst
    with _reg_lock:
        _reg_inst = None
