"""
validators.py -- iios.ai.prompt_context.validation
=====================================================
:class:`PromptValidator`, :class:`ContextValidator`, :class:`VariableValidator`
-- non-throwing validators returning :class:`ValidationResult`.

A3 Prompt & Context Platform -- Phase 3, Module 3
"""
from __future__ import annotations

from typing import List, Optional

from ..context.assembled_context import AssembledContext
from ..core.prompt_template       import PromptTemplate
from ..core.prompt_variables      import PromptVariables
from ..core.prompt_version        import PromptVersion
from .validation_result           import ValidationResult


class VariableValidator:
    """Validates that all declared template variables are supplied."""

    def validate(self, version: PromptVersion, variables: PromptVariables) -> ValidationResult:
        missing = [v for v in version.variables if v not in variables]
        if missing:
            return ValidationResult(False, tuple(f"missing variable: {m}" for m in missing))
        return ValidationResult(True)


class PromptValidator:
    """
    Validates a prompt template's structural integrity and (optionally)
    that supplied variables satisfy the active version's requirements.
    """

    def __init__(self, variable_validator: Optional[VariableValidator] = None) -> None:
        self._variable_validator = variable_validator or VariableValidator()

    def validate_template_text(self, template_text: str) -> ValidationResult:
        errors: List[str] = []
        if not template_text or not template_text.strip():
            errors.append("template_text is empty")
        if template_text.count("{{") != template_text.count("}}"):
            errors.append("unbalanced variable delimiters ('{{' / '}}')")
        return ValidationResult(len(errors) == 0, tuple(errors))

    def validate(
        self,
        template:  PromptTemplate,
        variables: Optional[PromptVariables] = None,
    ) -> ValidationResult:
        errors: List[str] = []

        if not template.enabled:
            errors.append(f"prompt {template.prompt_id!r} is disabled")

        version = template.active_version
        if version is None:
            errors.append(f"prompt {template.prompt_id!r} has no active version")
        else:
            text_result = self.validate_template_text(version.template_text)
            errors.extend(text_result.errors)

            if not text_result.errors:
                for name in version.variables:
                    if not name or not name.replace("_", "").isalnum():
                        errors.append(f"invalid declared variable name: {name!r}")

            if variables is not None and version is not None:
                var_result = self._variable_validator.validate(version, variables)
                errors.extend(var_result.errors)

        return ValidationResult(len(errors) == 0, tuple(errors))


class ContextValidator:
    """Validates completeness of an assembled context against its own budget."""

    def validate(self, context: AssembledContext) -> ValidationResult:
        errors: List[str] = []
        if not context.segments:
            errors.append("context has no segments")
        if not context.is_within_budget:
            errors.append(
                f"estimated_tokens={context.estimated_tokens} "
                f"exceeds max_tokens={context.metadata.max_tokens}"
            )
        if context.truncated:
            errors.append("context was truncated -- some segments were dropped to fit the budget")
        return ValidationResult(len(errors) == 0, tuple(errors))
