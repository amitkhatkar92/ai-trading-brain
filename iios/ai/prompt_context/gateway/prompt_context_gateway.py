"""
prompt_context_gateway.py -- iios.ai.prompt_context.gateway
===============================================================
:class:`PromptContextGateway` -- the single public entry point for the
A3 Prompt & Context Platform.

All other AI Platform modules (A1-A2, A4-A10) interact with A3
exclusively through this gateway.  No external module imports from
``iios.ai.prompt_context.registry``, ``.context``, ``.composer``, or
any other internal A3 sub-package.

Design
------
* Inherits ``AILifecycleAwareMixin`` (via A1) -- full lifecycle management.
* Owns a :class:`PromptContextContainer` -- DI composition root.
* Exposes a minimal, stable public API -- this is the V1 contract for A3.

A3 Prompt & Context Platform -- Phase 3, Module 3  |  M6 Gateway
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

from iios.common.logging.logging_manager import get_logger

from ..container.prompt_context_container import PromptContextContainer
from ..context.assembled_context    import AssembledContext
from ..context.context_builder      import ContextBuilder
from ..core.prompt_category         import PromptCategory
from ..core.prompt_template         import PromptTemplate
from ..core.prompt_variables        import PromptResult, PromptVariables
from ..core.prompt_version          import PromptVersion
from ..events.event_bus             import PromptEventBus
from ..events.prompt_events         import ValidationFailedEvent, ValidationSucceededEvent
from ..lifecycle import AILifecycleAwareMixin, AILifecycleState
from ..snapshot.prompt_context_snapshot import PromptContextSnapshot
from ..validation.validation_result import ValidationResult

_log = get_logger(__name__)

SYSTEM_ID = "iios:ai:prompt_context:gateway"


class PromptContextGateway(AILifecycleAwareMixin):
    """
    Single public entry point for the A3 Prompt & Context Platform.

    Usage::

        from iios.ai.prompt_context.gateway import PromptContextGateway
        from iios.ai.prompt_context.core import PromptCategory

        gw = PromptContextGateway()
        gw.initialize()
        gw.start()

        gw.register_prompt(
            "greeting", PromptCategory.SYSTEM, "Hello {{name}}!", variables=("name",)
        )
        ctx = gw.build_context("session-1", "my.module").add_user("hi").build()
        result = gw.compose_prompt("greeting", {"name": "Trader"}, context=ctx)
    """

    SYSTEM_ID: str = "iios:ai:prompt_context:gateway"
    VERSION:   str = "1.0.0"

    def __init__(self, container: Optional[PromptContextContainer] = None) -> None:
        self._container: PromptContextContainer   = container or PromptContextContainer()
        self._started_at: Optional[float]          = None

    # ── Lifecycle hooks ───────────────────────────────────────────────────────

    def _on_initialize(self) -> None:
        self._container.build()
        _log.info("PromptContextGateway: container built")

    def _on_start(self) -> None:
        self._started_at = time.time()
        _log.info(f"PromptContextGateway: started (v{self.VERSION})")

    def _on_stop(self) -> None:
        _log.info(
            f"PromptContextGateway: stopped "
            f"(templates={len(self._container.registry)})"
        )

    # ── Prompt Registry API ───────────────────────────────────────────────────

    def register_prompt(
        self,
        name:          str,
        category:      PromptCategory,
        template_text: str,
        *,
        description:   str            = "",
        tags:          Tuple[str, ...] = (),
        owner:         str            = "",
        variables:     Tuple[str, ...] = (),
        changed_by:    str            = "system",
    ) -> PromptTemplate:
        """Register a new prompt template with its initial (active) version."""
        return self._container.registry.register(
            name, category, template_text,
            description=description, tags=tags, owner=owner,
            variables=variables, changed_by=changed_by,
        )

    def remove_prompt(self, prompt_id: str) -> None:
        """Permanently deregister a prompt template."""
        self._container.registry.deregister(prompt_id)

    def enable_prompt(self, prompt_id: str) -> None:
        self._container.registry.enable(prompt_id)

    def disable_prompt(self, prompt_id: str) -> None:
        self._container.registry.disable(prompt_id)

    def get_prompt(self, prompt_id: str) -> PromptTemplate:
        """Raises ``AIPromptNotFoundError`` if unknown."""
        return self._container.registry.get(prompt_id)

    def find_prompt_by_name(self, name: str) -> Optional[PromptTemplate]:
        return self._container.registry.find_by_name(name)

    def list_templates(
        self,
        *,
        category:     Optional[PromptCategory] = None,
        tag:          Optional[str]             = None,
        enabled_only: bool                      = False,
    ) -> List[PromptTemplate]:
        """List/search registered templates by category, tag, and/or enabled state."""
        return self._container.registry.search(category=category, tag=tag, enabled_only=enabled_only)

    # ── Template Versioning API ───────────────────────────────────────────────

    def add_version(
        self,
        prompt_id:     str,
        template_text: str,
        *,
        variables:  Tuple[str, ...] = (),
        changed_by: str            = "system",
        reason:     str            = "",
        activate:   bool           = True,
    ) -> PromptVersion:
        return self._container.registry.add_version(
            prompt_id, template_text,
            variables=variables, changed_by=changed_by, reason=reason, activate=activate,
        )

    def activate_version(self, prompt_id: str, version_id: str) -> PromptVersion:
        return self._container.registry.activate_version(prompt_id, version_id)

    def rollback(self, prompt_id: str, version_id: str) -> PromptVersion:
        return self._container.registry.rollback(prompt_id, version_id)

    def version_history(self, prompt_id: str) -> List[PromptVersion]:
        return self.get_prompt(prompt_id).history()

    # ── Context Builder API ───────────────────────────────────────────────────

    def build_context(
        self,
        session_id: str,
        module_id:  str,
        *,
        max_tokens: Optional[int] = None,
        trace_id:   str           = "",
    ) -> ContextBuilder:
        """
        Return a fluent :class:`ContextBuilder` seeded with the module's
        token budget policy.
        """
        budget = max_tokens or self._container.token_budget_policy.max_tokens_for(module_id)
        return (
            ContextBuilder(
                session_id, module_id, self._container.assembler, self._container.event_bus
            )
            .with_max_tokens(budget)
            .with_trace_id(trace_id)
        )

    # ── Prompt Composer API ───────────────────────────────────────────────────

    def compose_prompt(
        self,
        prompt_id: str,
        variables: Dict[str, Any],
        *,
        context:   Optional[AssembledContext] = None,
    ) -> PromptResult:
        """Render + compose the final prompt text for ``prompt_id``."""
        template = self.get_prompt(prompt_id)
        return self._container.composer.compose(
            template, PromptVariables(dict(variables)), context=context,
        )

    # ── Validation API ────────────────────────────────────────────────────────

    def validate_prompt(
        self,
        prompt_id: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """Validate a template's structure and (optionally) supplied variables."""
        template = self.get_prompt(prompt_id)
        var_obj  = PromptVariables(dict(variables)) if variables is not None else None
        result   = self._container.prompt_validator.validate(template, var_obj)
        self._publish_validation_event("prompt", prompt_id, result)
        return result

    def validate_context(self, context: AssembledContext) -> ValidationResult:
        """Validate an assembled context's completeness and budget."""
        result = self._container.context_validator.validate(context)
        self._publish_validation_event("context", context.context_id, result)
        return result

    def _publish_validation_event(self, target: str, target_id: str, result: ValidationResult) -> None:
        bus = self._container.event_bus
        if result.is_valid:
            bus.publish(ValidationSucceededEvent.create(SYSTEM_ID, target, target_id))
        else:
            bus.publish(ValidationFailedEvent.create(SYSTEM_ID, target, target_id, result.errors))

    # ── Observability ─────────────────────────────────────────────────────────

    def health(self) -> Dict[str, Any]:
        """Return a structured health dictionary."""
        state     = self.lifecycle_state
        templates = self._container.registry.list_all()
        return {
            "module_id":              self.SYSTEM_ID,
            "state":                  state.value,
            "is_running":             (state == AILifecycleState.RUNNING),
            "template_count":         len(templates),
            "enabled_template_count": sum(1 for t in templates if t.enabled),
            "version":                self.VERSION,
        }

    def status(self) -> Dict[str, Any]:
        """Return a verbose status dictionary (superset of health)."""
        h = self.health()
        h["events_published"] = self._container.event_bus.published_count
        h["history_entries"]  = len(self._container.history)
        return h

    def snapshot(self) -> PromptContextSnapshot:
        """Return an immutable :class:`PromptContextSnapshot`."""
        return PromptContextSnapshot.capture(self._container.registry, self._container.event_bus)

    # ── Access to shared infrastructure ───────────────────────────────────────

    @property
    def event_bus(self) -> PromptEventBus:
        return self._container.event_bus

    @property
    def container(self) -> PromptContextContainer:
        return self._container
