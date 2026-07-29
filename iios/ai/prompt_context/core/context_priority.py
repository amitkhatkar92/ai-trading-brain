"""
context_priority.py -- iios.ai.prompt_context.core
=====================================================
:class:`ContextPriority` -- ordering used by the Context Assembler when
merging and truncating context segments from multiple sources.

Lower numeric value = higher priority (kept first when the token budget
is constrained).

A3 Prompt & Context Platform -- Phase 3, Module 3
"""
from __future__ import annotations

from enum import IntEnum


class ContextPriority(IntEnum):
    """Relative importance of a :class:`ContextSegment`."""
    CRITICAL   = 0   # e.g. system instructions -- never dropped
    HIGH       = 1   # e.g. the current user query
    NORMAL     = 2   # e.g. conversation history
    LOW        = 3   # e.g. retrieved / supplementary documents
    BACKGROUND = 4   # e.g. optional enrichment, dropped first
