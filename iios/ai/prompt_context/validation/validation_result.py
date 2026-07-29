"""
validation_result.py -- iios.ai.prompt_context.validation
============================================================
:class:`ValidationResult` -- immutable outcome of a validation check.

A3 Prompt & Context Platform -- Phase 3, Module 3
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple


@dataclass(frozen=True)
class ValidationResult:
    """Immutable result of a validation operation."""
    is_valid: bool
    errors:   Tuple[str, ...] = field(default_factory=tuple)
