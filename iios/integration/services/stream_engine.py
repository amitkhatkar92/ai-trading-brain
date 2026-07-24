"""
stream_engine.py — iios.integration.services
----------------------------------------------
StreamEngine — manages streaming sessions for push/pull/bidirectional
data flows through integration connectors.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterator, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import StreamMode

_log = get_logger(__name__)

StreamHandler = Callable[[Dict[str, Any]], None]


@dataclass
class StreamSession:
    """Mutable runtime state of an active streaming session."""
    session_id:   str
    stream_mode:  StreamMode
    source:       str
    created_at:   str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    active:       bool = False
    frames_sent:  int  = 0
    frames_recv:  int  = 0
    errors:       int  = 0


class StreamEngine:
    """
    Manages streaming sessions for integration data flows.

    Sessions are identified by session_id. The engine supports push (source
    pushes to consumer), pull (consumer requests from source), and
    bidirectional modes.

    All streaming is simulated within-process — no vendor transport libraries
    are imported.
    """

    def __init__(self, max_sessions: int = 256) -> None:
        self._lock        = threading.Lock()
        self._sessions:   Dict[str, StreamSession] = {}
        self._handlers:   Dict[str, List[StreamHandler]] = {}
        self._max_sessions = max_sessions

    # ── Session management ───────────────────────────────────────────────

    def open_session(
        self,
        source:      str,
        stream_mode: StreamMode = StreamMode.PUSH,
    ) -> StreamSession:
        with self._lock:
            if len(self._sessions) >= self._max_sessions:
                raise RuntimeError(
                    f"stream-engine: max sessions ({self._max_sessions}) reached"
                )
            sid     = f"strm-{uuid.uuid4().hex[:12]}"
            session = StreamSession(
                session_id=sid, stream_mode=stream_mode, source=source, active=True
            )
            self._sessions[sid]  = session
            self._handlers[sid]  = []
        return session

    def close_session(self, session_id: str) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            session.active = False
            return True

    def get_session(self, session_id: str) -> Optional[StreamSession]:
        with self._lock:
            return self._sessions.get(session_id)

    # ── Subscribe / push ─────────────────────────────────────────────────

    def subscribe(self, session_id: str, handler: StreamHandler) -> None:
        with self._lock:
            if session_id not in self._handlers:
                raise KeyError(f"stream-engine: unknown session {session_id!r}")
            self._handlers[session_id].append(handler)

    def push_frame(self, session_id: str, frame: Dict[str, Any]) -> int:
        """
        Deliver a frame to all subscribers of a session.
        Returns the number of handlers that received the frame.
        """
        with self._lock:
            session  = self._sessions.get(session_id)
            handlers = list(self._handlers.get(session_id, []))
        if session is None or not session.active:
            return 0
        delivered = 0
        for h in handlers:
            try:
                h(frame)
                delivered += 1
            except Exception as exc:
                _log.debug(f"stream-engine handler error session={session_id}: {exc}")
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].frames_sent += 1
        return delivered

    # ── Pull ─────────────────────────────────────────────────────────────

    def pull_frame(
        self,
        session_id: str,
        payload:    Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Simulate pulling a single frame from the source."""
        with self._lock:
            session = self._sessions.get(session_id)
        if session is None or not session.active:
            return {}
        frame = {"session_id": session_id, "simulated": True, "payload": payload or {}}
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].frames_recv += 1
        return frame

    # ── Stats ─────────────────────────────────────────────────────────────

    @property
    def active_sessions(self) -> int:
        with self._lock:
            return sum(1 for s in self._sessions.values() if s.active)

    @property
    def total_sessions(self) -> int:
        with self._lock:
            return len(self._sessions)

    def session_ids(self) -> List[str]:
        with self._lock:
            return list(self._sessions.keys())
