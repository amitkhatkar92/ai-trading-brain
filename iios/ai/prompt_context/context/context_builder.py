"""
context_builder.py -- iios.ai.prompt_context.context
=======================================================
:class:`ContextBuilder` -- fluent builder that assembles context
segments from multiple sources into an :class:`AssembledContext`.

A3 Prompt & Context Platform -- Phase 3, Module 3
"""
from __future__ import annotations

from typing import Any, List, Optional

from ..core.context_metadata import ContextMetadata
from ..core.context_priority import ContextPriority
from ..core.context_segment  import ContextSegment
from ..exceptions            import AIContextIncompleteError
from ..events.event_bus      import PromptEventBus
from ..events.prompt_events  import ContextBuiltEvent
from .assembled_context      import AssembledContext
from .context_assembler      import ContextAssembler

SYSTEM_ID = "iios:ai:prompt_context:context_builder"


class ContextBuilder:
    """
    Fluent builder for :class:`AssembledContext`.

    Usage::

        ctx = (
            ContextBuilder("session-1", "my.module", assembler)
            .with_max_tokens(4_096)
            .add_system("You are a trading analyst.")
            .add_retrieved("NIFTY is up 0.8%.")
            .add_user("What is the regime?")
            .build()
        )
    """

    def __init__(
        self,
        session_id: str,
        module_id:  str,
        assembler:  Optional[ContextAssembler] = None,
        event_bus:  Optional[PromptEventBus]   = None,
    ) -> None:
        self._session_id = session_id
        self._module_id  = module_id
        self._trace_id:   str                    = ""
        self._max_tokens: int                    = 8_192
        self._segments:   List[ContextSegment]    = []
        self._assembler:  ContextAssembler        = assembler or ContextAssembler()
        self._event_bus:  Optional[PromptEventBus] = event_bus

    # ── Configuration ─────────────────────────────────────────────────────────

    def with_trace_id(self, trace_id: str) -> "ContextBuilder":
        self._trace_id = trace_id
        return self

    def with_max_tokens(self, max_tokens: int) -> "ContextBuilder":
        if max_tokens <= 0:
            raise AIContextIncompleteError(f"max_tokens must be positive; got {max_tokens}.")
        self._max_tokens = max_tokens
        return self

    # ── Content additions ─────────────────────────────────────────────────────

    def add_segment(
        self,
        source:  str,
        content: str,
        *,
        priority:         ContextPriority = ContextPriority.NORMAL,
        estimated_tokens: Optional[int]   = None,
        **metadata: Any,
    ) -> "ContextBuilder":
        self._segments.append(
            ContextSegment.create(
                source, content, priority=priority, estimated_tokens=estimated_tokens, **metadata
            )
        )
        return self

    def add_system(self, content: str, **metadata: Any) -> "ContextBuilder":
        return self.add_segment("system", content, priority=ContextPriority.CRITICAL, **metadata)

    def add_user(self, content: str, **metadata: Any) -> "ContextBuilder":
        return self.add_segment("user", content, priority=ContextPriority.HIGH, **metadata)

    def add_history(self, content: str, **metadata: Any) -> "ContextBuilder":
        return self.add_segment("history", content, priority=ContextPriority.NORMAL, **metadata)

    def add_retrieved(self, content: str, **metadata: Any) -> "ContextBuilder":
        return self.add_segment("retrieval", content, priority=ContextPriority.LOW, **metadata)

    def add_background(self, content: str, **metadata: Any) -> "ContextBuilder":
        return self.add_segment("background", content, priority=ContextPriority.BACKGROUND, **metadata)

    # ── Multi-source merge ────────────────────────────────────────────────────

    def merge(self, other: AssembledContext) -> "ContextBuilder":
        """Merge all segments from a previously assembled context into this builder."""
        self._segments.extend(other.segments)
        return self

    # ── Build ─────────────────────────────────────────────────────────────────

    def build(self) -> AssembledContext:
        """
        Assemble and return the :class:`AssembledContext`.

        Raises
        ------
        AIContextIncompleteError
            If no segment fits within the token budget.
        """
        metadata = ContextMetadata.create(
            session_id = self._session_id,
            module_id  = self._module_id,
            trace_id   = self._trace_id,
            max_tokens = self._max_tokens,
        )
        assembled = self._assembler.assemble(metadata, self._segments)
        if self._event_bus is not None:
            self._event_bus.publish(
                ContextBuiltEvent.create(
                    SYSTEM_ID, assembled.context_id, len(assembled.segments),
                    assembled.estimated_tokens, assembled.is_within_budget,
                )
            )
        return assembled
