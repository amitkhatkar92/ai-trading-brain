"""
prompt_variables.py -- iios.ai.prompt_context.core
=====================================================
:class:`PromptVariables` -- immutable variable bag for prompt rendering.
:class:`PromptResult`    -- immutable outcome of a prompt composition.

A3 Prompt & Context Platform -- Phase 3, Module 3
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class PromptVariables:
    """Immutable bag of template substitution values."""
    values: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def with_value(self, key: str, value: Any) -> "PromptVariables":
        merged = dict(self.values)
        merged[key] = value
        return PromptVariables(merged)

    def __contains__(self, key: str) -> bool:
        return key in self.values


@dataclass(frozen=True)
class PromptResult:
    """Immutable result of :class:`PromptComposer`.compose()."""
    prompt_id:         str
    version_id:         str
    rendered_text:      str
    system_text:        str
    variables_used:     Tuple[str, ...]
    estimated_tokens:   int
    context_included:   bool
    created_at:         float = field(default_factory=time.time)
