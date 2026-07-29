"""
evaluation_manager.py -- iios.ai.learning_evaluation.evaluation
================================================================
:class:`EvaluationManager` — thread-safe registry of EvaluationSession objects.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from ..core.evaluation_metadata import EvaluationMetadata, EvaluationStatus
from ..exceptions.learning_evaluation_exceptions import (
    AIEvaluationSessionAlreadyExistsError,
    AIEvaluationSessionNotFoundError,
)
from .evaluation_session import EvaluationSession


class EvaluationManager:
    """
    Thread-safe in-memory registry for :class:`EvaluationSession` objects.

    One ``EvaluationManager`` instance is typically owned by the container.
    """

    def __init__(self) -> None:
        self._lock: threading.Lock = threading.Lock()
        self._sessions: Dict[str, EvaluationSession] = {}

    # ── creation ──────────────────────────────────────────────────────────────

    def create_session(self, metadata: EvaluationMetadata) -> EvaluationSession:
        with self._lock:
            sid = metadata.session_id
            if sid in self._sessions:
                raise AIEvaluationSessionAlreadyExistsError(
                    f"Session {sid!r} already exists"
                )
            session = EvaluationSession(metadata)
            self._sessions[sid] = session
        return session

    # ── lookup ────────────────────────────────────────────────────────────────

    def get_session(self, session_id: str) -> EvaluationSession:
        with self._lock:
            session = self._sessions.get(session_id)
        if session is None:
            raise AIEvaluationSessionNotFoundError(
                f"Session {session_id!r} not found"
            )
        return session

    def get_optional(self, session_id: str) -> Optional[EvaluationSession]:
        with self._lock:
            return self._sessions.get(session_id)

    # ── listing ───────────────────────────────────────────────────────────────

    def list_sessions(
        self,
        status: Optional[EvaluationStatus] = None,
    ) -> List[EvaluationSession]:
        with self._lock:
            sessions = list(self._sessions.values())
        if status is not None:
            sessions = [s for s in sessions if s.status == status]
        return sessions

    def active_count(self) -> int:
        with self._lock:
            return sum(
                1 for s in self._sessions.values()
                if s.status.is_active()
            )

    def total_count(self) -> int:
        with self._lock:
            return len(self._sessions)

    # ── cleanup ───────────────────────────────────────────────────────────────

    def remove_session(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)
