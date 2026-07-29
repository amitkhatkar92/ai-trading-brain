"""
capability_type.py -- iios.ai.model_management.capabilities
=============================================================
:class:`ModelCapabilityType` — immutable enumeration of AI model capabilities.

A2 Model Management — Phase 3, Module 2
"""
from __future__ import annotations

from enum import Enum


class ModelCapabilityType(str, Enum):
    """Immutable capability definitions for AI model discovery and routing."""
    CHAT              = "chat"
    COMPLETION        = "completion"
    EMBEDDINGS        = "embeddings"
    VISION            = "vision"
    AUDIO             = "audio"
    TOOL_CALLING      = "tool_calling"
    STRUCTURED_OUTPUT = "structured_output"
    STREAMING         = "streaming"
    CODE_GENERATION   = "code_generation"
    REASONING         = "reasoning"
