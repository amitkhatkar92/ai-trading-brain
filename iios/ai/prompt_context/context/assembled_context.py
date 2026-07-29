"""
assembled_context.py -- iios.ai.prompt_context.context
=========================================================
:class:`AssembledContext` -- immutable result of context assembly.

A3 Prompt & Context Platform -- Phase 3, Module 3
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from ..core.context_metadata import ContextMetadata
from ..core.context_segment  import ContextSegment


@dataclass(frozen=True)
class AssembledContext:
    """Immutable, prioritized, budget-checked collection of context segments."""
    metadata:         ContextMetadata
    segments:         Tuple[ContextSegment, ...]
    estimated_tokens: int
    truncated:        bool

    @property
    def context_id(self) -> str:
        return self.metadata.context_id

    @property
    def is_within_budget(self) -> bool:
        return self.estimated_tokens <= self.metadata.max_tokens

    def to_text(self, separator: str = "\n\n") -> str:
        """Render all segments (in assembled order) into a single text block."""
        return separator.join(s.content for s in self.segments)
