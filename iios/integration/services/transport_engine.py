"""
transport_engine.py — iios.integration.services
-------------------------------------------------
TransportEngine — manages transport-layer initialisation and teardown.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from .constants import ConnectionState, TransportType


class TransportSession:
    """Mutable runtime state for an active transport session."""

    def __init__(self, session_id: str, transport_type: TransportType) -> None:
        self.session_id     = session_id
        self.transport_type = transport_type
        self.state          = ConnectionState.IDLE
        self.metadata:      Dict[str, Any] = {}

    def open(self) -> None:
        self.state = ConnectionState.CONNECTED

    def close(self) -> None:
        self.state = ConnectionState.CLOSED

    def fail(self) -> None:
        self.state = ConnectionState.FAILED

    @property
    def is_open(self) -> bool:
        return self.state == ConnectionState.CONNECTED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id":     self.session_id,
            "transport_type": self.transport_type.value,
            "state":          self.state.value,
            "metadata":       self.metadata,
        }


class TransportEngine:
    """
    Manages transport-layer lifecycle: initialise, open, close, health check.

    Provider-independent: does not open real network connections.
    Actual transport is handled by pluggable infrastructure adapters.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, TransportSession] = {}
        self._lock      = threading.Lock()

    def initialize(
        self,
        session_id:     str,
        transport_type: TransportType,
        config:         Optional[Dict[str, Any]] = None,
    ) -> TransportSession:
        """Initialise a transport session (no actual connection opened)."""
        session = TransportSession(session_id, transport_type)
        session.metadata = dict(config or {})
        with self._lock:
            self._sessions[session_id] = session
        return session

    def open(self, session_id: str) -> TransportSession:
        """Mark a transport session as open."""
        session = self._get_or_create(session_id)
        session.open()
        return session

    def close(self, session_id: str) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
        if session:
            session.close()

    def get(self, session_id: str) -> Optional[TransportSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def is_open(self, session_id: str) -> bool:
        session = self.get(session_id)
        return session is not None and session.is_open

    def health(self, session_id: str) -> Dict[str, Any]:
        session = self.get(session_id)
        if session is None:
            return {"status": "not_found", "session_id": session_id}
        return {"status": session.state.value, "session_id": session_id}

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for s in self._sessions.values() if s.is_open)

    def total_count(self) -> int:
        with self._lock:
            return len(self._sessions)

    def close_all(self) -> None:
        with self._lock:
            sessions = list(self._sessions.values())
        for s in sessions:
            s.close()

    def _get_or_create(self, session_id: str) -> TransportSession:
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = TransportSession(
                    session_id, TransportType.INTERNAL
                )
            return self._sessions[session_id]
