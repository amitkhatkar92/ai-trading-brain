"""
change_metadata.py -- iios.ai.prompt_context.core
====================================================
:class:`ChangeMetadata` -- immutable audit record attached to every
prompt version change (creation, activation, rollback).

A3 Prompt & Context Platform -- Phase 3, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class ChangeMetadata:
    """Immutable audit metadata for a single prompt version change."""
    change_id:  str
    changed_by: str
    changed_at: float
    reason:     str = ""

    @classmethod
    def create(cls, changed_by: str = "system", reason: str = "") -> "ChangeMetadata":
        return cls(
            change_id  = str(uuid.uuid4()),
            changed_by = changed_by,
            changed_at = time.time(),
            reason     = reason,
        )
