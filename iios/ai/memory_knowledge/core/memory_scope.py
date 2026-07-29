"""
memory_scope.py -- iios.ai.memory_knowledge.core
=================================================
:class:`MemoryScope` — enum defining the four supported memory scopes.
"""
from __future__ import annotations

from enum import Enum


class MemoryScope(str, Enum):
    """Scope classification for memory entries."""
    WORKING   = "working"    # Ephemeral; exists only for a single task/turn
    SESSION   = "session"    # Lives for the duration of a user/agent session
    LONG_TERM = "long_term"  # Persists indefinitely across sessions
    SHARED    = "shared"     # Accessible by multiple agents or components
