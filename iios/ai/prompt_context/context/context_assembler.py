"""
context_assembler.py -- iios.ai.prompt_context.context
=========================================================
:class:`ContextAssembler` -- merges context segments from multiple
sources, prioritizes them, and truncates to fit the configured token
budget.  Provider-independent -- never calls a tokenizer.

A3 Prompt & Context Platform -- Phase 3, Module 3
"""
from __future__ import annotations

from typing import Iterable, List

from ..core.context_metadata import ContextMetadata
from ..core.context_segment  import ContextSegment
from ..exceptions            import AIContextIncompleteError
from .assembled_context      import AssembledContext


class ContextAssembler:
    """
    Priority-ordered, budget-aware context assembler.

    Segments are sorted by :class:`ContextPriority` (ascending numeric
    value -- CRITICAL first).  Segments are added greedily in priority
    order until the token budget would be exceeded; remaining segments
    are dropped and ``truncated`` is set to ``True``.
    """

    def assemble(
        self,
        metadata: ContextMetadata,
        segments: Iterable[ContextSegment],
    ) -> AssembledContext:
        """
        Raises
        ------
        AIContextIncompleteError
            If no segment fits within the token budget.
        """
        ordered: List[ContextSegment] = sorted(segments, key=lambda s: s.priority.value)

        selected: List[ContextSegment] = []
        total_tokens = 0
        truncated    = False

        for seg in ordered:
            if total_tokens + seg.estimated_tokens > metadata.max_tokens:
                truncated = True
                continue
            selected.append(seg)
            total_tokens += seg.estimated_tokens

        if not selected:
            raise AIContextIncompleteError(
                f"No context segments fit within max_tokens={metadata.max_tokens} "
                f"for context_id={metadata.context_id!r}."
            )

        return AssembledContext(
            metadata         = metadata,
            segments         = tuple(selected),
            estimated_tokens = total_tokens,
            truncated        = truncated,
        )
