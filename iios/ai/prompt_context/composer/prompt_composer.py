"""
prompt_composer.py -- iios.ai.prompt_context.composer
========================================================
:class:`PromptComposer` -- combines a rendered prompt template with an
optional :class:`AssembledContext` into a final :class:`PromptResult`.

This is the final stage of A3 -- output is handed to A1/A2 for
execution. A3 never calls a provider.

A3 Prompt & Context Platform -- Phase 3, Module 3
"""
from __future__ import annotations

from typing import Optional

from ..context.assembled_context import AssembledContext
from ..core.prompt_category      import PromptCategory
from ..core.prompt_template      import PromptTemplate
from ..core.prompt_variables     import PromptResult, PromptVariables
from ..core.token_estimator      import estimate_tokens
from ..events.event_bus          import PromptEventBus
from ..events.prompt_events      import PromptRenderedEvent
from ..exceptions                import AIPromptDisabledError, AIPromptVersionError
from .prompt_renderer            import PromptRenderer

SYSTEM_ID = "iios:ai:prompt_context:composer"


class PromptComposer:
    """Composes a final prompt from a template's active version + optional context."""

    def __init__(
        self,
        renderer:  Optional[PromptRenderer]  = None,
        event_bus: Optional[PromptEventBus]  = None,
    ) -> None:
        self._renderer:  PromptRenderer            = renderer or PromptRenderer()
        self._event_bus: Optional[PromptEventBus]  = event_bus

    def compose(
        self,
        template:  PromptTemplate,
        variables: PromptVariables,
        *,
        context:   Optional[AssembledContext] = None,
    ) -> PromptResult:
        """
        Raises
        ------
        AIPromptDisabledError
            If ``template`` is currently disabled.
        AIPromptVersionError
            If ``template`` has no active version.
        AIMissingVariableError
            If a required template variable is missing.
        """
        if not template.enabled:
            raise AIPromptDisabledError(template.prompt_id)

        version = template.active_version
        if version is None:
            raise AIPromptVersionError(f"Prompt {template.prompt_id!r} has no active version.")

        rendered    = self._renderer.render(version, variables)
        system_text = rendered if template.metadata.category == PromptCategory.SYSTEM else ""

        full_text        = rendered
        estimated_tokens  = estimate_tokens(rendered)
        if context is not None:
            full_text        = f"{context.to_text()}\n\n{rendered}"
            estimated_tokens += context.estimated_tokens

        result = PromptResult(
            prompt_id        = template.prompt_id,
            version_id       = version.version_id,
            rendered_text    = full_text,
            system_text      = system_text,
            variables_used   = version.variables,
            estimated_tokens = estimated_tokens,
            context_included = context is not None,
        )

        if self._event_bus is not None:
            self._event_bus.publish(
                PromptRenderedEvent.create(
                    SYSTEM_ID, template.prompt_id, version.version_id, estimated_tokens
                )
            )
        return result
