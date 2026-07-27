"""
iios.ai.foundation.context
===========================
A1 AI Foundation -- Context Framework.

    from iios.ai.foundation.context import AIContext, ContextBuilder

A1 AI Foundation -- Phase 3, Module 1
"""
from __future__ import annotations

from .context_metadata   import ContextMetadata
from .ai_context         import AIContext, ContextEntry
from .context_builder    import ContextBuilder
from .context_validator  import ContextValidator, ContextValidationResult
from .context_compressor import ContextCompressor, TruncationContextCompressor, CompressionResult

__all__ = [
    "ContextMetadata",
    "AIContext",
    "ContextEntry",
    "ContextBuilder",
    "ContextValidator",
    "ContextValidationResult",
    "ContextCompressor",
    "TruncationContextCompressor",
    "CompressionResult",
]
