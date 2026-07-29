"""
policies.py -- iios.ai.prompt_context.policy
===============================================
Policy interfaces (M3 Policy Framework) for the A3 Prompt & Context
Platform, plus sane default implementations.  All policies are
dependency-injected -- no policy is hard-wired into the engine layer.

A3 Prompt & Context Platform -- Phase 3, Module 3
"""
from __future__ import annotations

import abc
from typing import List, Optional

from ..core.context_segment import ContextSegment
from ..core.prompt_template import PromptTemplate
from ..core.prompt_version  import PromptVersion
from ..exceptions           import AIPromptPolicyViolationError
from ..validation.validation_result import ValidationResult


# ---------------------------------------------------------------------------
# Prompt Selection Policy
# ---------------------------------------------------------------------------

class PromptSelectionPolicy(abc.ABC):
    """Selects a single prompt template from a list of candidates."""

    @abc.abstractmethod
    def select(self, candidates: List[PromptTemplate]) -> Optional[PromptTemplate]:
        ...


class DefaultPromptSelectionPolicy(PromptSelectionPolicy):
    """Selects the first enabled template that has an active version."""

    def select(self, candidates: List[PromptTemplate]) -> Optional[PromptTemplate]:
        for candidate in candidates:
            if candidate.enabled and candidate.active_version is not None:
                return candidate
        return None


# ---------------------------------------------------------------------------
# Context Priority Policy
# ---------------------------------------------------------------------------

class ContextPriorityPolicy(abc.ABC):
    """Orders context segments prior to assembly/truncation."""

    @abc.abstractmethod
    def order(self, segments: List[ContextSegment]) -> List[ContextSegment]:
        ...


class DefaultContextPriorityPolicy(ContextPriorityPolicy):
    """Orders segments ascending by :class:`ContextPriority` value."""

    def order(self, segments: List[ContextSegment]) -> List[ContextSegment]:
        return sorted(segments, key=lambda s: s.priority.value)


# ---------------------------------------------------------------------------
# Template Version Policy
# ---------------------------------------------------------------------------

class TemplateVersionPolicy(abc.ABC):
    """Resolves which :class:`PromptVersion` of a template should be used."""

    @abc.abstractmethod
    def resolve(self, template: PromptTemplate) -> Optional[PromptVersion]:
        ...


class ActiveVersionPolicy(TemplateVersionPolicy):
    """Always resolves to the template's currently active version."""

    def resolve(self, template: PromptTemplate) -> Optional[PromptVersion]:
        return template.active_version


# ---------------------------------------------------------------------------
# Validation Policy
# ---------------------------------------------------------------------------

class ValidationPolicy(abc.ABC):
    """Decides how to react to a :class:`ValidationResult`."""

    @abc.abstractmethod
    def enforce(self, result: ValidationResult) -> None:
        ...


class StrictValidationPolicy(ValidationPolicy):
    """Raises :class:`AIPromptPolicyViolationError` on any validation failure."""

    def enforce(self, result: ValidationResult) -> None:
        if not result.is_valid:
            raise AIPromptPolicyViolationError("; ".join(result.errors))


class PermissiveValidationPolicy(ValidationPolicy):
    """Never raises -- validation failures are the caller's responsibility to inspect."""

    def enforce(self, result: ValidationResult) -> None:
        return None


# ---------------------------------------------------------------------------
# Token Budget Policy
# ---------------------------------------------------------------------------

class TokenBudgetPolicy(abc.ABC):
    """Determines the token budget available to a given module."""

    @abc.abstractmethod
    def max_tokens_for(self, module_id: str) -> int:
        ...


class FixedTokenBudgetPolicy(TokenBudgetPolicy):
    """Returns the same fixed token budget for every module."""

    def __init__(self, max_tokens: int = 8_192) -> None:
        if max_tokens <= 0:
            raise ValueError(f"max_tokens must be positive; got {max_tokens}.")
        self._max_tokens = max_tokens

    def max_tokens_for(self, module_id: str) -> int:
        return self._max_tokens


class PerModuleTokenBudgetPolicy(TokenBudgetPolicy):
    """Returns a per-module token budget with a default fallback."""

    def __init__(self, budgets: Optional[dict] = None, default: int = 8_192) -> None:
        self._budgets = dict(budgets or {})
        self._default = default

    def max_tokens_for(self, module_id: str) -> int:
        return self._budgets.get(module_id, self._default)
