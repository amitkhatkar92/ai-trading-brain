"""
prompt_version.py -- iios.ai.prompt_context.core
===================================================
:class:`PromptVersion` -- immutable snapshot of a single version of a
prompt template's text, declared variables, and activation state.

A3 Prompt & Context Platform -- Phase 3, Module 3
"""
from __future__ import annotations

import dataclasses
import uuid
from dataclasses import dataclass, field
from typing import Tuple

from .change_metadata import ChangeMetadata


@dataclass(frozen=True)
class PromptVersion:
    """Immutable prompt version.  Use :meth:`with_active` to change activation."""
    version_id:     str
    prompt_id:      str
    version_number: int
    template_text:  str
    variables:      Tuple[str, ...] = field(default_factory=tuple)
    change:         ChangeMetadata  = None  # type: ignore[assignment]
    active:         bool            = False

    @classmethod
    def create(
        cls,
        prompt_id:      str,
        version_number: int,
        template_text:  str,
        variables:      Tuple[str, ...] = (),
        *,
        changed_by:     str = "system",
        reason:         str = "",
    ) -> "PromptVersion":
        return cls(
            version_id     = str(uuid.uuid4()),
            prompt_id      = prompt_id,
            version_number = version_number,
            template_text  = template_text,
            variables      = tuple(variables),
            change         = ChangeMetadata.create(changed_by, reason),
            active         = False,
        )

    def with_active(self, active: bool) -> "PromptVersion":
        """Return a new :class:`PromptVersion` with ``active`` flipped."""
        return dataclasses.replace(self, active=active)
