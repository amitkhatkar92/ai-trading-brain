"""
prompt_category.py -- iios.ai.prompt_context.core
====================================================
:class:`PromptCategory` -- immutable enumeration of prompt template
categories used across the A3 Prompt & Context Platform.

A3 Prompt & Context Platform -- Phase 3, Module 3
"""
from __future__ import annotations

from enum import Enum


class PromptCategory(str, Enum):
    """Category of a prompt template -- drives composition behaviour."""
    SYSTEM            = "system"
    INSTRUCTION       = "instruction"
    CONVERSATIONAL    = "conversational"
    ANALYTICAL        = "analytical"
    STRUCTURED_OUTPUT = "structured_output"
    TOOL_CALLING      = "tool_calling"
    SUMMARIZATION     = "summarization"
    CUSTOM            = "custom"
