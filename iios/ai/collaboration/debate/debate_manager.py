"""
debate_manager.py -- iios.ai.collaboration.debate
===================================================
:class:`DebateManager` — creates and stores :class:`DebateSession` objects.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from ..exceptions.collaboration_exceptions import (
    AIDebateNotFoundError,
)
from .debate_session import DebateSession


class DebateManager:
    """
    Thread-safe registry of :class:`DebateSession` objects.

    One :class:`DebateManager` instance is shared across the framework (held
    by the :class:`CollaborationContainer`).
    """

    def __init__(self) -> None:
        self._lock:     threading.RLock                  = threading.RLock()
        self._sessions: Dict[str, DebateSession]         = {}

    def create(self, session_id: str, topic: str) -> DebateSession:
        """Create and open a new :class:`DebateSession` for *session_id*."""
        with self._lock:
            ds = DebateSession(session_id=session_id, topic=topic)
            ds.open()
            self._sessions[session_id] = ds
            return ds

    def get(self, session_id: str) -> DebateSession:
        with self._lock:
            ds = self._sessions.get(session_id)
        if ds is None:
            raise AIDebateNotFoundError(f"No debate session for collaboration session '{session_id}'.")
        return ds

    def exists(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._sessions

    def list_sessions(self) -> List[str]:
        with self._lock:
            return list(self._sessions.keys())

    def remove(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def session_count(self) -> int:
        with self._lock:
            return len(self._sessions)
