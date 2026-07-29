"""
token_estimator.py -- iios.ai.prompt_context.core
====================================================
Provider-independent token estimation heuristic.

A3 never calls a provider tokenizer -- estimation is a simple,
deterministic character-based heuristic suitable for budget planning
prior to execution by A1/A2.

A3 Prompt & Context Platform -- Phase 3, Module 3
"""
from __future__ import annotations

_CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """
    Estimate the token count of ``text`` using a provider-independent
    heuristic (~4 characters per token, minimum 1 for non-empty text).
    """
    if not text:
        return 0
    return max(1, len(text) // _CHARS_PER_TOKEN)
