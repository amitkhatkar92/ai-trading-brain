"""
context_validator.py -- iios.ai.foundation.context
====================================================
:class:`ContextValidator` -- validates an :class:`AIContext` before
submission to the execution pipeline.

A1 AI Foundation -- Phase 3, Module 1
"""
from __future__ import annotations

from typing import List

from .ai_context   import AIContext
from ..exceptions  import AIContextValidationError, AIContextTooLargeError


class ContextValidationResult:
    """Result of a context validation pass."""

    def __init__(self) -> None:
        self._errors:   List[str] = []
        self._warnings: List[str] = []

    def add_error(self, message: str) -> None:
        self._errors.append(message)

    def add_warning(self, message: str) -> None:
        self._warnings.append(message)

    @property
    def is_valid(self) -> bool:
        return len(self._errors) == 0

    @property
    def errors(self) -> List[str]:
        return list(self._errors)

    @property
    def warnings(self) -> List[str]:
        return list(self._warnings)


class ContextValidator:
    """
    Validates an :class:`AIContext` for structural correctness and
    budget compliance.

    Rules applied
    -------------
    * At least one entry must be present.
    * Entry content must not be blank.
    * Estimated token count must not exceed ``metadata.max_tokens``.
    * At most one system message (warn if multiple).
    """

    def validate(self, context: AIContext) -> ContextValidationResult:
        """
        Validate ``context`` and return a :class:`ContextValidationResult`.

        Also raises immediately on hard errors:
        * ``AIContextValidationError`` -- structural violations.
        * ``AIContextTooLargeError``   -- token budget exceeded.
        """
        result = ContextValidationResult()
        entries = context.entries()

        if not entries:
            result.add_error("Context has no entries.")

        for i, entry in enumerate(entries):
            if not entry.content.strip():
                result.add_error(f"Entry {i} (role={entry.role!r}) has blank content.")

        system_count = sum(1 for e in entries if e.role == "system")
        if system_count > 1:
            result.add_warning(f"Context has {system_count} system messages; expected 1.")

        if context.estimated_tokens > context.max_tokens:
            raise AIContextTooLargeError(
                context.estimated_tokens, context.max_tokens
            )

        if not result.is_valid:
            raise AIContextValidationError("; ".join(result.errors))

        return result
