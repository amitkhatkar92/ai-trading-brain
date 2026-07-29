"""
prompt_registry.py -- iios.ai.prompt_context.registry
========================================================
:class:`PromptRegistry` -- central registry of :class:`PromptTemplate`
aggregates.  Supports registration, deregistration, enable/disable,
lookup, search/tagging, and version updates (delegated to
:class:`VersionManager`).

A3 Prompt & Context Platform -- Phase 3, Module 3
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional, Tuple

from iios.common.logging.logging_manager import get_logger

from ..core.prompt_category  import PromptCategory
from ..core.prompt_metadata  import PromptMetadata
from ..core.prompt_template  import PromptTemplate
from ..core.prompt_version   import PromptVersion
from ..events.event_bus      import PromptEventBus
from ..events.prompt_events  import (
    PromptDisabledEvent,
    PromptEnabledEvent,
    PromptRegisteredEvent,
    PromptRemovedEvent,
    PromptUpdatedEvent,
    TemplateActivatedEvent,
)
from ..exceptions            import AIPromptAlreadyExistsError, AIPromptNotFoundError
from ..versioning.version_manager import VersionManager

_log = get_logger(__name__)

SYSTEM_ID = "iios:ai:prompt_context:registry"


class PromptRegistry:
    """Thread-safe registry of prompt templates."""

    def __init__(
        self,
        version_manager: Optional[VersionManager] = None,
        event_bus:       Optional[PromptEventBus] = None,
    ) -> None:
        self._templates:       Dict[str, PromptTemplate] = {}
        self._name_index:      Dict[str, str]            = {}   # name -> prompt_id
        self._lock:            threading.RLock           = threading.RLock()
        self._version_manager: VersionManager             = version_manager or VersionManager()
        self._event_bus:       Optional[PromptEventBus]   = event_bus

    @property
    def version_manager(self) -> VersionManager:
        return self._version_manager

    # ── Registration ──────────────────────────────────────────────────────────

    def register(
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
        """
        Register a new prompt template with its initial version (auto-activated).

        Raises
        ------
        AIPromptAlreadyExistsError
            If a template with the same ``name`` is already registered.
        """
        with self._lock:
            if name in self._name_index:
                raise AIPromptAlreadyExistsError(name)
            metadata = PromptMetadata.create(
                name=name, category=category, description=description, tags=tags, owner=owner,
            )
            template = PromptTemplate(metadata)
            self._version_manager.create_version(
                template, template_text, variables,
                changed_by=changed_by, reason="initial registration", activate=True,
            )
            self._templates[metadata.prompt_id] = template
            self._name_index[name] = metadata.prompt_id

        _log.info(f"PromptRegistry: registered prompt_id={metadata.prompt_id!r} name={name!r}")
        self._publish(PromptRegisteredEvent.create(SYSTEM_ID, metadata.prompt_id, name, category.value))
        return template

    def deregister(self, prompt_id: str) -> None:
        """Permanently remove a prompt template from the registry."""
        with self._lock:
            template = self._templates.pop(prompt_id, None)
            if template is None:
                raise AIPromptNotFoundError(prompt_id)
            self._name_index.pop(template.metadata.name, None)
        _log.info(f"PromptRegistry: deregistered prompt_id={prompt_id!r}")
        self._publish(PromptRemovedEvent.create(SYSTEM_ID, prompt_id))

    # ── Enable / disable ──────────────────────────────────────────────────────

    def enable(self, prompt_id: str) -> None:
        self.get(prompt_id).enable()
        self._publish(PromptEnabledEvent.create(SYSTEM_ID, prompt_id))

    def disable(self, prompt_id: str) -> None:
        self.get(prompt_id).disable()
        self._publish(PromptDisabledEvent.create(SYSTEM_ID, prompt_id))

    # ── Version updates ───────────────────────────────────────────────────────

    def add_version(
        self,
        prompt_id:     str,
        template_text: str,
        *,
        variables:     Tuple[str, ...] = (),
        changed_by:    str            = "system",
        reason:        str            = "",
        activate:      bool           = True,
    ) -> PromptVersion:
        template = self.get(prompt_id)
        version  = self._version_manager.create_version(
            template, template_text, variables,
            changed_by=changed_by, reason=reason, activate=activate,
        )
        self._publish(
            PromptUpdatedEvent.create(SYSTEM_ID, prompt_id, version.version_id, version.version_number)
        )
        if activate:
            self._publish(
                TemplateActivatedEvent.create(
                    SYSTEM_ID, prompt_id, version.version_id, version.version_number
                )
            )
        return version

    def activate_version(self, prompt_id: str, version_id: str) -> PromptVersion:
        template = self.get(prompt_id)
        version  = self._version_manager.activate(template, version_id)
        self._publish(
            TemplateActivatedEvent.create(
                SYSTEM_ID, prompt_id, version.version_id, version.version_number
            )
        )
        return version

    def rollback(self, prompt_id: str, version_id: str) -> PromptVersion:
        template = self.get(prompt_id)
        version  = self._version_manager.rollback(template, version_id)
        self._publish(
            TemplateActivatedEvent.create(
                SYSTEM_ID, prompt_id, version.version_id, version.version_number
            )
        )
        return version

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(self, prompt_id: str) -> PromptTemplate:
        """
        Raises
        ------
        AIPromptNotFoundError
            If ``prompt_id`` is not registered.
        """
        with self._lock:
            template = self._templates.get(prompt_id)
        if template is None:
            raise AIPromptNotFoundError(prompt_id)
        return template

    def find_by_name(self, name: str) -> Optional[PromptTemplate]:
        with self._lock:
            prompt_id = self._name_index.get(name)
            if prompt_id is None:
                return None
            return self._templates.get(prompt_id)

    def search(
        self,
        *,
        category:     Optional[PromptCategory] = None,
        tag:          Optional[str]             = None,
        enabled_only: bool                      = False,
    ) -> List[PromptTemplate]:
        """Search templates by category, tag, and/or enabled state."""
        with self._lock:
            candidates = list(self._templates.values())
        results = []
        for t in candidates:
            if category is not None and t.metadata.category != category:
                continue
            if tag is not None and tag not in t.metadata.tags:
                continue
            if enabled_only and not t.enabled:
                continue
            results.append(t)
        return results

    def list_all(self) -> List[PromptTemplate]:
        with self._lock:
            return list(self._templates.values())

    def __len__(self) -> int:
        with self._lock:
            return len(self._templates)

    # ── Internals ─────────────────────────────────────────────────────────────

    def _publish(self, event) -> None:
        if self._event_bus is not None:
            self._event_bus.publish(event)
