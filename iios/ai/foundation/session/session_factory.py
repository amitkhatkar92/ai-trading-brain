"""
session_factory.py -- iios.ai.foundation.session
=================================================
:class:`SessionFactory` -- creates :class:`AISession` instances with
validated metadata.

A1 AI Foundation -- Phase 3, Module 1
"""
from __future__ import annotations

from typing import Optional

from .ai_session       import AISession
from .session_metadata import SessionMetadata


class SessionFactory:
    """
    Factory for :class:`AISession` instances.

    Centralises session creation so defaults and validation rules
    are applied consistently across all AI modules.

    Parameters
    ----------
    default_ttl_s :    Default session TTL when not explicitly specified.
    default_priority : Default priority string.
    """

    DEFAULT_TTL_S:      float = 300.0
    DEFAULT_PRIORITY:   str   = "normal"
    DEFAULT_CAPABILITY: str   = "completion"

    def __init__(
        self,
        default_ttl_s:      float = DEFAULT_TTL_S,
        default_priority:   str   = DEFAULT_PRIORITY,
        default_capability: str   = DEFAULT_CAPABILITY,
    ) -> None:
        self._default_ttl_s      = default_ttl_s
        self._default_priority   = default_priority
        self._default_capability = default_capability

    def create(
        self,
        module_id:  str,
        *,
        priority:   Optional[str]   = None,
        user_id:    str              = "",
        ttl_s:      Optional[float]  = None,
        capability: Optional[str]    = None,
        trace_id:   str              = "",
        **tags: str,
    ) -> AISession:
        """
        Create and return a new :class:`AISession` in PENDING state.

        Parameters
        ----------
        module_id :  Identifier of the requesting AI module.
        priority :   Request priority (defaults to factory default).
        user_id :    Optional caller identifier.
        ttl_s :      TTL override (defaults to factory default).
        capability : Required capability (defaults to factory default).
        trace_id :   Distributed trace ID (auto-generated if blank).
        **tags :     Arbitrary string tags attached to session metadata.
        """
        metadata = SessionMetadata.create(
            module_id  = module_id,
            priority   = priority   or self._default_priority,
            user_id    = user_id,
            ttl_s      = ttl_s      if ttl_s is not None else self._default_ttl_s,
            capability = capability or self._default_capability,
            trace_id   = trace_id,
            **tags,
        )
        return AISession(metadata)

    def create_from_metadata(self, metadata: SessionMetadata) -> AISession:
        """Create a session from a pre-built :class:`SessionMetadata` object."""
        return AISession(metadata)
