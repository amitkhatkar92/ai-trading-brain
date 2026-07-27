"""
ai_foundation_registry.py — iios.ai.foundation.lifecycle
=========================================================
Thread-safe registry for AI Foundation sessions.

A1 AI Foundation — Phase 3, Module 1
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .ai_foundation_session import AIFoundationSession
from .constants import DEFAULT_MAX_SESSIONS, REGISTRY_SYSTEM_ID


class AIFoundationRegistry:
    """
    Thread-safe registry of active :class:`AIFoundationSession` objects.

    Capacity is bounded by ``max_sessions``; the oldest completed sessions
    are evicted when the limit is reached.
    """

    def __init__(self, max_sessions: int = DEFAULT_MAX_SESSIONS) -> None:
        self._max      = max_sessions
        self._lock     = threading.Lock()
        self._sessions: Dict[str, AIFoundationSession] = {}

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def register(self, session: AIFoundationSession) -> None:
        with self._lock:
            self._sessions[session.session_id] = session
            self._evict_if_needed()

    def get(self, session_id: str) -> Optional[AIFoundationSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def remove(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def all_sessions(self) -> List[AIFoundationSession]:
        with self._lock:
            return list(self._sessions.values())

    def count(self) -> int:
        with self._lock:
            return len(self._sessions)

    # ── Internals ─────────────────────────────────────────────────────────────

    def _evict_if_needed(self) -> None:
        """Evict oldest sessions when capacity is exceeded."""
        if len(self._sessions) <= self._max:
            return
        # Sort by created_at and remove oldest
        ordered = sorted(self._sessions.values(), key=lambda s: s.created_at)
        excess  = len(self._sessions) - self._max
        for s in ordered[:excess]:
            del self._sessions[s.session_id]
