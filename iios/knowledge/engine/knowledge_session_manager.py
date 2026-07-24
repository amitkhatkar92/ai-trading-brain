"""
knowledge_session_manager.py — iios.knowledge.engine
------------------------------------------------------
Manages knowledge lifecycle sessions via the M1 Knowledge Lifecycle package.

Wraps KnowledgeLifecycle so the engine never directly manipulates sessions.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import ACTOR_ENGINE, ENGINE_SYSTEM_ID

_log = get_logger(ENGINE_SYSTEM_ID)


class KnowledgeSessionManager:
    """
    Thin adapter over the M1 KnowledgeLifecycle for engine use.

    All session operations are delegated to an injected lifecycle instance.
    When no lifecycle is injected (e.g. in tests), a no-op implementation
    is used so the engine still functions.
    """

    def __init__(self, lifecycle: Optional[Any] = None) -> None:
        self._lifecycle = lifecycle
        self._lock      = threading.Lock()
        self._active:   Dict[str, Any] = {}   # session_id → session object

    # ------------------------------------------------------------------
    # Session operations
    # ------------------------------------------------------------------

    def create_session(
        self,
        artifact_id:    str,
        knowledge_type: str = "custom",
        actor:          str = ACTOR_ENGINE,
    ) -> str:
        """Create a lifecycle session and return its session_id."""
        if self._lifecycle is not None:
            try:
                from iios.knowledge.lifecycle import KnowledgeType
                kt = KnowledgeType(knowledge_type) if knowledge_type in [
                    m.value for m in KnowledgeType
                ] else KnowledgeType.CUSTOM
                session = self._lifecycle.create(artifact_id, kt, actor=actor)
                with self._lock:
                    self._active[session.session_id] = session
                return session.session_id
            except Exception as exc:
                _log.warning(f"Lifecycle session create failed: {exc!r}")

        # Fallback: generate a synthetic session ID
        import uuid
        sid = str(uuid.uuid4())
        with self._lock:
            self._active[sid] = {"session_id": sid, "artifact_id": artifact_id}
        return sid

    def initialize(self, session_id: str, actor: str = ACTOR_ENGINE) -> None:
        if self._lifecycle is not None:
            try:
                self._lifecycle.initialize(session_id, actor=actor)
            except Exception as exc:
                _log.warning(f"Lifecycle initialize failed: session_id={session_id!r} {exc!r}")

    def collect(self, session_id: str, actor: str = ACTOR_ENGINE) -> None:
        if self._lifecycle is not None:
            try:
                self._lifecycle.collect(session_id, actor=actor)
            except Exception as exc:
                _log.warning(f"Lifecycle collect failed: session_id={session_id!r} {exc!r}")

    def validate_session(self, session_id: str, actor: str = ACTOR_ENGINE) -> None:
        if self._lifecycle is not None:
            try:
                self._lifecycle.validate_session(session_id, actor=actor)
            except Exception as exc:
                _log.warning(f"Lifecycle validate failed: session_id={session_id!r} {exc!r}")

    def mark_ready(self, session_id: str, actor: str = ACTOR_ENGINE) -> None:
        if self._lifecycle is not None:
            try:
                self._lifecycle.mark_ready(session_id, actor=actor)
            except Exception as exc:
                _log.warning(f"Lifecycle mark_ready failed: session_id={session_id!r} {exc!r}")

    def start_capture(self, session_id: str, actor: str = ACTOR_ENGINE) -> None:
        if self._lifecycle is not None:
            try:
                self._lifecycle.start_capture(session_id, actor=actor)
            except Exception as exc:
                _log.warning(f"Lifecycle start_capture failed: session_id={session_id!r} {exc!r}")

    def mark_indexing_pending(self, session_id: str, actor: str = ACTOR_ENGINE) -> None:
        if self._lifecycle is not None:
            try:
                self._lifecycle.mark_indexing_pending(session_id, actor=actor)
            except Exception as exc:
                _log.warning(f"Lifecycle indexing_pending failed: {exc!r}")

    def publish(self, session_id: str, actor: str = ACTOR_ENGINE) -> None:
        if self._lifecycle is not None:
            try:
                self._lifecycle.publish(session_id, actor=actor)
            except Exception as exc:
                _log.warning(f"Lifecycle publish failed: session_id={session_id!r} {exc!r}")

    def complete_session(self, session_id: str, actor: str = ACTOR_ENGINE) -> None:
        if self._lifecycle is not None:
            try:
                self._lifecycle.complete(session_id, actor=actor)
                self._lifecycle.archive(session_id, actor=actor)
            except Exception as exc:
                _log.warning(f"Lifecycle complete failed: session_id={session_id!r} {exc!r}")
        with self._lock:
            self._active.pop(session_id, None)

    def fail_session(self, session_id: str, reason: str = "", actor: str = ACTOR_ENGINE) -> None:
        if self._lifecycle is not None:
            try:
                self._lifecycle.fail(session_id, reason, actor=actor)
                self._lifecycle.archive(session_id, actor=actor)
            except Exception as exc:
                _log.warning(f"Lifecycle fail failed: session_id={session_id!r} {exc!r}")
        with self._lock:
            self._active.pop(session_id, None)

    def active_count(self) -> int:
        with self._lock:
            return len(self._active)

    def health(self) -> Dict[str, Any]:
        if self._lifecycle is not None:
            try:
                return self._lifecycle.health()
            except Exception:
                pass
        return {"status": "no_lifecycle", "active_sessions": self.active_count()}
