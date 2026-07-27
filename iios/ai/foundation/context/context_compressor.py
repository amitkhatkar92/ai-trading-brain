"""
context_compressor.py -- iios.ai.foundation.context
=====================================================
:class:`ContextCompressor` -- placeholder compression interface.

When an assembled context exceeds the token budget, the compressor
applies a reduction strategy to bring it within budget.

Concrete implementations (truncation, summarisation, sliding-window)
are provided by A3 Context Assembly once LLM providers are wired up.
This module defines the interface and a simple truncation reference
implementation.

A1 AI Foundation -- Phase 3, Module 1
"""
from __future__ import annotations

import abc
from typing import Any, Dict, Optional

from .ai_context  import AIContext
from ..exceptions import AIContextTooLargeError


class CompressionResult:
    """Records the outcome of a compression operation."""

    def __init__(
        self,
        original_tokens:   int,
        compressed_tokens: int,
        entries_removed:   int,
        strategy:          str,
    ) -> None:
        self.original_tokens   = original_tokens
        self.compressed_tokens = compressed_tokens
        self.entries_removed   = entries_removed
        self.strategy          = strategy
        self.reduction_pct     = (
            round((original_tokens - compressed_tokens) / original_tokens * 100, 1)
            if original_tokens > 0 else 0.0
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_tokens":   self.original_tokens,
            "compressed_tokens": self.compressed_tokens,
            "entries_removed":   self.entries_removed,
            "reduction_pct":     self.reduction_pct,
            "strategy":          self.strategy,
        }


class ContextCompressor(abc.ABC):
    """
    Abstract context compressor.

    Implementations reduce a context that exceeds the token budget
    using provider-specific or generic strategies.

    A3 Context Assembly provides concrete implementations.
    """

    @abc.abstractmethod
    def compress(
        self,
        context:   AIContext,
        *,
        target_tokens: Optional[int] = None,
    ) -> CompressionResult:
        """
        Reduce ``context`` to fit within the token budget.

        Parameters
        ----------
        context :       The context to compress (mutated in-place).
        target_tokens : Override target budget (defaults to ``context.max_tokens``).

        Returns
        -------
        CompressionResult
            Statistics describing the compression applied.

        Raises
        ------
        AIContextTooLargeError
            If the compressor cannot bring the context within budget.
        """


class TruncationContextCompressor(ContextCompressor):
    """
    Reference implementation: removes entries from the end (LIFO) until
    the context is within budget.

    This is intentionally simple and provider-independent.  It preserves
    the system message and user query by discarding retrieved context first.
    """

    def compress(
        self,
        context:       AIContext,
        *,
        target_tokens: Optional[int] = None,
    ) -> CompressionResult:
        target    = target_tokens or context.max_tokens
        original  = context.estimated_tokens
        removed   = 0

        while context.estimated_tokens > target:
            entry = context.remove_last()
            if entry is None:
                break
            removed += 1

        if context.estimated_tokens > target:
            raise AIContextTooLargeError(context.estimated_tokens, target)

        return CompressionResult(
            original_tokens   = original,
            compressed_tokens = context.estimated_tokens,
            entries_removed   = removed,
            strategy          = "truncation",
        )
