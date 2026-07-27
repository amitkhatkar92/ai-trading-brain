"""
context_builder.py -- iios.ai.foundation.context
=================================================
:class:`ContextBuilder` -- fluent builder for :class:`AIContext`.

A1 AI Foundation -- Phase 3, Module 1
"""
from __future__ import annotations

from typing import Any, Optional

from .ai_context        import AIContext
from .context_metadata  import ContextMetadata
from .context_validator import ContextValidator
from ..exceptions       import AIContextBuildError


class ContextBuilder:
    """
    Fluent builder for :class:`AIContext`.

    Usage::

        ctx = (
            ContextBuilder(session_id="s-001", module_id="a3")
            .with_max_tokens(4_096)
            .add_system("You are a trading analyst.")
            .add_retrieved("NIFTY is up 0.8%.", estimated_tokens=12)
            .add_user("What is the regime?", estimated_tokens=8)
            .build()
        )

    Parameters
    ----------
    session_id : Originating session identifier.
    module_id :  Building AI module identifier.
    """

    def __init__(self, session_id: str, module_id: str) -> None:
        self._session_id = session_id
        self._module_id  = module_id
        self._trace_id:  str   = ""
        self._capability: str  = "completion"
        self._max_tokens: int  = 8_192
        self._tags:      dict  = {}
        self._pending:   list  = []    # (role, content, label, estimated_tokens, metadata)
        self._validate:  bool  = True

    # ── Configuration ──────────────────────────────────────────────────────────

    def with_trace_id(self, trace_id: str) -> "ContextBuilder":
        self._trace_id = trace_id
        return self

    def with_capability(self, capability: str) -> "ContextBuilder":
        self._capability = capability
        return self

    def with_max_tokens(self, max_tokens: int) -> "ContextBuilder":
        if max_tokens <= 0:
            raise AIContextBuildError(f"max_tokens must be positive; got {max_tokens}.")
        self._max_tokens = max_tokens
        return self

    def with_tag(self, key: str, value: str) -> "ContextBuilder":
        self._tags[key] = value
        return self

    def skip_validation(self) -> "ContextBuilder":
        self._validate = False
        return self

    # ── Content additions ──────────────────────────────────────────────────────

    def add_system(
        self,
        content: str,
        *,
        estimated_tokens: int = 0,
        **metadata: Any,
    ) -> "ContextBuilder":
        self._pending.append(("system", content, "system_prompt", estimated_tokens, metadata))
        return self

    def add_user(
        self,
        content: str,
        *,
        label:            str = "user_query",
        estimated_tokens: int = 0,
        **metadata: Any,
    ) -> "ContextBuilder":
        self._pending.append(("user", content, label, estimated_tokens, metadata))
        return self

    def add_assistant(
        self,
        content: str,
        *,
        estimated_tokens: int = 0,
        **metadata: Any,
    ) -> "ContextBuilder":
        self._pending.append(("assistant", content, "assistant", estimated_tokens, metadata))
        return self

    def add_retrieved(
        self,
        content: str,
        *,
        label:            str = "retrieved",
        estimated_tokens: int = 0,
        **metadata: Any,
    ) -> "ContextBuilder":
        self._pending.append(("user", content, label, estimated_tokens, metadata))
        return self

    # ── Build ──────────────────────────────────────────────────────────────────

    def build(self) -> AIContext:
        """
        Assemble and return the :class:`AIContext`.

        Raises
        ------
        AIContextBuildError
            If the pending content cannot be assembled.
        AIContextValidationError
            If validation is enabled and the context fails validation.
        AIContextTooLargeError
            If the estimated token count exceeds ``max_tokens``.
        """
        meta = ContextMetadata.create(
            session_id = self._session_id,
            module_id  = self._module_id,
            trace_id   = self._trace_id,
            capability = self._capability,
            max_tokens = self._max_tokens,
            **self._tags,
        )
        ctx = AIContext(meta)
        for role, content, label, est_tokens, extra in self._pending:
            ctx.add_entry(role, content, label=label, estimated_tokens=est_tokens, **extra)

        if self._validate:
            ContextValidator().validate(ctx)
        return ctx
