"""
event_types.py -- iios.ai.prompt_context.events
==================================================
:class:`PromptEventType` -- enumeration of all A3 domain event types.

A3 Prompt & Context Platform -- Phase 3, Module 3
"""
from __future__ import annotations

from enum import Enum


class PromptEventType(str, Enum):
    PROMPT_REGISTERED    = "prompt.registered"
    PROMPT_REMOVED       = "prompt.removed"
    PROMPT_ENABLED       = "prompt.enabled"
    PROMPT_DISABLED      = "prompt.disabled"
    PROMPT_UPDATED       = "prompt.updated"
    PROMPT_RENDERED      = "prompt.rendered"
    CONTEXT_BUILT        = "context.built"
    VALIDATION_SUCCEEDED = "validation.succeeded"
    VALIDATION_FAILED    = "validation.failed"
    TEMPLATE_ACTIVATED   = "template.activated"
