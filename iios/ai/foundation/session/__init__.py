"""
iios.ai.foundation.session
===========================
A1 AI Foundation -- Session Framework.

    from iios.ai.foundation.session import AISessionManager, AISession

A1 AI Foundation -- Phase 3, Module 1
"""
from __future__ import annotations

from .session_state    import SessionState, TERMINAL_SESSION_STATES, ACTIVE_SESSION_STATES, can_session_transition
from .session_metadata import SessionMetadata
from .ai_session       import AISession
from .session_factory  import SessionFactory
from .session_manager  import AISessionManager

__all__ = [
    "SessionState",
    "TERMINAL_SESSION_STATES",
    "ACTIVE_SESSION_STATES",
    "can_session_transition",
    "SessionMetadata",
    "AISession",
    "SessionFactory",
    "AISessionManager",
]
