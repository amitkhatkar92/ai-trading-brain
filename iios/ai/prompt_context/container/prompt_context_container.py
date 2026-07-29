"""
prompt_context_container.py -- iios.ai.prompt_context.container
===================================================================
:class:`PromptContextContainer` -- DI composition root wiring every
A3 component: registry, version manager, context assembler, composer,
validators, and policies.  Mirrors the ``AIContainer`` pattern from A1.

A3 Prompt & Context Platform -- Phase 3, Module 3
"""
from __future__ import annotations

from typing import Optional

from ..composer.prompt_composer   import PromptComposer
from ..composer.prompt_renderer   import PromptRenderer
from ..context.context_assembler  import ContextAssembler
from ..events.event_bus           import PromptEventBus
from ..policy.policies            import (
    StrictValidationPolicy,
    TokenBudgetPolicy,
    FixedTokenBudgetPolicy,
    ValidationPolicy,
)
from ..registry.prompt_registry   import PromptRegistry
from ..validation.validators      import ContextValidator, PromptValidator
from ..versioning.prompt_history  import PromptHistory
from ..versioning.version_manager import VersionManager


class PromptContextContainer:
    """
    DI composition root for the A3 Prompt & Context Platform.

    Usage::

        container = PromptContextContainer()
        container.build()
        container.registry.register(...)
    """

    def __init__(
        self,
        token_budget_policy: Optional[TokenBudgetPolicy] = None,
        validation_policy:   Optional[ValidationPolicy]  = None,
    ) -> None:
        self._event_bus:       PromptEventBus  = PromptEventBus()
        self._history:         PromptHistory   = PromptHistory()
        self._version_manager: VersionManager  = VersionManager(self._history)
        self._registry:        PromptRegistry  = PromptRegistry(
            self._version_manager, event_bus=self._event_bus
        )
        self._assembler:       ContextAssembler = ContextAssembler()
        self._renderer:        PromptRenderer   = PromptRenderer()
        self._composer:        PromptComposer   = PromptComposer(
            self._renderer, event_bus=self._event_bus
        )
        self._prompt_validator:  PromptValidator  = PromptValidator()
        self._context_validator: ContextValidator = ContextValidator()

        self._token_budget_policy: TokenBudgetPolicy = token_budget_policy or FixedTokenBudgetPolicy()
        self._validation_policy:   ValidationPolicy  = validation_policy or StrictValidationPolicy()

        self._built = False

    def build(self) -> "PromptContextContainer":
        """Finalize wiring.  Idempotent -- safe to call multiple times."""
        self._built = True
        return self

    @property
    def is_built(self) -> bool:
        return self._built

    # ── Component accessors ───────────────────────────────────────────────────

    @property
    def event_bus(self) -> PromptEventBus:
        return self._event_bus

    @property
    def history(self) -> PromptHistory:
        return self._history

    @property
    def version_manager(self) -> VersionManager:
        return self._version_manager

    @property
    def registry(self) -> PromptRegistry:
        return self._registry

    @property
    def assembler(self) -> ContextAssembler:
        return self._assembler

    @property
    def renderer(self) -> PromptRenderer:
        return self._renderer

    @property
    def composer(self) -> PromptComposer:
        return self._composer

    @property
    def prompt_validator(self) -> PromptValidator:
        return self._prompt_validator

    @property
    def context_validator(self) -> ContextValidator:
        return self._context_validator

    @property
    def token_budget_policy(self) -> TokenBudgetPolicy:
        return self._token_budget_policy

    @property
    def validation_policy(self) -> ValidationPolicy:
        return self._validation_policy

    def __repr__(self) -> str:
        return (
            f"<PromptContextContainer built={self._built} "
            f"templates={len(self._registry)}>"
        )
