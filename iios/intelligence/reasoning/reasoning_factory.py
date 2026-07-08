"""
iios/intelligence/reasoning/reasoning_factory.py
================================================
Factory for creating and registering ReasoningSession objects.
"""
from __future__ import annotations

import threading
import uuid
from typing import Any

from .reasoning_constants import ReasoningType, DEFAULT_SESSION_TIMEOUT_S
from .reasoning_registry import ReasoningSessionRegistry, get_session_registry
from .reasoning_session import ReasoningSession


class ReasoningSessionFactory:
    """
    Creates ReasoningSession instances and registers them in the registry.
    Supports reusable templates.
    """

    def __init__(
        self,
        registry: ReasoningSessionRegistry | None = None,
    ) -> None:
        self._registry:  ReasoningSessionRegistry  = registry or get_session_registry()
        self._templates: dict[str, dict[str, Any]] = {}
        self._lock:      threading.RLock            = threading.RLock()
        self._created:   int                        = 0

    # -- Creation ──────────────────────────────────────────────────────────────

    def create(
        self,
        *,
        session_id:     str | None            = None,
        topic:          str                   = "",
        reasoning_type: ReasoningType         = ReasoningType.GENERIC,
        reasoner_id:    str | None            = None,
        timeout_s:      float                 = DEFAULT_SESSION_TIMEOUT_S,
        metadata:       dict[str, Any] | None = None,
        overwrite:      bool                  = False,
    ) -> ReasoningSession:
        session = ReasoningSession(
            session_id     = session_id or str(uuid.uuid4()),
            topic          = topic,
            reasoning_type = reasoning_type,
            reasoner_id    = reasoner_id,
            timeout_s      = timeout_s,
            metadata       = dict(metadata or {}),
        )
        self._registry.register(session, overwrite=overwrite)
        with self._lock:
            self._created += 1
        return session

    # -- Templates ─────────────────────────────────────────────────────────────

    def register_template(
        self,
        name:           str,
        default_config: dict[str, Any],
    ) -> None:
        with self._lock:
            self._templates[name] = dict(default_config)

    def create_from_template(
        self,
        template_name: str,
        *,
        session_id:  str | None = None,
        topic:       str        = "",
        **overrides: Any,
    ) -> ReasoningSession:
        with self._lock:
            tmpl = dict(self._templates.get(template_name, {}))
        tmpl.update(overrides)
        return self.create(
            session_id     = session_id,
            topic          = topic,
            reasoning_type = tmpl.pop("reasoning_type", ReasoningType.GENERIC),
            reasoner_id    = tmpl.pop("reasoner_id", None),
            timeout_s      = tmpl.pop("timeout_s", DEFAULT_SESSION_TIMEOUT_S),
            metadata       = tmpl,
        )

    # -- Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "created":   self._created,
                "templates": list(self._templates.keys()),
            }


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:    threading.Lock               = threading.Lock()
_FACTORY: ReasoningSessionFactory | None = None


def get_reasoning_factory() -> ReasoningSessionFactory:
    global _FACTORY
    if _FACTORY is None:
        with _LOCK:
            if _FACTORY is None:
                _FACTORY = ReasoningSessionFactory()
    return _FACTORY


def reset_reasoning_factory() -> None:
    global _FACTORY
    with _LOCK:
        _FACTORY = None
