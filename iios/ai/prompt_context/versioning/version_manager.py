"""
version_manager.py -- iios.ai.prompt_context.versioning
==========================================================
:class:`VersionManager` -- orchestrates prompt version creation,
activation, and rollback while recording audit history via
:class:`PromptHistory`.

A3 Prompt & Context Platform -- Phase 3, Module 3
"""
from __future__ import annotations

from typing import Optional, Tuple

from ..core.prompt_template import PromptTemplate
from ..core.prompt_version  import PromptVersion
from ..exceptions           import AIPromptVersionError
from .prompt_history        import PromptHistory


class VersionManager:
    """
    Coordinates version lifecycle operations on a :class:`PromptTemplate`.

    Every mutation is recorded in the shared :class:`PromptHistory`,
    giving full audit trail and rollback support across the registry.
    """

    def __init__(self, history: Optional[PromptHistory] = None) -> None:
        self._history: PromptHistory = history or PromptHistory()

    @property
    def history(self) -> PromptHistory:
        return self._history

    def create_version(
        self,
        template:      PromptTemplate,
        template_text: str,
        variables:     Tuple[str, ...] = (),
        *,
        changed_by:    str  = "system",
        reason:        str  = "",
        activate:      bool = True,
    ) -> PromptVersion:
        """Create and append a new version to ``template``."""
        next_number = len(template.history()) + 1
        version = PromptVersion.create(
            template.prompt_id, next_number, template_text, variables,
            changed_by=changed_by, reason=reason,
        )
        template.add_version(version, activate=activate)
        version = template.get_version(version.version_id)
        action  = "created:activated" if version.active else "created"
        self._history.record(template.prompt_id, version, action)
        return version

    def activate(self, template: PromptTemplate, version_id: str) -> PromptVersion:
        """Activate an existing version (does not create a new one)."""
        template.activate_version(version_id)
        version = template.get_version(version_id)
        self._history.record(template.prompt_id, version, "activated")
        return version

    def rollback(self, template: PromptTemplate, version_id: str) -> PromptVersion:
        """
        Roll back to a previously created (non-active) version.

        Raises
        ------
        AIPromptVersionError
            If ``version_id`` does not exist for this template.
        """
        known = {v.version_id for v in template.history()}
        if version_id not in known:
            raise AIPromptVersionError(
                f"Cannot rollback: unknown version_id {version_id!r} "
                f"for prompt {template.prompt_id!r}"
            )
        template.activate_version(version_id)
        version = template.get_version(version_id)
        self._history.record(template.prompt_id, version, "rolled_back")
        return version
