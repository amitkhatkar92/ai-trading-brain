"""
capability_request.py -- iios.ai.capability.engine
====================================================
:class:`CapabilityContext` — caller context (who, session, trace).
:class:`CapabilityRequest` — immutable invocation request.

A9 Enterprise Capability Platform — Phase 3, Module 9
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, Optional, Tuple


@dataclass(frozen=True)
class CapabilityContext:
    """Immutable context provided by the caller at invocation time."""

    context_id:   str
    principal_id: str
    session_id:   str
    trace_id:     str
    environment:  FrozenSet[Tuple[str, str]]   # key-value pairs

    # ── factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        principal_id: str,
        session_id:   str  = "",
        trace_id:     str  = "",
        **env_kwargs: str,
    ) -> "CapabilityContext":
        return cls(
            context_id   = str(uuid.uuid4()),
            principal_id = principal_id,
            session_id   = session_id or str(uuid.uuid4()),
            trace_id     = trace_id   or str(uuid.uuid4()),
            environment  = frozenset(env_kwargs.items()),
        )

    def get_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Return the environment value for *key*, or *default*."""
        for k, v in self.environment:
            if k == key:
                return v
        return default


@dataclass(frozen=True)
class CapabilityRequest:
    """Immutable invocation request for a single capability."""

    request_id:    str
    capability_id: str
    context:       CapabilityContext
    parameters:    FrozenSet[Tuple[str, Any]]  # key-value pairs
    requested_at:  float

    # ── factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        capability_id: str,
        context:       CapabilityContext,
        **parameters: Any,
    ) -> "CapabilityRequest":
        return cls(
            request_id    = str(uuid.uuid4()),
            capability_id = capability_id,
            context       = context,
            parameters    = frozenset(parameters.items()),
            requested_at  = time.time(),
        )

    def get_param(self, key: str, default: Any = None) -> Any:
        """Return the parameter value for *key*, or *default*."""
        for k, v in self.parameters:
            if k == key:
                return v
        return default

    def params_dict(self) -> Dict[str, Any]:
        """Return parameters as a plain dict."""
        return dict(self.parameters)
