"""
governance_context.py -- iios.ai.governance.core
==================================================
:class:`GovernanceContext` — immutable request context for governance evaluation.

A8 AI Governance Platform — Phase 3, Module 8
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, FrozenSet, Optional, Tuple


@dataclass(frozen=True)
class GovernanceContext:
    """
    Immutable snapshot of the circumstances surrounding a governance evaluation.

    ``action``      — the action being evaluated (e.g. "model.invoke", "data.read").
    ``resource``    — resource identifier the action targets.
    ``principal_id`` — identity (agent/user/system) requesting the action.
    ``environment`` — key→value runtime context (model version, market state, etc.).
    """

    context_id:   str
    action:       str
    resource:     str
    principal_id: str
    session_id:   Optional[str]
    environment:  FrozenSet[Tuple[str, Any]]
    requested_at: float

    @classmethod
    def create(
        cls,
        action:       str,
        resource:     str,
        principal_id: str,
        session_id:   Optional[str] = None,
        **environment: Any,
    ) -> "GovernanceContext":
        return cls(
            context_id   = str(uuid.uuid4()),
            action       = action,
            resource     = resource,
            principal_id = principal_id,
            session_id   = session_id,
            environment  = frozenset(environment.items()),
            requested_at = time.time(),
        )

    def get_env(self, key: str, default: Any = None) -> Any:
        for k, v in self.environment:
            if k == key:
                return v
        return default
