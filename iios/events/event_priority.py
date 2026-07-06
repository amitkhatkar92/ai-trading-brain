"""
iios/events/event_priority.py
================================
Priority levels for events and messages.
"""

from __future__ import annotations

from enum import IntEnum

__all__ = ["EventPriority", "MessagePriority"]


class EventPriority(IntEnum):
    """Event delivery priority. Lower value = higher priority."""
    CRITICAL = 0
    HIGH = 10
    ABOVE_NORMAL = 20
    NORMAL = 30
    BELOW_NORMAL = 40
    LOW = 50
    BACKGROUND = 100

    @classmethod
    def from_str(cls, value: str) -> "EventPriority":
        try:
            return cls[value.upper()]
        except KeyError:
            return cls.NORMAL


class MessagePriority(IntEnum):
    """Message queue priority. Lower value = higher priority."""
    URGENT = 0
    HIGH = 10
    NORMAL = 50
    LOW = 100
    DEFERRED = 200

    @classmethod
    def from_str(cls, value: str) -> "MessagePriority":
        try:
            return cls[value.upper()]
        except KeyError:
            return cls.NORMAL
